"""Scatter of power-on hours at failure vs first day in the data, for one manufacturer.

Usage, from scripts/:  python plot_makers.py seagate   (or wd, toshiba)

Reads data/samples/by_maker/<maker>_failed.csv (run split_by_maker.py first) and writes:
- plots/manufacturers/<maker>_scatter.png
- site/manufacturers/<maker>.data.js   (drawn by site/manufacturers/app.js)

Drives with suspect power-on hours are left out. All makers share the same axes so the
plots can be compared side by side.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NAMES = {"seagate": "Seagate", "wd": "Western Digital", "toshiba": "Toshiba"}
HOURS_PER_YEAR = 8766

# Shared axes
X_RANGE = (pd.Timestamp("2013-01-01"), pd.Timestamp("2027-01-01"))
Y_MAX = 10  # years

# Capacity groups, light to dark blue (checked with the dataviz palette validator)
BINS = [  # (label, upper bound in TB, light color, dark color)
    ("Under 4 TB", 3.5, "#86b6ef", "#184f95"),
    ("4–6 TB", 7, "#3987e5", "#2a78d6"),
    ("8–12 TB", 13, "#256abf", "#5598e7"),
    ("14–16 TB", 17, "#184f95", "#9ec5f4"),
    ("18 TB+", 999, "#0d366b", "#cde2fb"),
]


def cap_group(tb):
    return next(i for i, b in enumerate(BINS) if tb < b[1])


def load(maker):
    df = pd.read_csv(ROOT / "data/samples/by_maker" / f"{maker}_failed.csv")
    df = df[~df.poh_suspect].copy()
    df["tb"] = df.capacity_bytes / 1e12
    df["group"] = df.tb.map(cap_group)
    df["years"] = df.poh_last / HOURS_PER_YEAR
    df["first_date"] = pd.to_datetime(df.first_date)
    return df


def save_png(df, maker):
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    ax.set_facecolor("#fcfcfb")
    fig.patch.set_facecolor("#fcfcfb")
    for i, (label, _, color, _) in enumerate(BINS):
        g = df[df.group == i]
        if len(g):
            ax.scatter(g.first_date, g.years, s=22, color=color, edgecolors="#fcfcfb",
                       linewidths=0.6, label=f"{label} ({len(g)})", zorder=2)
    ax.set_xlim(*X_RANGE)
    ax.set_ylim(0, Y_MAX)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", color="#e1e0d9", linewidth=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#898781")
    ax.tick_params(colors="#52514e", length=0)
    ax.set_xlabel("First day in the data", color="#52514e")
    ax.set_ylabel("Power-on time at failure (years)", color="#52514e")
    ax.set_title(f"{NAMES[maker]}: {len(df)} failed drives", loc="left",
                 color="#0b0b0b", fontsize=13, fontweight="bold")
    ax.legend(title="Capacity", frameon=False, loc="upper right", fontsize=9, title_fontsize=9)
    out = ROOT / "plots/manufacturers" / f"{maker}_scatter.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out)
    print(f"wrote {out.relative_to(ROOT)}")


def save_data_js(df, maker):
    points = [
        [r.model, round(r.tb, 1), r.first_date.strftime("%Y-%m-%d"), round(r.years, 3), r.group]
        for r in df.sort_values("first_date").itertuples()
    ]
    data = {
        "maker": maker,
        "name": NAMES[maker],
        "fields": ["model", "tb", "first_date", "years", "group"],
        "points": points,
    }
    out = ROOT / "site/manufacturers" / f"{maker}.data.js"
    out.write_text(
        f"window.MAKERS = window.MAKERS || [];\nwindow.MAKERS.push({json.dumps(data)});\n",
        encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(points)} drives)")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in NAMES:
        sys.exit(f"usage: python plot_makers.py {{{','.join(NAMES)}}}")
    maker = sys.argv[1]
    df = load(maker)
    save_png(df, maker)
    save_data_js(df, maker)


if __name__ == "__main__":
    main()
