"""Build the spin speed page for one manufacturer, for the Seagate vs WD vs Toshiba topic.

Same page as site/rpm/ (failure rate per RPM class and cumulative failures per quarter), but
only that maker's drives from the all-eras sample. The pages reuse site/rpm/app.js and
style.css, so a change to the spin speed page shows up here too.

Usage, from rpm_analysis/:
    python make_maker_pages.py seagate   (or wd, toshiba)

Writes site/manufacturers/<page>.html and <page>.data.js. Seagate is index.html so the
topic opens on it.
"""
import sys
from pathlib import Path

import pandas as pd

from make_website import build_data, write_page

HERE = Path(__file__).parent
SAMPLE = HERE / "sample_all_eras.parquet"
TEMPLATE = HERE / "maker_template.html"
OUT_DIR = HERE.parent / "site" / "manufacturers"

# The sample has its own manufacturer column, which keeps HGST apart from WDC. We count
# HGST (and the Hitachi drives it labels HGST) as Western Digital, like the rest of the repo.
# data/drive_models.csv can't be joined here: the oldest HGST model names in this sample
# don't have the "HGST " prefix that the newer data uses.
MAKERS = {
    # CLI name: (display name, labels in the sample, page file, note under the title)
    "seagate": ("Seagate", ["Seagate"], "index.html", ""),
    "wd": ("Western Digital", ["WDC", "HGST"], "wd.html",
           "HGST and Hitachi count as Western Digital. All the 5700 RPM drives here are HGST."),
    "toshiba": ("Toshiba", ["Toshiba"], "toshiba.html",
                "Every Toshiba model in the data spins at 7200 RPM, so there's no slower "
                "class to compare against. Shown for its failure rate."),
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MAKERS:
        sys.exit(f"usage: python make_maker_pages.py {{{','.join(MAKERS)}}}")
    name, labels, page, note = MAKERS[sys.argv[1]]

    s = pd.read_parquet(SAMPLE)
    s = s[s.manufacturer.isin(labels)]
    data = build_data(s, f"{SAMPLE.name} ({name} drives only)")

    html = TEMPLATE.read_text(encoding="utf-8")
    if not note:
        # Drop the whole note line, so an empty paragraph doesn't add space.
        html = "".join(line for line in html.splitlines(keepends=True) if "__NOTE__" not in line)
    html = html.replace("__MAKER__", name).replace("__NOTE__", note)
    out = OUT_DIR / page
    data_file = write_page(data, out, html)

    print(f"Wrote {out.relative_to(HERE.parent)} and {data_file.name}")
    for c in data["summary"]:
        print(f"  {c['rpm']} RPM: {c['drives']:,} drives, {c['failures']:,} failures, AFR {c['afr']}%")


if __name__ == "__main__":
    main()
