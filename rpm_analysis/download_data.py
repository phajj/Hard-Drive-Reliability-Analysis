"""Download the Backblaze hard drive data zips (2013 onward).

Files that are already fully downloaded are skipped, so re-running resumes where it
left off and picks up newly published quarters. Each file downloads to a .part file
first and is renamed only when its size matches the server's.

Usage:
    python download_data.py [--dest data/zips] [--from-year 2013] [--to-year 2026]
"""
import argparse
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/"
YEARLY = (2013, 2014, 2015)  # before 2016, Backblaze published one zip per year


def file_names(first: int, last: int) -> list[str]:
    names = [f"data_{y}" for y in YEARLY if first <= y <= last]
    for y in range(max(first, 2016), last + 1):
        names += [f"data_Q{q}_{y}" for q in range(1, 5)]
    return names


def remote_size(url: str):
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return int(r.headers["Content-Length"])
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # not published (yet)
        raise


def download(url: str, dest: Path, size: int, retries: int = 3) -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
                got, last_report = 0, time.time()
                while chunk := r.read(1 << 20):
                    f.write(chunk)
                    got += len(chunk)
                    if time.time() - last_report > 15:
                        print(f"    {got / size:5.1%} of {size / 2**20:,.0f} MB", flush=True)
                        last_report = time.time()
            if part.stat().st_size != size:
                raise IOError(f"size mismatch: got {part.stat().st_size}, expected {size}")
            part.replace(dest)
            return
        except Exception as e:
            print(f"    attempt {attempt} failed: {e}", flush=True)
            time.sleep(5 * attempt)
    part.unlink(missing_ok=True)
    raise RuntimeError(f"giving up on {url}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", type=Path, default=Path("data/zips"))
    ap.add_argument("--from-year", type=int, default=2013)
    ap.add_argument("--to-year", type=int, default=time.localtime().tm_year)
    args = ap.parse_args()
    args.dest.mkdir(parents=True, exist_ok=True)

    names = file_names(args.from_year, args.to_year)
    ok = skipped = unpublished = failed = 0
    for i, name in enumerate(names, 1):
        url, dest = f"{BASE}{name}.zip", args.dest / f"{name}.zip"
        tag = f"[{i}/{len(names)}] {name}.zip"
        try:
            size = remote_size(url)
            if size is None:
                print(f"{tag}: not published yet")
                unpublished += 1
                continue
            if dest.exists() and dest.stat().st_size == size:
                print(f"{tag}: already downloaded")
                skipped += 1
                continue
            print(f"{tag}: downloading {size / 2**20:,.0f} MB", flush=True)
            t0 = time.time()
            download(url, dest, size)
            print(f"{tag}: done in {time.time() - t0:.0f}s", flush=True)
            ok += 1
        except Exception as e:
            print(f"{tag}: FAILED ({e})", flush=True)
            failed += 1

    print(f"\nDownloaded {ok}, already had {skipped}, not published {unpublished}, failed {failed}.")
    if failed:
        print("Re-run the same command to retry the failed files.")


if __name__ == "__main__":
    main()
