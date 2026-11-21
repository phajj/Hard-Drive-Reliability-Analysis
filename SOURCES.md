# Data Sources

## Primary Source: Backblaze Drive Stats

This is currently the project's only data source.

| Field | Details |
|---|---|
| Link | [Backblaze Hard Drive Test Data](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data) |
| Coverage | April 2013 – Q2 2026 (yearly archives for 2013–2015, quarterly from 2016 on; 45 archives as of Nov 2026) |
| Size | ~35 GB zipped, ~260 GB unzipped (each recent quarter is ~1–2 GB zipped, ~11–12 GB unzipped) |
| Download | `https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/<file>` (e.g. `data_Q2_2026.zip`, `data_2015.zip`) |
| Format | One CSV per day (`YYYY-MM-DD.csv`), one row per drive that was working that day |
| Key columns | `date`, `serial_number`, `model`, `capacity_bytes`, `failure` (0/1), location (`datacenter`, `cluster_id`, `vault_id`, `pod_id`, `pod_slot_num`), `is_legacy_format`, normalized and raw values for dozens of SMART attributes (`smart_N_normalized`, `smart_N_raw`) |
| Schema | [Drive_Stats_Schema_Current.csv](https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/Drive_Stats_Schema_Current.csv), with changes since 2018 in [Drive_Stats_Schema_2018_Onward.csv](https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/Drive_Stats_Schema_2018_Onward.csv). The columns can change between quarters. |
| Iceberg copy | Read-only Apache Iceberg copy on Backblaze's S3-compatible storage: endpoint `https://s3.us-west-004.backblazeb2.com`, bucket `drivestats-iceberg`, prefix `drivestats`. Access keys are on the Backblaze page. Can be queried with DuckDB or Spark without downloading the CSVs. |
| Scale | ~354k drives in service (Q2 2026). Lifetime: 558M drive-days, 21,609 failures. |
| License | Free to use as long as Backblaze is cited. Work built on the data may be sold; the data itself may not. |

### Drive type and manufacturer

- We only analyze HDDs. The files also have a few SSDs (from Q4 2018 on, 26 models, about 4,000 drives vs ~540k HDDs), which we filter out.
- **There is no drive-type or manufacturer column.** Both come from the **`model`** column. Our labels are in `data/drive_models.csv` (made by `scripts/drive_types.py`).
- SSDs are spotted by name (e.g. Seagate `ZA…`, Micron `MTFD…`, Crucial `CT…`, WDC `WDS…`). As a check, HDDs report spin-up time (`smart_3`) and spin retries (`smart_10`) and SSDs don't. A few 2013–2015 HDD models get flagged, but only because the early files have fewer SMART columns.
- Manufacturer: `ST…` is Seagate, `TOSHIBA …` is Toshiba, and `WDC …`, `HGST …` and `Hitachi …` are Western Digital (WD bought Hitachi's drive business, HGST, in 2012). Other makers are left out.

### Modeling notes

- A drive's lifetime runs from its first to its last day in the data, and `failure = 1` on its last day means it failed. Drives that disappear without a failure, or are still running at the end, count as censored.
- Drives already running when the data starts in April 2013 are left-truncated: their early life wasn't observed. Survival fitting needs to account for this.
- SMART attribute 9 (`smart_9_raw`, power-on hours) gives a drive's real age, including drives installed before the data starts. **We use power-on hours as our measure of drive life**, not days in the data. Some models report it in odd units or with junk values, so the samples flag drives where it doesn't match the calendar (`poh_suspect`).
- **Do failed drives drop out?** Mostly yes. We checked every drive with a `failure = 1` row (`scripts/check_failed_rows.py`). Out of 34,728 failed drives, 33,508 (96.5%) never show up again after their failure day. 1,220 do, usually the next day (median 1 day later), and some keep going for years, probably because the drive was put back in service. 67 drives have more than one failure row. Our samples cut each drive off at its first failure.
- Model names sometimes have extra spaces (`WDC  WUH721414ALE6L4` vs `WDC WUH721414ALE6L4`), so `scripts/connect.py` cleans them up.

## Logos

The manufacturer logos on the site (`site/assets/logos/`) come from Wikimedia Commons, the media library Wikipedia uses.

| Logo | File page | File |
|---|---|---|
| Seagate | [File:Seagate-Logo.svg](https://commons.wikimedia.org/wiki/File:Seagate-Logo.svg) | `seagate.svg` |
| WD (since Feb 2026) | [File:WD_Logo.svg](https://commons.wikimedia.org/wiki/File:WD_Logo.svg) | `wd.svg` |
| Toshiba | [File:Toshiba_Logo.svg](https://commons.wikimedia.org/wiki/File:Toshiba_Logo.svg) | `toshiba.svg` |