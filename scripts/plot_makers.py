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
matplotlib.use("Agg")  # render straight to file; no display needed
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# CLI name -> display name. The CLI names match the by_maker/ file prefixes.
NAMES = {"seagate": "Seagate", "wd": "Western Digital", "toshiba": "Toshiba"}

HOURS_PER_YEAR = 8766  # 365.25 * 24

# Shared axes, fixed rather than fit to the data so every maker's chart lines up.
# Keep in sync with X0, X1 and Y_MAX in site/manufacturers/app.js.
X_RANGE = (pd.Timestamp("2013-01-01"), pd.Timestamp("2027-01-01"))
Y_MAX = 10  # years; the longest-lived drive in the sample is ~8.8

# Capacity groups as (label, upper bound in TB, color). A drive goes in the first group
# whose bound is above its capacity. Bounds sit between the nominal sizes (3 vs 4 TB,
# 6 vs 8, ...) so decimal capacities like 4.0008 TB land in the right group.
# Colors are a light-to-dark blue ramp that passed the dataviz palette validator. The
# website uses the same ramp (plus a dark-mode version) in site/manufacturers/style.css,
# and a group's index here is its index in GROUPS in app.js.
BINS = [
    ("Under 4 TB", 3.5, "#86b6ef"),
    ("4–6 TB", 7, "#3987e5"),
    ("8–12 TB", 13, "#256abf"),
    ("14–16 TB", 17, "#184f95"),
    ("18 TB+", float("inf"), "#0d366b"),
]

# Chart chrome, matching the site's light theme.
SURFACE = "#fcfcfb"
GRID = "#e1e0d9"
AXIS = "#898781"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"


def cap_group(tb):
    """Index into BINS for a capacity in TB."""
    return next(i for i, (_, upper, _) in enumerate(BINS) if tb < upper)


def load(maker):
    """Failed drives for one maker, with the columns both outputs need."""
    df = pd.read_csv(ROOT / "data/samples/by_maker" / f"{maker}_failed.csv")
    df = df[~df.poh_suspect].copy()
    df["tb"] = df.capacity_bytes / 1e12  # decimal TB, as drives are sold
    df["group"] = df.tb.map(cap_group)
    df["years"] = df.poh_last / HOURS_PER_YEAR
    df["first_date"] = pd.to_datetime(df.first_date)
    return df


def save_png(df, maker):
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    ax.set_facecolor(SURFACE)
    fig.patch.set_facecolor(SURFACE)

    # One scatter call per group so each gets its own legend entry. Empty groups are
    # skipped, which keeps them out of the legend too.
    for i, (label, _, color) in enumerate(BINS):
        g = df[df.group == i]
        if len(g):
            # The surface-colored edge separates overlapping dots.
            ax.scatter(g.first_date, g.years, s=22, color=color, edgecolors=SURFACE,
                       linewidths=0.6, label=f"{label} ({len(g)})", zorder=2)

    ax.set_xlim(*X_RANGE)
    ax.set_ylim(0, Y_MAX)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # Light horizontal grid and a single baseline; the other spines are noise.
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=TEXT_2, length=0)

    ax.set_xlabel("First day in the data", color=TEXT_2)
    ax.set_ylabel("Power-on time at failure (years)", color=TEXT_2)
    ax.set_title(f"{NAMES[maker]}: {len(df)} failed drives", loc="left",
                 color=TEXT, fontsize=13, fontweight="bold")
    # Upper right stays empty on every chart: new drives can't have run for long yet.
    ax.legend(title="Capacity", frameon=False, loc="upper right", fontsize=9, title_fontsize=9)

    out = ROOT / "plots/manufacturers" / f"{maker}_scatter.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def save_data_js(df, maker):
    """Write the chart data as a script that adds itself to window.MAKERS.

    A <script> file rather than JSON so the page works without fetch(). Points are
    arrays in the order given by "fields" instead of objects, which keeps the file
    about half the size.
    """
    # Oldest first: SVG draws later elements on top, so newer drives stay visible
    # where the clusters overlap.
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
    # Each maker's file pushes onto a shared array, so the page can load any subset
    # of them in any order.
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
