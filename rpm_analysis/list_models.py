"""List models with enough drives so you can label each one's RPM from its spec sheet.

Writes models_to_label.csv with an empty `rpm` column for you to fill in, plus an
`rpm_hint` column. The hints are starting points only: verify every model against the
manufacturer's spec sheet. sample_by_rpm.py reads only the `rpm` column.
Leave `rpm` blank for SSDs and any model you want to exclude.

Usage:
    python list_models.py [--drives drives.parquet] [--min-drives 500] [--force]
"""
import argparse
import re
from pathlib import Path

import pandas as pd

OUT = Path("models_to_label.csv")

# Starting points only. Verify each one.
KNOWN_HINTS = {
    "ST4000DM000": 5900,
    "ST12000NM0007": 7200,
    "ST12000NM0008": 7200,
    "ST8000NM0055": 7200,
    "TOSHIBA MG07ACA14TA": 7200,
    "ST3000DM001": 7200,
    "ST8000DM002": 7200,
    "ST6000DX000": 7200,
    "ST31500541AS": 5900,     # Barracuda LP
}


def rpm_hint(model: str):
    if model in KNOWN_HINTS:
        return KNOWN_HINTS[model]
    # Hitachi/HGST: the digit(s) after the series letters give the speed class.
    # "5C" = CoolSpin, which these drives report as 5700 RPM (often mislisted as 5400).
    if re.match(r"^H[A-Z]S5", model):          # HDS5..., HMS5...
        return 5700
    if re.match(r"^H[A-Z]{2}72", model):       # HDS72..., HUS72..., HUH72...
        return 7200
    if re.match(r"^WDC WD\d+EFRX$", model):    # WD Red, "5400 RPM class"
        return 5400
    if re.match(r"^WDC WUH72", model):         # WD Ultrastar DC HC5xx
        return 7200
    if re.match(r"^TOSHIBA MG\d", model):      # Toshiba enterprise MG series
        return 7200
    if re.match(r"^ST\d+NM", model):           # Seagate Exos / enterprise
        return 7200
    if "SSD" in model:
        return "SSD - exclude"
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drives", type=Path, default=Path("drives.parquet"))
    ap.add_argument("--min-drives", type=int, default=500)
    ap.add_argument("--force", action="store_true", help="overwrite an existing models_to_label.csv")
    args = ap.parse_args()

    if OUT.exists() and not args.force:
        raise SystemExit(f"{OUT} already exists (it may have your RPM labels). Use --force to overwrite.")

    d = pd.read_parquet(args.drives)
    summary = (
        d.groupby("model")
        .agg(
            drives=("serial_number", "size"),
            failures=("failed", "sum"),
            drive_years=("days", lambda x: round(x.sum() / 365, 1)),
            capacity_tb=("capacity_bytes", lambda x: round(x.median() / 1e12, 1)),
            first_year=("first_date", lambda x: pd.to_datetime(x).dt.year.min()),
            last_year=("last_date", lambda x: pd.to_datetime(x).dt.year.max()),
        )
        .query("drives >= @args.min_drives")
        .sort_values("drives", ascending=False)
        .reset_index()
    )
    summary["afr_pct"] = (100 * summary.failures / summary.drive_years).round(2)
    summary["rpm_hint"] = summary.model.map(rpm_hint)
    summary["rpm"] = ""
    summary.to_csv(OUT, index=False)
    print(f"Wrote {len(summary)} models with >= {args.min_drives} drives to {OUT}")
    print("Next: fill in the `rpm` column from spec sheets, then run sample_by_rpm.py")


if __name__ == "__main__":
    main()
