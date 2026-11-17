"""Reduce one folder of Backblaze daily CSVs to one row per drive.

Usage (normally called by process_zips.py):
    python summarize.py <folder_with_csvs> <output.parquet>
"""
import sys
from pathlib import Path

import duckdb

# Every column is read as text and cast explicitly. Backblaze adds SMART columns
# over the years, and type sniffing across hundreds of files is fragile.
QUERY = """
COPY (
  SELECT serial_number,
         any_value(model)                                AS model,
         max(capacity_bytes)                             AS capacity_bytes,
         min(d)                                          AS first_date,
         max(d)                                          AS last_date,
         arg_min(poh, d) FILTER (WHERE poh IS NOT NULL)  AS first_poh,
         arg_max(poh, d) FILTER (WHERE poh IS NOT NULL)  AS last_poh,
         max(failure)                                    AS failed,
         count(*)                                        AS days
  FROM (
    SELECT trim(serial_number)                  AS serial_number,
           trim(model)                          AS model,
           TRY_CAST(capacity_bytes AS BIGINT)   AS capacity_bytes,
           TRY_CAST(failure AS INTEGER)         AS failure,
           TRY_CAST(date AS DATE)               AS d,
           TRY_CAST(smart_9_raw AS DOUBLE)      AS poh      -- power-on hours
    FROM read_csv('{glob}', union_by_name=true, all_varchar=true, header=true)
  )
  WHERE serial_number IS NOT NULL AND serial_number <> '' AND d IS NOT NULL
  GROUP BY serial_number
) TO '{out}' (FORMAT parquet)
"""


def _sql_path(p: Path) -> str:
    return p.resolve().as_posix().replace("'", "''")


def summarize_folder(csv_dir: Path, out_file: Path) -> None:
    """Write one row per drive for every daily CSV under csv_dir (recursively)."""
    glob = _sql_path(Path(csv_dir)) + "/**/*.csv"
    con = duckdb.connect()
    try:
        con.execute(QUERY.format(glob=glob, out=_sql_path(Path(out_file))))
    finally:
        con.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    summarize_folder(Path(sys.argv[1]), Path(sys.argv[2]))
    print("wrote", sys.argv[2])
