"""Build a small website that shows the sample: failures over time and the failure rate per RPM class.

Reads the sample (default sample.parquet), counts failures per calendar quarter for each speed
class, computes each class's annualized failure rate, and writes one self-contained page.

A drive's failure date is the last day it reported (Backblaze marks failure = 1 on that day).
AFR = failures / drive-years, where drive-years = days observed / 365.

Usage:
    python make_website.py [--sample sample.parquet] [--out website/index.html]
"""
import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

TEMPLATE = Path(__file__).with_name("website_template.html")


def build_data(sample_path: Path) -> dict:
    s = pd.read_parquet(sample_path)
    s["first_date"] = pd.to_datetime(s.first_date)
    s["last_date"] = pd.to_datetime(s.last_date)
    classes = sorted(s.rpm_class.unique(), key=int)

    summary = []
    for cls in classes:
        g = s[s.rpm_class == cls]
        drive_years = g.days.sum() / 365
        failures = int(g.failed.sum())
        summary.append({
            "rpm": cls,
            "drives": int(len(g)),
            "failures": failures,
            "drive_years": round(float(drive_years), 1),
            "afr": round(100 * failures / drive_years, 2),
            "models": sorted(g.model.unique().tolist()),
        })

    failed = s[s.failed == 1]
    quarter = failed.last_date.dt.to_period("Q")
    all_quarters = pd.period_range(s.first_date.min().to_period("Q"), s.last_date.max().to_period("Q"), freq="Q")
    counts = (failed.groupby([quarter, failed.rpm_class]).size()
              .unstack(fill_value=0)
              .reindex(index=all_quarters, columns=classes, fill_value=0))

    return {
        "quarters": [f"{p.year} Q{p.quarter}" for p in all_quarters],
        "series": {cls: [int(v) for v in counts[cls]] for cls in classes},
        "summary": summary,
        "meta": {
            "sample_file": sample_path.name,
            "drives": int(len(s)),
            "failures": int(s.failed.sum()),
            "first_seen_min": str(s.first_date.min().date()),
            "first_seen_max": str(s.first_date.max().date()),
            "data_end": str(s.last_date.max().date()),
            "generated": str(date.today()),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=Path, default=Path("sample.parquet"))
    ap.add_argument("--out", type=Path, default=Path("website/index.html"))
    args = ap.parse_args()

    data = build_data(args.sample)
    # Escape "</" so a value can never close the <script> tag the JSON sits in.
    payload = json.dumps(data).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    m = data["meta"]
    print(f"Wrote {args.out} from {args.sample}: {m['drives']:,} drives, {m['failures']:,} failures, "
          f"{len(data['quarters'])} quarters")


if __name__ == "__main__":
    main()
