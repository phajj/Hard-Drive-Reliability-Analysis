# Analysis Plan

## The samples
All in `data/samples/`, built by `scripts/build_samples.py`. Drives are picked at random but with a fixed seed, so rerunning gives the same drives.

| File | What's in it |
|---|---|
| `failed_1000.csv` | 1000 random drives that failed. Our main sample. |
| `hdd_random_1000.csv` | 1000 random data HDDs (the ones that store customer data), failed or not |
| `boot_hdd_random_1000.csv` | 1000 random boot HDDs still running on or after Q4 2018, failed or not |
| `ssd_random_1000.csv` | 1000 random SSDs (all boot drives), failed or not |
| `model_totals.csv` | Every model: number of drives, failures, drive-days and drive-hours. Used for failure rates. |

The 1000 failed drives only tell us how long drives lasted *when* they failed. To compare how *often* models fail we also need the drives that didn't fail, which is what `model_totals.csv` is for.

There aren't 1000 failed SSDs in the Backblaze data, so the HDD vs SSD samples are random drives instead. Most of them won't have failed yet.

### Columns in the sample files
- `serial_number`, `model`, `drive_type` (HDD or SSD), `role` (boot or data), `capacity_bytes`, `datacenter`
- `first_date`, `last_date`: first and last day the drive shows up (for failed drives, `last_date` is the day it failed)
- `days_observed`: number of daily reports for the drive
- `failed`: 1 if it failed, 0 if it was still running or was taken out for another reason
- `poh_first`, `poh_last`: power-on hours at the first and last report. **`poh_last` is our measure of drive life.**
- `poh_ratio`: power-on hours gained ÷ hours on the calendar over the same stretch. Should be close to 1.
- `poh_suspect`: true if the power-on hours look off (ratio far from 1, zero, or over 15 years). Check these before using them.

## What we look at first
1. **HDD model vs HDD model.** Power-on hours at failure by model, maker and capacity (from `failed_1000.csv`), and failures per drive-year by model (from `model_totals.csv`). This is the biggest and cleanest part of the data, so it's the place to start.
2. **Spin speed (RPM).** RPM isn't in the data. We'll make `data/model_specs.csv` by hand from spec sheets for the models that show up, then check whether RPM lines up with failure rate.
3. **HDD vs SSD.** Since most drives haven't failed, this needs survival curves rather than plain averages.
   - Main comparison: SSDs vs boot HDDs. Both do the same job (booting the storage servers) over the same years, so the difference is mostly down to the drive type.
   - Second comparison: SSDs vs data HDDs. Data HDDs do much heavier work, so differences here mix drive type with workload.
