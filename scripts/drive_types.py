"""Label every drive model in the data as HDD or SSD, and boot or data.

There's no drive type column, so this goes off the model name, with a
SMART check on top: HDDs report spin-up time (smart_3) and spin retries
(smart_10), SSDs usually don't. Models where the name and SMART disagree
get check_by_hand = True.

Boot vs data: all SSDs are boot drives. HDDs under 1 TB, plus 2.5" laptop
models, are boot drives too. Everything else is a data drive.

Writes data/drive_models.csv and prints the SSD and boot lists for a manual check.
"""
import re

from connect import DATA, connect

# Model name patterns that mean SSD. Checked against Backblaze's SSD Drive Stats posts.
SSD_PATTERNS = [
    r"SSD",           # anything that says SSD in the name
    r"\bZA\d",        # Seagate BarraCuda / IronWolf SSDs, e.g. ZA250CM10002
    r"SA510",         # WD Blue SA510
    r"SSDSC",         # Intel / Dell, e.g. SSDSCKKB240G8R
    r"MTFD",          # Micron, e.g. MTFDDAV240TCB
    r"^(Crucial )?CT\d",  # Crucial, e.g. CT250MX500SSD1
    r"WDS\d",         # WD Blue / Green SSDs, e.g. WDS250G2B0A
    r"^(SAMSUNG )?MZ", # Samsung SSDs, e.g. MZ7LH240HAHQ
    r"^KINGSTON S",   # Kingston SSDs, e.g. KINGSTON SA400S37240G
    r"DELLBOSS",      # Dell BOSS boot card (M.2 SSDs)
]
SSD_RE = re.compile("|".join(SSD_PATTERNS), re.IGNORECASE)


def drive_type(model: str) -> str:
    return "SSD" if SSD_RE.search(model) else "HDD"


# 2.5" laptop HDDs used as boot drives, e.g. ST500LM030, TOSHIBA MQ01ABF050
LAPTOP_HDD_RE = re.compile(r"LM\d|MQ01", re.IGNORECASE)


def role(row) -> str:
    if row["drive_type"] == "SSD":
        return "boot"
    if row["capacity_bytes"] < 1e12 or LAPTOP_HDD_RE.search(row["model"]):
        return "boot"
    return "data"


def main():
    con = connect()
    print("Scanning models (one pass over the model column, takes a few minutes)...")
    models = con.sql("""
        SELECT model,
               mode(capacity_bytes) AS capacity_bytes,
               count(*) AS drive_days,
               count(DISTINCT serial_number) AS drives,
               min(date) AS first_seen,
               max(date) AS last_seen,
               -- share of reports that include spin-up time or spin retries (HDD-only attributes)
               round(avg((smart_3_normalized IS NOT NULL OR smart_10_normalized IS NOT NULL)::int), 3)
                   AS spin_attr_share
        FROM drives
        WHERE model IS NOT NULL
        GROUP BY 1
        ORDER BY drive_days DESC
    """).df()
    models["drive_type"] = models["model"].map(drive_type)
    models["role"] = models.apply(role, axis=1)
    models["check_by_hand"] = (
        ((models["drive_type"] == "SSD") & (models["spin_attr_share"] > 0.5))
        | ((models["drive_type"] == "HDD") & (models["spin_attr_share"] < 0.5))
    )

    DATA.mkdir(exist_ok=True)
    out = DATA / "drive_models.csv"
    models.to_csv(out, index=False)

    cols = ["model", "capacity_bytes", "drives", "spin_attr_share"]
    ssd = models[models["drive_type"] == "SSD"]
    boot_hdd = models[(models["drive_type"] == "HDD") & (models["role"] == "boot")]
    flagged = models[models["check_by_hand"]]
    print(f"\n{len(models)} models: {len(ssd)} SSD ({ssd.drives.sum()} drives), "
          f"{len(boot_hdd)} boot HDD ({boot_hdd.drives.sum()} drives). Wrote {out}\n")
    print("SSD models:")
    print(ssd[cols].to_string(index=False))
    print("\nBoot HDD models:")
    print(boot_hdd[cols].to_string(index=False))
    print("\nName and SMART disagree (check these by hand):")
    print(flagged[cols + ["drive_type"]].to_string(index=False) if len(flagged) else "none")


if __name__ == "__main__":
    main()