"""Build the pages for the Seagate vs WD vs Toshiba topic (site/manufacturers/).

- One page per maker: the spin speed page (failure rate per RPM class and cumulative failures
  per quarter), but only that maker's drives.
- A comparison page: the same chart with one series per maker, every speed together.

The maker pages use the all-eras sample. The comparison page uses
data/samples/maker_random_2000.csv instead, which has the same number of drives from each
maker (built by scripts/build_samples.py). All pages reuse site/rpm/app.js and style.css, so a
change to the spin speed page shows up here too.

Usage, from rpm_analysis/:
    python make_maker_pages.py seagate   (or wd, toshiba, compare)

Writes site/manufacturers/<page>.html and <page>.data.js. Seagate is index.html so the
topic opens on it.
"""
import sys
from pathlib import Path

import pandas as pd

from make_website import build_data, write_page

HERE = Path(__file__).parent
SAMPLE = HERE / "sample_all_eras.parquet"
COMPARE_SAMPLE = HERE.parent / "data" / "samples" / "maker_random_2000.csv"
TEMPLATE = HERE / "maker_template.html"
OUT_DIR = HERE.parent / "site" / "manufacturers"

# The sample has its own manufacturer column, which keeps HGST apart from WDC. We count
# HGST (and the Hitachi drives it labels HGST) as Western Digital, like the rest of the repo.
# data/drive_models.csv can't be joined here: the oldest HGST model names in this sample
# don't have the "HGST " prefix that the newer data uses.
MAKERS = {
    # key: (display name, labels in the sample, page file, note under the title)
    # The key is also the series key on the comparison page (colors in makers.css).
    "seagate": ("Seagate", ["Seagate"], "index.html", ""),
    "wd": ("Western Digital", ["WDC", "HGST"], "wd.html",
           "HGST and Hitachi count as Western Digital. All the 5700 RPM drives here are HGST."),
    "toshiba": ("Toshiba", ["Toshiba"], "toshiba.html",
                "Every Toshiba model in the data spins at 7200 RPM, so there's no slower "
                "class to compare against. Shown for its failure rate."),
}

COMPARE_NOTE = (
    "2,000 random data drives from each maker, failed or not, all speeds together. We took "
    "the same number from each maker, not the same percentage, so Toshiba's smaller fleet "
    "gets as much weight as Seagate's. This is called stratified sampling with equal "
    "allocation. Each maker bought its drives in different years, so some of the gap "
    "between them comes from drive age.")


def render(heading, note, group, drives):
    """Fill in the page template. `group` names what a series is, e.g. "RPM class"."""
    html = TEMPLATE.read_text(encoding="utf-8")
    if not note:
        # Drop the whole note line, so an empty paragraph doesn't add space.
        html = "".join(line for line in html.splitlines(keepends=True) if "__NOTE__" not in line)
    return (html.replace("__HEADING__", heading).replace("__NOTE__", note)
            .replace("__GROUP__", group).replace("__DRIVES__", drives))


def maker_page(key, s):
    name, labels, page, note = MAKERS[key]
    data = build_data(s[s.manufacturer.isin(labels)], f"{SAMPLE.name} ({name} drives only)")
    data["maker"] = key  # app.js shows this maker's logo on every card
    html = render(f"{name}: drive failures by spin speed", note, "RPM class", f"{name} drives")
    return page, data, html


def compare_page():
    # This sample already uses the repo's maker names (HGST counted as WD).
    to_key = {name: key for key, (name, *_) in MAKERS.items()}
    s = pd.read_csv(COMPARE_SAMPLE)
    s = s.assign(maker=s.manufacturer.map(to_key), days=s.days_observed)
    data = build_data(s, COMPARE_SAMPLE.name, by="maker", order=list(MAKERS))
    data["labels"] = {key: name for key, (name, *_) in MAKERS.items()}
    data["class_noun"] = "manufacturer"
    html = render("Seagate vs Western Digital vs Toshiba", COMPARE_NOTE, "manufacturer", "drives")
    return "compare.html", data, html


def main():
    choices = [*MAKERS, "compare"]
    if len(sys.argv) != 2 or sys.argv[1] not in choices:
        sys.exit(f"usage: python make_maker_pages.py {{{','.join(choices)}}}")
    key = sys.argv[1]
    page, data, html = compare_page() if key == "compare" else maker_page(key, pd.read_parquet(SAMPLE))

    out = OUT_DIR / page
    data_file = write_page(data, out, html)
    print(f"Wrote {out.relative_to(HERE.parent)} and {data_file.name}")
    label = data.get("labels") or {c["rpm"]: f"{c['rpm']} RPM" for c in data["summary"]}
    for c in data["summary"]:
        print(f"  {label[c['rpm']]}: {c['drives']:,} drives, {c['failures']:,} failures, AFR {c['afr']}%")


if __name__ == "__main__":
    main()
