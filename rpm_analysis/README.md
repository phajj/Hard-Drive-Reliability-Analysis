# Hard drive spin speed vs. failure (Backblaze 2013–2026)

Hypothesis: faster-spinning drives (7200 RPM) fail sooner / wear out faster than slower ones (5700–5900 RPM).

The approach: reduce the full Backblaze dataset to one row per drive, label each model's RPM,
draw a stratified sample of drives per speed class (5700, 5900 and 7200, each kept separate), and
run survival analysis with drive age (SMART 9, power-on hours) as the time axis.

**For the analysis itself (speed classes, model table, exclusions, confounding, what we can
claim), see [RPM_ANALYSIS.md](RPM_ANALYSIS.md).** This file covers how to run the pipeline.

> **Excluded by default** (see RPM_ANALYSIS.md):
> - **ST3000DM001** (7200 RPM, 28% annualized failure rate): its failures reflect a problem with
>   that model, not spin speed.
> - **WDC WD30EFRX**: the only 5400 RPM model with 1,000+ drives, so 5400 RPM isn't analyzed.

## Setup

This folder uses the repo's shared venv and `requirements.txt` (in the repo root). From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
cd rpm_analysis
```

Run every command below from inside `rpm_analysis/` with that venv active.
Unlike the rest of the repo, this pipeline downloads the full dataset (about 34 GB) instead of
querying Backblaze's hosted copy, so it needs no access keys.

## Run order

| Step | Command | Output |
|---|---|---|
| 1. Download | `python download_data.py` (about 34 GB; resumable) | `data/zips/*.zip` |
| 2. Unzip + summarize | `python process_zips.py data\zips` | `summaries/*.parquet` (one per zip) |
| 3. Combine | `python build_drive_table.py` | `drives.parquet` (one row per drive) |
| 4. List models | `python list_models.py --min-drives 1000` | `models_to_label.csv` |
| 5. Label RPM | Already done: `rpm` and `rpm_source` are filled in `models_to_label.csv` | |
| 6a. Sample (main) | `python sample_by_rpm.py` | `sample.parquet`: era-matched, 5,000 drives per class |
| 6b. Sample (all eras) | `python sample_by_rpm.py --all-eras --out sample_all_eras.parquet` | `sample_all_eras.parquet`: comparison sample |
| 7. Website | `python make_website.py` | `website/index.html` (open it in a browser) |

### Step 2 notes
- Each zip is extracted to `work/`, summarized, and the CSVs are deleted, so you only need
  enough free disk space for one unzipped quarter at a time (a few GB).
- You can re-run it whenever you like. Zips already summarized are skipped, so you can stop it, download more, and continue.
- Add `--delete-zips` to delete each zip once it has been summarized successfully.

### Step 5 notes
- The `rpm_hint` column is only a starting point. Verify every model from its spec sheet.
- Leave `rpm` blank for SSDs and anything you want to exclude.
- `list_models.py` refuses to overwrite your labeled file unless you pass `--force`.
- HGST/Hitachi "5C" CoolSpin drives are 5700 RPM even though many listings say 5400. The
  drives report 5700 themselves.

### Step 6 options
- **Sample size** is set by `DRIVES_PER_CLASS` at the top of `sample_by_rpm.py` (default 5,000
  per class × 3 classes = 15,000 drives). Change it there to resize the sample permanently, or
  pass `--per-class N` to override it for a single run.
- **Era matching** is set by `LATEST_MODEL_YEAR` at the top of `sample_by_rpm.py` (default 2016).
  It's a hard limit: no drive first seen in the data after that year can be sampled, whatever
  its model, so all speed classes come from the same drive generation. Change it there, pass `--latest-model-year YEAR` for one
  run, or pass `--all-eras` to turn it off.
- `--exclude-models A B ...`: models to drop (default: `ST3000DM001` and `"WDC WD30EFRX"`).
  Passing the flag replaces the defaults; pass it with no values to exclude nothing.
- `--out FILE`: write the sample somewhere other than `sample.parquet` (useful for sensitivity runs)
- `--max-model-share 1.0` (default, no cap): models are sampled in proportion to their share of
  the class, so the sample's model mix matches the full dataset. A value below 1.0 caps any one
  model's share, which moves the mix away from the population. The script prints the population
  vs. sample model mix so you can confirm they match.
- `--seed 42`: the same seed and the same data always give the same sample.
- The script also prints failures per class, the **minimum detectable hazard ratio**, and an
  **era check** (when each class's drives were first seen, and their median capacity).

### Step 7 notes
- The page shows **cumulative** failures per quarter (dots, one color per RPM class) and each class's AFR.
  It's built from `sample.parquet`. For the all-era sample, run
  `python make_website.py --sample sample_all_eras.parquet --out website/all_eras.html`.
- Re-run it after redrawing the sample.

## Interpreting the results
See [RPM_ANALYSIS.md](RPM_ANALYSIS.md) for what each output means, the confounding problems
in this dataset, and which claims the results can support.

## Testing
`python smoke_test.py` builds synthetic Backblaze-style zips with a known 2× RPM effect, runs the
whole pipeline in a temp folder, and checks the counts. Run it after changing any script.
