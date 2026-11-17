"""Unzip each Backblaze data zip, summarize it to one row per drive, then delete the CSVs.

Handles both the yearly zips (data_2013.zip ... data_2015.zip) and the quarterly
ones (data_Q1_2016.zip ...). Safe to re-run: zips that already have a summary
are skipped, so you can stop it and continue later, or add new zips as you download them.

Usage:
    python process_zips.py <folder_with_zips> [--summaries summaries] [--work work] [--delete-zips]
"""
import argparse
import shutil
import time
import zipfile
from pathlib import Path

from summarize import summarize_folder


def extract_csvs(zip_path: Path, dest: Path) -> int:
    """Extract only the real daily CSVs (skip macOS metadata files such as __MACOSX/._x.csv)."""
    with zipfile.ZipFile(zip_path) as zf:
        members = [
            m for m in zf.infolist()
            if not m.is_dir()
            and m.filename.lower().endswith(".csv")
            and "__MACOSX" not in m.filename
            and not Path(m.filename).name.startswith("._")
        ]
        for m in members:
            zf.extract(m, dest)
    return len(members)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip_dir", type=Path, help="folder containing the downloaded data_*.zip files")
    ap.add_argument("--summaries", type=Path, default=Path("summaries"), help="output folder for per-zip summaries")
    ap.add_argument("--work", type=Path, default=Path("work"), help="temporary folder for extracted CSVs")
    ap.add_argument("--delete-zips", action="store_true", help="delete each zip after it is summarized successfully")
    args = ap.parse_args()

    zips = sorted(args.zip_dir.glob("*.zip"))
    if not zips:
        raise SystemExit(f"No .zip files found in {args.zip_dir}")
    args.summaries.mkdir(parents=True, exist_ok=True)
    args.work.mkdir(parents=True, exist_ok=True)

    done = skipped = failed = 0
    for i, zp in enumerate(zips, 1):
        out = args.summaries / f"{zp.stem}.parquet"
        tag = f"[{i}/{len(zips)}] {zp.name}"
        if out.exists():
            print(f"{tag}: already summarized, skipping")
            skipped += 1
            continue

        tmp_dir = args.work / zp.stem
        tmp_out = out.with_suffix(".parquet.partial")
        t0 = time.time()
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            n = extract_csvs(zp, tmp_dir)
            if n == 0:
                raise RuntimeError("zip contains no CSV files")
            print(f"{tag}: extracted {n} CSVs, summarizing...")
            summarize_folder(tmp_dir, tmp_out)
            tmp_out.replace(out)  # only a complete summary counts as done
            print(f"{tag}: done in {time.time() - t0:.0f}s -> {out}")
            done += 1
            if args.delete_zips:
                zp.unlink()
        except Exception as e:  # keep going; a re-run retries this zip
            print(f"{tag}: FAILED ({e})")
            tmp_out.unlink(missing_ok=True)
            failed += 1
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"\nSummarized {done}, skipped {skipped}, failed {failed}.")
    if failed:
        print("Re-run the same command to retry the failed zips.")


if __name__ == "__main__":
    main()
