"""Build a small website that shows the sample: failures over time and the failure rate per RPM class.

Reads the sample (default sample.parquet), counts failures per calendar quarter for each speed
class, computes each class's annualized failure rate, and writes one page plus its data file
(index.html -> index.data.js). The page also loads app.js and style.css, which must sit in the
same folder (../site/rpm/).

A drive's failure date is the last day it reported (Backblaze marks failure = 1 on that day).
AFR = failures / drive-years, where drive-years = days observed / 365.

Each class also gets the piecewise-constant rate model from MODELS.md (one failure rate per
drive-age interval): the expected cumulative failures per quarter and a 95% Poisson range, drawn as
a line and shaded range behind the dots, plus each interval's rate for the cards. The sample needs a
first_poh column (power-on hours at the first report).

Usage:
    python make_website.py [--sample sample.parquet] [--out ../site/rpm/index.html]
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "modeling"))
from reliability import HOURS_PER_YEAR, piecewise_curve  # noqa: E402

TEMPLATE = Path(__file__).with_name("website_template.html")

# Notes shown next to a model in a card's model list, e.g. for a known-bad model.
# Rates are from data/samples/model_totals.csv (every drive, not just the sample).
MODEL_NOTES = {
    "ST31500541AS": "an old 1.5 TB Seagate (2013-2018) that failed roughly 10% a year",
}


def build_data(s: pd.DataFrame, sample_name: str, by: str = "rpm_class", order: list | None = None) -> dict:
    """Page data for a sample, or any subset of one. sample_name is shown in the footer.

    Each value of column `by` becomes one series (a card and a dot color). The default is the
    RPM class, sorted by speed; pass `order` to group by something else, in that order.
    """
    s = s.copy()  # the date conversions below shouldn't leak into the caller's frame
    s["first_date"] = pd.to_datetime(s.first_date)
    s["last_date"] = pd.to_datetime(s.last_date)
    present = set(s[by].unique())
    classes = [c for c in order if c in present] if order else sorted(present, key=int)

    summary = []
    for cls in classes:
        g = s[s[by] == cls]
        drive_years = g.days.sum() / 365
        failures = int(g.failed.sum())
        models = sorted(g.model.unique().tolist())
        summary.append({
            "rpm": cls,  # the series key; app.js reads it as "rpm" whatever `by` is
            "drives": int(len(g)),
            "failures": failures,
            "drive_years": round(float(drive_years), 1),
            "afr": round(100 * failures / drive_years, 2),
            "models": models,
            "model_notes": {m: MODEL_NOTES[m] for m in models if m in MODEL_NOTES},
        })

    failed = s[s.failed == 1]
    quarter = failed.last_date.dt.to_period("Q")
    all_quarters = pd.period_range(s.first_date.min().to_period("Q"), s.last_date.max().to_period("Q"), freq="Q")
    counts = (failed.groupby([quarter, failed[by]]).size()
              .unstack(fill_value=0)
              .reindex(index=all_quarters, columns=classes, fill_value=0))

    # Piecewise-constant rate model (MODELS.md): one failure rate per drive-age interval, per class.
    # A drive's age = power-on hours at its first report + calendar time since. Day numbers
    # count from 1970-01-01; a drive is at risk from first_date to the day after last_date.
    to_day = lambda x: np.asarray(x, dtype="datetime64[D]").astype(np.int64)
    q_start = to_day(all_quarters.start_time)
    q_end = to_day(all_quarters.end_time) + 1
    model = {}
    for cls in classes:
        g = s[s[by] == cls]
        curve = piecewise_curve(g.first_poh.to_numpy() / HOURS_PER_YEAR, to_day(g.first_date),
                                to_day(g.last_date) + 1, g.failed.to_numpy(), q_start, q_end)
        model[cls] = {
            "expected": [round(float(v), 1) for v in curve["expected"]],
            "low": [int(v) for v in curve["low"]],
            "high": [int(v) for v in curve["high"]],
            "intervals": [{"from": float(b.age_from), "to": None if np.isinf(b.age_to) else float(b.age_to),
                       "failures": int(b.failures), "drive_years": round(float(b.drive_years), 1),
                       "rate": None if np.isnan(b.rate) else round(100 * b.rate, 2),
                       "low": None if np.isnan(b.rate_low) else round(100 * b.rate_low, 2),
                       "high": None if np.isnan(b.rate_high) else round(100 * b.rate_high, 2)}
                      for b in curve["rates"].itertuples()],
        }

    return {
        "quarters": [f"{p.year} Q{p.quarter}" for p in all_quarters],
        "series": {cls: [int(v) for v in counts[cls]] for cls in classes},
        "model": model,
        "summary": summary,
        "meta": {
            "sample_file": sample_name,
            "drives": int(len(s)),
            "failures": int(s.failed.sum()),
            "first_seen_min": str(s.first_date.min().date()),
            "first_seen_max": str(s.first_date.max().date()),
            "data_end": str(s.last_date.max().date()),
            "generated": str(date.today()),
        },
    }


def write_page(data: dict, out: Path, template: str) -> Path:
    """Write the page and its data file (out.html -> out.data.js). Returns the data file's path.

    The data goes in a .js file (not .json) so the page still works when opened straight from disk.
    """
    data_file = out.with_suffix(".data.js")
    out.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text(f"window.DATA = {json.dumps(data)};\n", encoding="utf-8")
    out.write_text(template.replace("__DATA_FILE__", data_file.name), encoding="utf-8")
    return data_file


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=Path, default=Path("sample.parquet"))
    ap.add_argument("--out", type=Path, default=Path("../site/rpm/index.html"))
    args = ap.parse_args()

    data = build_data(pd.read_parquet(args.sample), args.sample.name)
    data_file = write_page(data, args.out, TEMPLATE.read_text(encoding="utf-8"))
    m = data["meta"]
    print(f"Wrote {args.out} and {data_file.name} from {args.sample}: {m['drives']:,} drives, {m['failures']:,} failures, "
          f"{len(data['quarters'])} quarters")


if __name__ == "__main__":
    main()
