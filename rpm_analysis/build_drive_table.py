"""Combine the per-zip summaries into one table with one row per drive across 2013-2026.

Usage:
    python build_drive_table.py [--summaries summaries] [--out drives.parquet]
"""
import argparse
from pathlib import Path

import duckdb

QUERY = """
COPY (
  SELECT serial_number,
         -- older files say 'Hitachi HDS...', later ones 'HGST HDS...': use one name per model
         regexp_replace(any_value(model), '^(HGST|Hitachi) ', '')       AS model,
         max(capacity_bytes)                                             AS capacity_bytes,
         min(first_date)                                                 AS first_date,
         max(last_date)                                                  AS last_date,
         arg_min(first_poh, first_date) FILTER (WHERE first_poh IS NOT NULL) AS first_poh,
         arg_max(last_poh,  last_date)  FILTER (WHERE last_poh  IS NOT NULL) AS last_poh,
         max(failed)                                                     AS failed,
         sum(days)                                                       AS days
  FROM read_parquet('{glob}')
  GROUP BY serial_number
  ORDER BY serial_number
) TO '{out}' (FORMAT parquet)
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summaries", type=Path, default=Path("summaries"))
    ap.add_argument("--out", type=Path, default=Path("drives.parquet"))
    args = ap.parse_args()

    files = list(args.summaries.glob("*.parquet"))
    if not files:
        raise SystemExit(f"No summaries in {args.summaries}; run process_zips.py first.")

    glob = args.summaries.resolve().as_posix().replace("'", "''") + "/*.parquet"
    out = args.out.resolve().as_posix().replace("'", "''")
    con = duckdb.connect()
    con.execute(QUERY.format(glob=glob, out=out))
    n, failures, models, start, end = con.execute(
        f"SELECT count(*), sum(failed), count(DISTINCT model), min(first_date), max(last_date) FROM '{out}'"
    ).fetchone()
    print(f"Combined {len(files)} summaries -> {args.out}")
    print(f"{n:,} drives, {failures:,} failures, {models:,} models, {start} to {end}")


if __name__ == "__main__":
    main()
