"""Split the samples by manufacturer into data/samples/by_maker/.

Writes <maker>_failed.csv, <maker>_hdd_random.csv and <maker>_model_totals.csv
for Seagate, Western Digital (wd) and Toshiba. HDDs only; other makers are dropped.

Run build_samples.py first. No database connection needed.
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
SAMPLES = DATA / "samples"
OUT = SAMPLES / "by_maker"

MAKERS = {"Seagate": "seagate", "Western Digital": "wd", "Toshiba": "toshiba"}
FILES = {
    "failed": "failed_1000.csv",
    "hdd_random": "hdd_random_1000.csv",
    "model_totals": "model_totals.csv",
}


def main():
    makers = pd.read_csv(DATA / "drive_models.csv", usecols=["model", "manufacturer"])
    OUT.mkdir(parents=True, exist_ok=True)

    for name, file in FILES.items():
        df = pd.read_csv(SAMPLES / file).merge(makers, on="model", how="left")
        df = df[df.drive_type == "HDD"]
        for maker, short in MAKERS.items():
            part = df[df.manufacturer == maker]
            part.to_csv(OUT / f"{short}_{name}.csv", index=False)
            print(f"{short}_{name}.csv: {len(part)} rows")


if __name__ == "__main__":
    main()
