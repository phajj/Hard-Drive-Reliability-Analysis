"""Draw a stratified sample of drives by speed class, stratified by model within each class.

Each RPM value (5700, 5900, 7200) is its own class. Each class gets DRIVES_PER_CLASS drives
(set near the top of this file; --per-class overrides it for a single run),
split across its models in proportion to their population (proportional stratified
sampling), so each model's share of the class matches the full dataset.

--max-model-share optionally caps any single model's share of its class (default 1.0 = no
cap). A cap changes the class's model mix away from the population, so leave it off unless
you deliberately want that.

Era matching: a hard limit on the sample space. Only drives first seen in the data in or before
LATEST_MODEL_YEAR can be sampled; every later drive is removed, including later-added drives of
older models. Each model's share of its class is then based on its eligible drives only.
--latest-model-year overrides the year for one run; --all-eras disables the limit (writes the
all-era comparison sample).

Models in --exclude-models are dropped before sampling. The defaults are:
  ST3000DM001   28% annualized failure rate; a problem with that model, not a spin-speed effect
  WDC WD30EFRX  the only 5400 RPM model with 1,000+ drives; a one-model class can't separate
                speed from that model's quality

Usage:
    python sample_by_rpm.py                                          # era-matched -> sample.parquet
    python sample_by_rpm.py --all-eras --out sample_all_eras.parquet # all eras
  options: [--per-class N] [--latest-model-year YEAR] [--max-model-share 1.0] [--seed 42]
           [--exclude-models ST3000DM001 "WDC WD30EFRX" ...]
"""
import argparse
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

# ---- Main settings: change these to reshape the sample -----------------------------------------
DRIVES_PER_CLASS = 5000   # drives sampled per speed class (3 classes -> 15,000 drives in total)
LATEST_MODEL_YEAR = 2016  # era matching, a hard limit: no drive first seen in the data after this
                          # year can be sampled, whatever its model. Keeps every class to the same
                          # drive generation. --all-eras turns it off.
# -----------------------------------------------------------------------------------------------

MAX_PLAUSIBLE_HOURS = 15 * 8760  # drop drives reporting more than 15 years of power-on time
DEFAULT_EXCLUDED = [
    "ST3000DM001",   # 28% AFR outlier (model-specific problem); see RPM_ANALYSIS.md
    "WDC WD30EFRX",  # only 5400 RPM model with 1,000+ drives; see RPM_ANALYSIS.md
]


def manufacturer(model: str) -> str:
    if model.startswith(("ST", "Seagate")):
        return "Seagate"
    if model.startswith("WDC"):
        return "WDC"
    if model.startswith("TOSHIBA"):
        return "Toshiba"
    if re.match(r"^H[A-Z]{2}\d", model):
        return "HGST"
    return "Other"


def allocate(counts: pd.Series, n: int, max_share: float) -> pd.Series:
    """Split n across models proportionally to counts, capping each model at max_share * n
    (and at its population size). Capped-off slots go to the uncapped models."""
    n = min(n, int(counts.sum()))
    limit = np.minimum(counts, math.floor(max_share * n)).astype(float)
    alloc = pd.Series(0.0, index=counts.index)
    free = list(counts.index)
    remaining = float(n)
    while free and remaining > 0:
        share = remaining * counts[free] / counts[free].sum()
        over = share[share >= limit[free]].index
        if len(over) == 0:
            alloc[free] = share
            break
        alloc[over] = limit[over]
        remaining -= limit[over].sum()
        free = [m for m in free if m not in over]

    # round to integers while keeping the total (largest remainder), never above the limit
    base = np.floor(alloc).astype(int)
    short = int(round(alloc.sum())) - base.sum()
    room = (limit - base) > 0
    order = (alloc - base)[room].sort_values(ascending=False).index[:max(short, 0)]
    base[order] += 1
    return base


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drives", type=Path, default=Path("drives.parquet"))
    ap.add_argument("--labels", type=Path, default=Path("models_to_label.csv"))
    ap.add_argument("--out", type=Path, default=Path("sample.parquet"))
    ap.add_argument("--per-class", type=int, default=DRIVES_PER_CLASS,
                    help=f"drives per speed class (default: DRIVES_PER_CLASS = {DRIVES_PER_CLASS})")
    ap.add_argument("--latest-model-year", type=int, default=LATEST_MODEL_YEAR,
                    help=f"only drives first seen in or before this year (default: LATEST_MODEL_YEAR = {LATEST_MODEL_YEAR})")
    ap.add_argument("--all-eras", action="store_true",
                    help="disable era matching: drives from every year are eligible")
    ap.add_argument("--max-model-share", type=float, default=1.0,
                    help="cap on one model's share of its class (1.0 = no cap, fully proportional)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--exclude-models", nargs="*", default=DEFAULT_EXCLUDED,
                    help="models to drop before sampling (pass with no values to exclude nothing)")
    args = ap.parse_args()

    labels = pd.read_csv(args.labels)
    labels["rpm"] = pd.to_numeric(labels["rpm"], errors="coerce")
    labels = labels.dropna(subset=["rpm"])[["model", "rpm"]]
    if labels.empty:
        raise SystemExit(f"No RPM values filled in {args.labels}. Label the models first.")

    d = pd.read_parquet(args.drives).merge(labels, on="model", how="inner")
    if args.exclude_models:
        dropped = d.model.isin(args.exclude_models)
        print(f"Excluded models {args.exclude_models}: {dropped.sum():,} drives removed")
        d = d[~dropped]

    # era matching: a hard limit on the sample space. Every drive first seen after the cutoff
    # year is removed, whatever its model (so later-added drives of older models are dropped too,
    # and models that first appear after the cutoff disappear entirely).
    if args.all_eras:
        print("Era matching OFF: drives from all years are eligible")
    else:
        drive_year = pd.to_datetime(d.first_date).dt.year
        late = drive_year > args.latest_model_year
        models_before = d.model.nunique()
        d = d[~late]
        print(f"Era matching ON: only drives first seen by {args.latest_model_year} are eligible; "
              f"removed {late.sum():,} later drives ({models_before - d.model.nunique()} models left "
              f"with no eligible drives)")
    if d.empty:
        raise SystemExit("No drives left after exclusions and era filter.")
    before = len(d)
    d = d[d.first_poh.notna() & d.last_poh.notna()
          & (d.first_poh >= 0) & (d.last_poh >= d.first_poh)
          & (d.last_poh < MAX_PLAUSIBLE_HOURS)]
    print(f"Labeled drives: {before:,}; usable power-on hours: {len(d):,}")

    # fixed row order, so the same seed always draws the same drives
    d = d.sort_values("serial_number", kind="stable").reset_index(drop=True)
    d["rpm"] = d.rpm.astype(int)
    d["rpm_class"] = d.rpm.astype(str)  # each speed is its own class: "5700", "5900", "7200"
    d["capacity_tb"] = (d.capacity_bytes / 1e12).round()
    d["deploy_year"] = pd.to_datetime(d.first_date).dt.year
    d["manufacturer"] = d.model.map(manufacturer)

    parts = []
    for cls, g in d.groupby("rpm_class"):
        counts = g.model.value_counts()
        if len(counts) == 1:
            print(f"WARNING: class {cls} has only one model ({counts.index[0]}); "
                  "RPM will be indistinguishable from that model's quality.")
            alloc = pd.Series({counts.index[0]: min(args.per_class, counts.iloc[0])})
        else:
            alloc = allocate(counts, args.per_class, args.max_model_share)
        if alloc.sum() < args.per_class:
            print(f"WARNING: class {cls} only yields {alloc.sum()} drives "
                  f"(population/cap limits); requested {args.per_class}.")
        for model, k in alloc.items():
            if k > 0:
                parts.append(g[g.model == model].sample(n=int(k), random_state=args.seed))
    s = pd.concat(parts, ignore_index=True)
    s.to_parquet(args.out, index=False)

    # model mix: population vs sample (differs only where the cap kicked in)
    mix = pd.concat({
        "population_share": d.groupby("rpm_class").model.value_counts(normalize=True),
        "sample_share": s.groupby("rpm_class").model.value_counts(normalize=True),
        "sample_n": s.groupby("rpm_class").model.value_counts(),
    }, axis=1).fillna(0).round(3)
    print("\nModel mix by class:\n", mix.to_string())

    summ = s.groupby("rpm_class").agg(
        drives=("serial_number", "size"),
        models=("model", "nunique"),
        failures=("failed", "sum"),
        drive_years=("days", lambda x: x.sum() / 365),
    )
    summ["afr_pct"] = 100 * summ.failures / summ.drive_years
    print("\nSample summary:\n", summ.round(2).to_string())

    # era check: when each sampled drive first appears, and its capacity, by class
    era = pd.cut(s.deploy_year, [0, 2015, 2018, 2021, 9999], labels=["<=2015", "2016-18", "2019-21", "2022+"])
    era_tab = (pd.crosstab(s.rpm_class, era, normalize="index") * 100).round(1)
    era_tab["median_tb"] = s.groupby("rpm_class").capacity_tb.median()
    print("\nEra check (% of drives by year first seen; median capacity):\n", era_tab.to_string())

    # Smallest hazard ratio detectable vs. the slowest class, 80% power, alpha = 0.05.
    # Optimistic: it ignores clustering by model, which widens the real uncertainty.
    ref = min(summ.index, key=int)
    if summ.loc[ref, "failures"] > 0:
        print()
        for cls in sorted(summ.index, key=int):
            if cls != ref and summ.loc[cls, "failures"] > 0:
                se = math.sqrt(1 / summ.loc[ref, "failures"] + 1 / summ.loc[cls, "failures"])
                print(f"Minimum detectable hazard ratio, {cls} vs {ref} RPM (80% power): ~{math.exp(2.8 * se):.2f}x")
    print(f"\nWrote {len(s):,} drives to {args.out}")


if __name__ == "__main__":
    main()
