# Analysis Plan

## The samples
All in `data/samples/`, built by `scripts/build_samples.py`. Drives are picked at random but with a fixed seed, so rerunning gives the same drives.

| File | What's in it |
|---|---|
| `failed_1000.csv` | 1000 random drives that failed. Our main sample. |
| `hdd_random_1000.csv` | 1000 random data HDDs (the ones that store customer data), failed or not |
| `model_totals.csv` | Every model: number of drives, failures, drive-days and drive-hours. Used for failure rates. |
| `by_maker/<maker>_<sample>.csv` | The three files above split by maker (`seagate`, `wd`, `toshiba`), HDDs only, with a `manufacturer` column. Made by `scripts/split_by_maker.py`. |

We only analyze HDDs. `failed_1000.csv` can include a few SSDs, so filter to `drive_type = HDD`.

The 1000 failed drives only tell us how long drives lasted *when* they failed. To compare how *often* models fail we also need the drives that didn't fail, which is what `model_totals.csv` is for.

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
   - Run every model on Seagate, Western Digital and Toshiba separately, then compare the three. The `manufacturer` column in `data/drive_models.csv` says which is which (join on `model`). HGST and Hitachi count as WD; other makers are left out.
   - HDD drive-days by maker: Seagate 48%, Western Digital 30% (12% WDC + 16% HGST + 2% Hitachi), Toshiba 21%.
2. **Spin speed (RPM).** RPM isn't in the data. We'll make `data/model_specs.csv` by hand from spec sheets for the models that show up, then check whether RPM lines up with failure rate.
3. **Seagate vs Western Digital vs Toshiba.** Put the per-manufacturer results from step 1 side by side.
   - Compare power-on hours at failure and failures per drive-year for each maker.
   - Since most drives haven't failed, compare survival curves rather than plain averages.
   - Makers bought different models in different years, so compare drives of similar age and capacity where we can. Otherwise a maker difference may really be an era difference.
