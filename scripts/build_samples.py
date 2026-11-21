"""Build the sample data sets in data/samples/.

- failed_1000.csv           1000 random drives that failed (any type)
- hdd_random_1000.csv       1000 random data HDDs, failed or not
- model_totals.csv          drives, failures and drive-days for every model
- maker_failed_2000.csv     2000 failed data HDDs from each of Seagate, WD and Toshiba
- maker_random_2000.csv     2000 data HDDs from each maker, failed or not

The maker_* files take the same number of drives from each maker (stratified sampling
with equal allocation), so the three can be compared fairly. See ANALYSIS_PLAN.md.

Run drive_types.py first (this reads data/drive_models.csv).
The pick is random but repeatable: drives are sorted by md5(serial + SEED).
Change SEED to get a different sample.
"""
from connect import DATA, connect

SEED = "42"
N = 1000
N_PER_MAKER = 2000
MAKERS = "'Seagate', 'Western Digital', 'Toshiba'"
OUT = DATA / "samples"


def main():
    con = connect()
    models_csv = (DATA / "drive_models.csv").as_posix()
    con.sql(f"CREATE TABLE models AS SELECT model, drive_type, role, manufacturer FROM read_csv('{models_csv}')")

    # Pass 1: one row per drive across the whole dataset (a few minutes)
    print("Pass 1: summarising every drive...")
    con.sql("""
        CREATE TABLE per_drive AS
        SELECT serial_number,
               mode(model) AS model,
               count(*) AS drive_days,
               max(date) AS last_date,
               max(failure) AS failed,
               min(date) FILTER (WHERE failure = 1) AS fail_date,
               count(smart_9_raw) AS poh_rows
        FROM drives
        WHERE serial_number IS NOT NULL
        GROUP BY 1
    """)
    con.sql("""
        CREATE TABLE per_drive_t AS
        SELECT p.*, m.drive_type, m.role, m.manufacturer FROM per_drive p LEFT JOIN models m USING (model)
    """)

    # Per-model totals, for failure rates
    totals = con.sql("""
        SELECT model, drive_type, role,
               count(*) AS drives,
               sum(failed) AS failures,
               sum(drive_days) AS drive_days,
               sum(drive_days) * 24 AS drive_hours
        FROM per_drive_t
        GROUP BY ALL
        ORDER BY drives DESC, model
    """).df()

    # Pick the samples. Only drives with at least one power-on hours reading.
    def pick(name, where):
        con.sql(f"""
            CREATE TABLE pick_{name} AS
            SELECT serial_number, model, drive_type, role, fail_date
            FROM per_drive_t
            WHERE poh_rows > 0 AND {where}
            ORDER BY md5(serial_number || '-{SEED}')
            LIMIT {N}
        """)

    # Same idea, but N_PER_MAKER drives from each of the big three
    def pick_by_maker(name, where):
        con.sql(f"""
            CREATE TABLE pick_{name} AS
            SELECT serial_number, model, drive_type, role, fail_date
            FROM per_drive_t
            WHERE poh_rows > 0 AND drive_type = 'HDD' AND role = 'data'
              AND manufacturer IN ({MAKERS}) AND {where}
            QUALIFY row_number() OVER (PARTITION BY manufacturer
                                       ORDER BY md5(serial_number || '-{SEED}')) <= {N_PER_MAKER}
        """)

    pick("failed", "failed = 1")
    pick("hdd", "drive_type = 'HDD' AND role = 'data'")
    pick_by_maker("maker_failed", "failed = 1")
    pick_by_maker("maker_random", "true")
    con.sql("""
        CREATE TABLE picks AS
        SELECT * FROM pick_failed UNION SELECT * FROM pick_hdd
        UNION SELECT * FROM pick_maker_failed UNION SELECT * FROM pick_maker_random
    """)

    # Pass 2: details for just the picked drives, up to their first failure
    print("Pass 2: details for the picked drives...")
    con.sql("""
        CREATE TABLE details AS
        SELECT d.serial_number,
               min(d.date) AS first_date,
               max(d.date) AS last_date,
               count(*) AS days_observed,
               max(d.failure) AS failed,
               mode(d.capacity_bytes) AS capacity_bytes,
               mode(d.datacenter) AS datacenter,
               arg_min(d.smart_9_raw, d.date) FILTER (WHERE d.smart_9_raw IS NOT NULL) AS poh_first,
               arg_max(d.smart_9_raw, d.date) FILTER (WHERE d.smart_9_raw IS NOT NULL) AS poh_last,
               min(d.date) FILTER (WHERE d.smart_9_raw IS NOT NULL) AS poh_first_date,
               max(d.date) FILTER (WHERE d.smart_9_raw IS NOT NULL) AS poh_last_date
        FROM drives d
        JOIN picks p USING (serial_number)
        WHERE d.date <= coalesce(p.fail_date, DATE '9999-12-31')
        GROUP BY 1
    """)

    # Flag power-on hours that don't line up with the calendar. Some models
    # report smart_9 in odd units, and some values are just junk.
    con.sql("""
        CREATE TABLE sample_rows AS
        SELECT p.serial_number, p.model, p.drive_type, p.role, m.manufacturer, d.capacity_bytes,
               d.first_date, d.last_date, d.days_observed, d.failed,
               d.poh_first, d.poh_last, d.datacenter,
               (d.poh_last - d.poh_first) / nullif((d.poh_last_date - d.poh_first_date) * 24, 0)
                   AS poh_ratio,
               coalesce(
                   d.poh_last <= 0
                   OR d.poh_last > 24 * 365 * 15
                   OR (d.poh_last_date - d.poh_first_date >= 30
                       AND NOT ((d.poh_last - d.poh_first)
                                / ((d.poh_last_date - d.poh_first_date) * 24) BETWEEN 0.5 AND 1.5)),
                   true) AS poh_suspect
        FROM picks p JOIN details d USING (serial_number)
        LEFT JOIN models m USING (model)
    """)

    OUT.mkdir(parents=True, exist_ok=True)
    totals.to_csv(OUT / "model_totals.csv", index=False)
    samples = [
        ("failed", "failed_1000.csv"),
        ("hdd", "hdd_random_1000.csv"),
        ("maker_failed", f"maker_failed_{N_PER_MAKER}.csv"),
        ("maker_random", f"maker_random_{N_PER_MAKER}.csv"),
    ]
    for name, file in samples:
        # The old samples keep their old columns; only the maker_* files get manufacturer
        drop = "poh_ratio" if name.startswith("maker_") else "poh_ratio, manufacturer"
        df = con.sql(f"""
            SELECT s.* EXCLUDE ({drop}), round(s.poh_ratio, 3) AS poh_ratio
            FROM sample_rows s JOIN pick_{name} USING (serial_number)
            ORDER BY serial_number
        """).df()
        df.to_csv(OUT / file, index=False)
        print(f"{file}: {len(df)} drives, {int(df.failed.sum())} failed, "
              f"{int(df.poh_suspect.sum())} with suspect power-on hours")
        if name.startswith("maker_"):
            print("   ", df.manufacturer.value_counts().to_dict())
    print(f"model_totals.csv: {len(totals)} models")


if __name__ == "__main__":
    main()
