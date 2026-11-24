"""Fit the RPM models (MODELS.md M1-M4) to the RPM samples.

    python modeling/rpm_models.py

Reads rpm_analysis/sample.parquet (main, era-matched) and sample_all_eras.parquet.
Writes to data/models/:
  rpm_afr.csv        M1  AFR + 95% CI per class, per maker+class, per model
  rpm_rate_ratio.csv M2  rate ratios + M3 log-rank p-values for the planned comparisons
  rpm_weibull.csv    M4  Weibull k, lam, median and B10 life per class and per maker+class
  rpm_km.csv         M3  Kaplan-Meier curves per class and per maker+class
"""
from pathlib import Path

import pandas as pd

from reliability import afr_ci, fit_weibull, intervals, km, logrank, rate_ratio

REPO = Path(__file__).resolve().parent.parent
SAMPLES = {"main": REPO / "rpm_analysis/sample.parquet",
           "all_eras": REPO / "rpm_analysis/sample_all_eras.parquet"}
OUT = REPO / "data/models"

# (label, group 1, reference group 0). A group is (manufacturer or None, rpm_class).
COMPARISONS = [
    ("HGST 7200 vs HGST 5700", ("HGST", "7200"), ("HGST", "5700")),
    ("Seagate 7200 vs Seagate 5900", ("Seagate", "7200"), ("Seagate", "5900")),
    ("5900 vs 5700 (all makers, confounded)", (None, "5900"), (None, "5700")),
    ("7200 vs 5700 (all makers, confounded)", (None, "7200"), (None, "5700")),
]


def load(path: Path) -> pd.DataFrame:
    d = pd.read_parquet(path)
    d["rpm_class"] = d["rpm_class"].astype(str)
    iv = intervals(d)
    return d.loc[iv.index].join(iv)


def pick(d, maker, cls):
    m = d.rpm_class == cls
    if maker:
        m &= d.manufacturer == maker
    return d[m]


def afr_row(g: pd.DataFrame) -> dict:
    f, e = g.d.sum(), (g.t - g.a).sum()
    afr, lo, hi = afr_ci(f, e)
    return {"drives": len(g), "failures": int(f), "drive_years": round(e, 1),
            "afr_pct": 100 * afr, "afr_low_pct": 100 * lo, "afr_high_pct": 100 * hi}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    afr, rr, wb, curves = [], [], [], []

    for sample, path in SAMPLES.items():
        d = load(path)
        groupings = {"class": ["rpm_class"], "maker_class": ["manufacturer", "rpm_class"],
                     "model": ["manufacturer", "rpm_class", "model"]}
        for level, cols in groupings.items():
            for key, g in d.groupby(cols):
                key = dict(zip(cols, key if isinstance(key, tuple) else (key,)))
                afr.append({"sample": sample, "level": level, **key, **afr_row(g)})
                if level == "model" or g.d.sum() < 10:
                    continue
                w = fit_weibull(g)
                wb.append({"sample": sample, "level": level, **key,
                           **{k: v for k, v in w.items() if k != "cov_log"}})
                c = km(g)
                curves.append(c.assign(sample=sample, level=level, **key))

        for label, (m1, c1), (m0, c0) in COMPARISONS:
            g1, g0 = pick(d, m1, c1), pick(d, m0, c0)
            if g1.d.sum() == 0 or g0.d.sum() == 0:
                continue
            ratio, lo, hi = rate_ratio(g1.d.sum(), (g1.t - g1.a).sum(), g0.d.sum(), (g0.t - g0.a).sum())
            rr.append({"sample": sample, "comparison": label,
                       "failures_1": int(g1.d.sum()), "failures_0": int(g0.d.sum()),
                       "rate_ratio": ratio, "rr_low": lo, "rr_high": hi,
                       "logrank_p": logrank(g1, g0)})

    for name, rows in [("rpm_afr", afr), ("rpm_rate_ratio", rr), ("rpm_weibull", wb)]:
        pd.DataFrame(rows).round(4).to_csv(OUT / f"{name}.csv", index=False)
    pd.concat(curves).round(5).to_csv(OUT / "rpm_km.csv", index=False)

    show = pd.DataFrame(afr)
    print(show[show.level == "class"][["sample", "rpm_class", "drives", "failures", "drive_years",
                                       "afr_pct", "afr_low_pct", "afr_high_pct"]].round(2).to_string(index=False))
    print()
    print(pd.DataFrame(rr).round(3).to_string(index=False))
    print()
    w = pd.DataFrame(wb)
    print(w[["sample", "level", "manufacturer", "rpm_class", "k", "k_low", "k_high", "median_life", "b10_life"]]
          .round(2).to_string(index=False))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
