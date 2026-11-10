"""Shared DuckDB connection to Backblaze's Drive Stats Iceberg table.

Usage:
    from connect import connect
    con = connect()
    con.sql("SELECT count(*) FROM drives")
"""
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"


def connect():
    load_dotenv(REPO / ".env")
    key_id = os.environ.get("B2_KEY_ID")
    app_key = os.environ.get("B2_APP_KEY")
    if not key_id or not app_key:
        raise SystemExit("Missing B2_KEY_ID / B2_APP_KEY. Copy .env.example to .env.")

    con = duckdb.connect()
    con.sql("INSTALL httpfs; LOAD httpfs; INSTALL iceberg; LOAD iceberg;")
    con.sql(f"""
        CREATE SECRET b2 (
            TYPE s3,
            KEY_ID '{key_id}',
            SECRET '{app_key}',
            REGION 'us-west-004',
            ENDPOINT 's3.us-west-004.backblazeb2.com'
        )
    """)
    con.sql("SET unsafe_enable_version_guessing = true")
    # Some models show up with extra spaces ("WDC  WUH721414ALE6L4"), so squash those.
    con.sql("""
        CREATE VIEW drives AS
        SELECT * REPLACE (regexp_replace(trim(model), '\\s+', ' ', 'g') AS model)
        FROM iceberg_scan(
            's3://drivestats-iceberg/drivestats',
            version = '?',
            allow_moved_paths = true
        )
    """)
    return con


if __name__ == "__main__":
    # Quick connection test
    con = connect()
    print(con.sql("DESCRIBE drives").df().head(30).to_string())
