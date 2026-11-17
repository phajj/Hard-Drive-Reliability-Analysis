# Spin speed vs. failure rate

**Question:** Does a hard drive's spin speed affect how likely it is to fail, or how long it lasts?

**Hypothesis:** Faster-spinning drives degrade quicker, so they fail sooner. If true, we expect
failure hazard to rise from 5700 → 5900 → 7200 RPM, and the hazard to climb faster with age
at higher speeds.

For how to install and run the pipeline, see [README.md](README.md). This document covers the
analysis itself.

## Data

- **Source:** Backblaze daily drive stats, 10 April 2013 to 30 September 2026 (46 zip files).
- **Population:** 530,430 drives, 34,719 failures, about 2.13 million drive-years, 180 models.
- **How drives are counted:** one drive = one unique serial number, counted once if it appears on
  any day in the period, regardless of how long it was in service. "Drives" is therefore
  every drive that ever appeared, not how many were running at one time. Drive-years measure
  exposure and are what failure rates are based on.
- **Models included:** only models with **1,000+ drives**.
- **Speed labels:** every model's RPM is in `models_to_label.csv`, with an `rpm_source` column
  saying where the value came from (see [How speeds were verified](#how-speeds-were-verified)).

## Speed classes

Each speed is kept as its own class (they are **not** pooled). Population figures for models
with 1,000+ drives (SSDs excluded):

| Speed | Models | Drives | Failures | Capacity | Years in data |
|---|---|---|---|---|---|
| 5700 | 4 | 32,565 | 953 | 3–4 TB | 2013–2026 |
| 5900 | 2 | 39,228 | 6,186 | 1.5–4 TB | 2013–2025 |
| 7200 | 32 | 442,145 | 24,919 | 2–26 TB | 2013–2026 |

The 7200 row includes ST3000DM001, which is excluded from the analysis (see
[Exclusions](#exclusions)). Without it, the 7200 class is 31 models, 437,438 drives and 23,211 failures.

**Raw annualized failure rates** (failures ÷ drive-years, whole population, no adjustment,
excluded models removed):

| Speed | Drive-years | AFR |
|---|---|---|
| 5700 | 189,420 | 0.50% |
| 5900 | 224,244 | 2.76% |
| 7200 | 1,656,429 | 1.40% |

These raw rates do **not** rise with speed. 5900 is highest. They aren't evidence either way yet,
because they don't account for drive age, manufacturer or era. The 5900 class is almost all one
Seagate model (ST4000DM000). Accounting for those is a job for the modeling stage.

### Models in the slower classes

| Model | Speed | Drives | Failures | Drive-years | Capacity | Years | AFR |
|---|---|---|---|---|---|---|---|
| HMS5C4040BLE640 | 5700 | 16,342 | 448 | 112,736 | 4 TB | 2014–2026 | 0.40% |
| HMS5C4040ALE640 | 5700 | 8,722 | 260 | 46,015 | 4 TB | 2013–2026 | 0.57% |
| HDS5C3030ALA630 | 5700 | 4,664 | 150 | 18,196 | 3 TB | 2013–2018 | 0.82% |
| HDS5C4040ALE630 | 5700 | 2,837 | 95 | 12,473 | 4 TB | 2013–2024 | 0.76% |
| ST4000DM000 | 5900 | 37,040 | 5,789 | 220,284 | 4 TB | 2013–2025 | 2.63% |
| ST31500541AS | 5900 | 2,188 | 397 | 3,959 | 1.5 TB | 2013–2018 | 10.03% |

### Eligible drives under the era cutoff (first seen by 2016)

Only drives first seen in 2016 or earlier can be sampled. Counts are usable drives (excluded
models removed, power-on hours present):

| Model | Speed | Manufacturer | Eligible drives | Of all drives | Failures | Drive-years | AFR |
|---|---|---|---|---|---|---|---|
| HMS5C4040BLE640 | 5700 | HGST | 10,160 | 16,342 | 250 | 69,332 | 0.36% |
| HMS5C4040ALE640 | 5700 | HGST | 7,168 | 8,722 | 185 | 35,383 | 0.52% |
| HDS5C3030ALA630 | 5700 | HGST | 4,664 | 4,664 | 150 | 18,196 | 0.82% |
| HDS5C4040ALE630 | 5700 | HGST | 2,799 | 2,837 | 93 | 12,343 | 0.75% |
| ST4000DM000 | 5900 | Seagate | 36,553 | 37,038 | 5,728 | 218,970 | 2.62% |
| ST31500541AS | 5900 | Seagate | 2,188 | 2,188 | 397 | 3,959 | 10.03% |
| ST8000DM002 | 7200 | Seagate | 8,712 | 10,316 | 1,215 | 80,241 | 1.51% |
| HDS722020ALA330 | 7200 | HGST | 4,774 | 4,774 | 235 | 14,538 | 1.62% |
| ST6000DX000 | 7200 | Seagate | 1,932 | 1,939 | 99 | 11,710 | 0.85% |
| HDS723030ALA640 | 7200 | HGST | 1,048 | 1,048 | 73 | 3,917 | 1.86% |
| ST8000NM0055 | 7200 | Seagate | 61 | 15,674 | 9 | 562 | 1.60% |
| HUH728080ALE600 | 7200 | HGST | 47 | 1,218 | 3 | 183 | 1.64% |

| Speed | Eligible drives | AFR (eligible drives) |
|---|---|---|
| 5700 | 24,791 | 0.50% |
| 5900 | 38,741 | 2.75% |
| 7200 | 16,574 | 1.47% |

The other 25 7200 RPM models have no drives from 2016 or earlier, so they're only in the
all-era sample. ST8000NM0055 and HUH728080ALE600 almost drop out too: nearly all their drives
arrived after 2016. In practice the era-matched 7200 class is four models.

## How speeds were verified

- **HGST/Hitachi CoolSpin drives (HMS5C…, HDS5C…) are 5700 RPM, not 5400.** HGST didn't
  publish a number for CoolSpin, and many retailers and reviews list these drives as 5400 RPM.
  The rotation rate the drives report about themselves (recorded at
  [smarthdd.com](https://smarthdd.com/database/HGST-HMS5C4040BLE640/MPAOA5D0)) is 5700 RPM for
  all four models. This document uses the drive-reported value.
- **Seagate ST4000DM000 and ST31500541AS are 5900 RPM** (Seagate product manual and reviews).
- **ST6000DX000** is sometimes listed as 5900 RPM, but the drive reports 7200 RPM.
- **7200 RPM product lines:** Seagate Exos/enterprise (ST…NM…), Toshiba MG series,
  WD/HGST Ultrastar (WUH72…, HUH72…) and Deskstar 7K (HDS72…).

## Exclusions

> **ST3000DM001 is excluded from the analysis.** This 3 TB, 7200 RPM Seagate model has an
> annualized failure rate of **28.27%** (1,708 failures over 6,042 drive-years among 4,707
> drives, 2013–2015), roughly 20× the rest of the 7200 class. It reflects a problem with that
> specific model, not spin speed. Including it would make 7200 RPM look worse no matter what
> speed actually does. `sample_by_rpm.py` excludes it by default (`--exclude-models`). As a
> sensitivity check, you can re-run with it included and report how much the results change.

> **5400 RPM is not analyzed.** After verification, WDC WD30EFRX (1,335 drives, 174 failures,
> 3,484 drive-years, 4.99% AFR) is the only 5400 RPM model with 1,000+ drives. A class made of
> one model can't separate the effect of speed from the quality of that model, so it is
> excluded by default as well.

Also excluded:
- **SSDs** (e.g. Seagate BarraCuda 120 SSD): they have no spinning platters. `rpm` is blank.
- **Drives with no usable power-on hours** (469 drives, under 0.1%), and any reporting more than
  15 years of power-on time.

## Sampling design

Two samples are drawn with the same settings, except for era matching:

| File | Era matching | Use |
|---|---|---|
| `sample.parquet` | **On**: only drives first seen by 2016 | Main sample: all three classes from the same drive generation |
| `sample_all_eras.parquet` | Off: drives from every year | Comparison: shows how much the era restriction changes things |

- **3 classes × 5,000 drives = 15,000 drives** per sample, the top of the 1,000–5,000-per-class
  range. Set by `DRIVES_PER_CLASS` at the top of `sample_by_rpm.py`. Every class has more
  eligible drives than that. Era-matched: 5700 has 24,791, 5900 has 38,741 and 7200 has 16,574,
  so 7200 is the tightest at 30% sampled. All-era: 32,565, 39,226 and 437,397.
- **Era matching is a hard limit on the sample space.** No drive first seen in the data after
  `LATEST_MODEL_YEAR` (2016, set at the top of `sample_by_rpm.py`) can be sampled, whatever its
  model. Later-added drives of older models are removed as well (e.g. about 6,200 HMS5C4040BLE640
  drives added in 2017–18). Each model's share of its class is based on its eligible drives only.
  Without the limit, half the 7200 drives would be from 2022 or later and four times larger
  (median 16 TB vs. 4 TB).
- **The limit applies to when drives *enter* the data, not to how long they're followed.** A drive
  first seen in 2015 keeps its full record through to failure or the end of the data in 2026.
- **Across classes: equal allocation.** Each class gets the same number of drives, even though
  7200 RPM is about 86% of the population. This is deliberate (*disproportionate* stratified
  sampling): spreading 15,000 drives proportionally would leave 5700 RPM with only about 960
  drives and roughly 26 failures, too few to compare. Comparisons between classes need no adjustment. Any claim about
  the fleet as a whole (e.g. an overall failure rate) must weight each class by its population share.
- **Within each class: proportional allocation.** Each model's share of the sample matches its
  share of that class in the full dataset (`--max-model-share 1.0`, i.e. no cap).
- **Within each model: simple random sampling** without replacement.
- **Fixed seed (42):** the same data and settings always give the same sample.

**Note on the 5900 class:** proportional sampling makes it about 94% ST4000DM000, because that is
what the population looks like. That's a real limitation of the data: 5900 RPM results will
mostly reflect that one model, and this should be stated when reporting them.

**What the two samples look like** (seed 42):

Main sample (era-matched):

| | 5700 | 5900 | 7200 |
|---|---|---|---|
| Models | 4 | 2 | 6 (4 with more than 20 drives) |
| Failures | 124 | 788 | 498 |
| AFR in sample | 0.46% | 2.74% | 1.48% |
| First seen ≤2015 / 2016 | 72 / 28% | 83 / 17% | 47 / 53% |
| Latest drive first seen | 2016 | 2016 | 2016 |
| Median capacity | 4 TB | 4 TB | 8 TB |

All-era sample: 5700 and 5900 include drives added up to 2018 (137 and 777 failures). The 7200
class has 31 models, 290 failures and a 1.53% AFR, with 84% of its drives first seen in 2019 or
later and a median capacity of 16 TB.

**Expected power:** in the main sample, a hazard ratio of about **1.3×** against 5700 RPM is
detectable with 80% power (1.31× for 5900, 1.32× for 7200). The all-era sample is about 1.34× for 7200.
For comparison, 1,650 drives per class could only detect about 1.6×. `sample_by_rpm.py` prints
these figures, plus the era check, for whatever sample you draw.

## Confounding: read before interpreting

**Speed is tied to manufacturer, and partly to era:**

| | 5700 | 5900 | 7200 (main, era-matched) | 7200 (all-era) |
|---|---|---|---|---|
| Manufacturers | HGST only | Seagate only | HGST, Seagate | HGST, Seagate, Toshiba, WD |
| Capacity | 3–4 TB | 1.5–4 TB | 2–8 TB | mostly 8–26 TB |
| Drives first seen (main sample) | 2013–2016 | 2013–2016 | 2013–2016 | 2013–2026 |

Era matching keeps every class within the same entry window (2013–2016), but the classes still
differ inside it. The 7200 drives skew toward 2016 and are larger (median 8 TB vs. 4 TB).

Consequences:
- **5900 vs. 5700 is effectively Seagate vs. HGST.** No model lets us see the same
  manufacturer at both speeds, so a raw difference may be a brand difference.
- **Adjusting for manufacturer can mislead.** With only a handful of models, the adjustment relies on
  a few cross-class models and can even reverse the sign. In a synthetic test, where the true
  effect of the faster class was 1.5×, the unadjusted estimate was 1.30× and the
  manufacturer-adjusted estimate was 0.82×. Report unadjusted and adjusted results side by side,
  and don't trust either alone.
- **Confidence intervals are too narrow.** Speed is a property of the model, so the real number of
  independent units is the number of models (effectively 10 in the main sample: 4 + 2 + 4), not
  the number of drives.

**Recommended comparisons within one manufacturer** (cleanest evidence available). Both are fully
contained in the main sample:
- **HGST, 5700 vs. 7200:** HMS5C4040BLE640, HMS5C4040ALE640, HDS5C3030ALA630, HDS5C4040ALE630
  vs. HDS722020ALA330, HDS723030ALA640 (plus 14 HUH728080ALE600 drives).
- **Seagate, 5900 vs. 7200:** ST4000DM000, ST31500541AS vs. ST8000DM002, ST6000DX000 (plus 19
  ST8000NM0055 drives).

If speed matters, the effect should show up *within* each manufacturer, not just between classes.

## Running it

```powershell
# main sample (era-matched) -> sample.parquet
python sample_by_rpm.py

# all-era comparison sample -> sample_all_eras.parquet
python sample_by_rpm.py --all-eras --out sample_all_eras.parquet

# alternative: cap any one model at 50% of its class (changes the model mix)
python sample_by_rpm.py --max-model-share 0.5 --out sample_capped.parquet

# alternative: ST3000DM001 included
python sample_by_rpm.py --exclude-models "WDC WD30EFRX" --out sample_with_outlier.parquet
```

## What we can and can't claim

- This is **observational** data, so results show **association**, not causation.
- A supported hypothesis would look like this: hazard ratios above 1 that increase from 5900 to 7200, a
  per-1000-RPM trend above 1, larger Weibull `rho` at higher speed, and the same direction
  within HGST and within Seagate.
- A null result is still a result if the confidence intervals are narrow enough to rule out
  large effects (e.g. "7200 RPM drives are no more than 1.3× as likely to fail").
- Results apply to drives running in Backblaze's datacenters. Home or laptop use may differ.
