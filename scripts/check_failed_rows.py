"""Do failed drives drop out of the data after they fail, or keep showing up?

For every drive with a failure = 1 row, count how many rows it has after
its first failure date, and how many drives have more than one failure row.
"""
from connect import connect


def main():
    con = connect()
    print("Checking failed drives (one pass over the data, takes a few minutes)...")
    con.sql("""
        CREATE TABLE per_drive AS
        WITH fails AS (
            SELECT serial_number, min(date) AS fail_date, count(*) AS fail_rows
            FROM drives
            WHERE failure = 1
            GROUP BY 1
        )
        SELECT f.serial_number,
               f.fail_date,
               f.fail_rows,
               count(*) FILTER (WHERE d.date > f.fail_date) AS rows_after,
               min(d.date) FILTER (WHERE d.date > f.fail_date) AS next_seen,
               max(d.date) AS last_seen
        FROM fails f
        JOIN drives d USING (serial_number)
        GROUP BY ALL
    """)

    s = con.sql("""
        SELECT count(*) AS failed_drives,
               count(*) FILTER (WHERE rows_after = 0) AS gone_after_failure,
               count(*) FILTER (WHERE rows_after > 0) AS seen_again,
               count(*) FILTER (WHERE fail_rows > 1) AS failed_more_than_once,
               median(next_seen - fail_date) FILTER (WHERE rows_after > 0) AS median_days_until_seen_again
        FROM per_drive
    """).df()
    print(s.T.to_string(header=False))

    print("\nExamples of drives seen again after failing:")
    print(con.sql("""
        SELECT serial_number, fail_date, next_seen, last_seen, rows_after, fail_rows
        FROM per_drive WHERE rows_after > 0
        ORDER BY rows_after DESC, serial_number LIMIT 10
    """).df().to_string(index=False))


if __name__ == "__main__":
    main()
