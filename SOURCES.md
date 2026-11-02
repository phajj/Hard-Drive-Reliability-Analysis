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

### HDD vs. SSD

- The files are mostly HDDs. Since **Q4 2018**, the boot drives of Backblaze's storage servers are in the same daily files. Many of them are SSDs and some are small HDDs. Data before Q4 2018 is HDD only.
- **There is no drive-type column.** The only way to tell SSDs from HDDs (and boot drives from data drives) is the **`model`** column.
- SSD models are mostly easy to spot by name, e.g. Seagate `ZA…` (BarraCuda/IronWolf SSD), Dell `SSDSC…`, Micron `MTFD…`, Crucial `CT…`, WDC `WDS…`. Build the full list from the models in the data, checked against Backblaze's yearly "SSD Edition" Drive Stats posts.
- Capacity alone is not a reliable test, because some boot HDDs are also small.
- SSDs are a small share of the data (low thousands of drives, compared with ~350k HDDs). Boot drives also have a different workload from data drives, so keep that in mind when comparing HDDs and SSDs.

### Modeling notes

- A drive's lifetime runs from its first to its last day in the data, and `failure = 1` on its last day means it failed. Drives that disappear without a failure, or are still running at the end, count as censored.
- Drives already running when the data starts in April 2013 are left-truncated: their early life wasn't observed. Survival fitting needs to account for this.
- SMART attribute 9 (`smart_9_raw`, power-on hours) gives a drive's real age, including drives installed before the data starts.

## Possible Additional Sources

For use if more data is needed, such as more SSDs, a second group of HDDs for validation, or data on failures that happen together.

| Source | Drive type | Coverage / size | Access / license | Possible use |
|---|---|---|---|---|
| [Alibaba SSD SMART dataset (Tianchi)](https://tianchi.aliyun.com/dataset/95044), described in [alibaba-edu/dcbrain](https://github.com/alibaba-edu/dcbrain/blob/master/ssd_smart_logs/readme.md) | SSD | ~500k SSDs across 6 models, daily SMART data and failures, 2018–2019, ~4.3 GB per year | Needs a free Tianchi account. Non-commercial license (CC BY-NC-SA 4.0). | Much larger SSD group for HDD vs. SSD comparison |
| [Alibaba Large-scale Disk Failure Prediction Dataset (Tianchi)](https://tianchi.aliyun.com/dataset/70251), mirror on [OpenI](https://openi.pcl.ac.cn/Cx/Large-scale-Disk-Failure-Prediction-Dataset) | HDD | Daily SMART logs and failure labels, Jul 2017 – Dec 2018 | Non-commercial license (CC BY-NC-SA 4.0). The Tianchi listing said it was temporarily unavailable; the OpenI mirror may work instead. | Second HDD group, to check whether the models hold up outside Backblaze |
| [NVMe SSD Open Dataset (OpenI)](https://openi.pcl.ac.cn/Cx/NVMe-SSD-Open-Dataset) | SSD (NVMe) | ~700k SSDs across 11 drive families from 3 vendors, 1 year. Files: `ssd_smart.csv`, `ssd_failure_ticket.csv` | Free on OpenI. Goes with a USENIX ATC '22 paper. | More SSD data, but only one year |
| [Alibaba correlated SSD failures (USENIX FAST '21)](https://www.usenix.org/conference/fast21/presentation/han) | SSD | ~1M SSDs across 11 models: SMART logs, trouble tickets, physical location, applications | Released by the authors for public use | Modeling failures that happen together in RAID/mirror simulations |
| [SMART-Z (Nature Scientific Data, 2025)](https://www.nature.com/articles/s41597-025-05457-z) | HDD | 147,496 HDDs in a Chinese video data center, Mar 2017 – Feb 2018 | Hosting and license not yet checked (the paper page wouldn't load) | Another non-Backblaze HDD group |
| [USENIX Computer Failure Data Repository (CFDR) / LANL](https://www.usenix.org/cfdr) | HDD (SCSI) | Disk replacement records from Los Alamos high-performance computing clusters, ~1996–2006 (e.g. 1,263 failures among 3,406 disks) | Free. Old links, check that they still work. Primary paper: Schroeder & Gibson, "Disk failures in the real world," FAST '07. | History and comparing against classic results |
| [`hdfail` in the frailtySurv R package](https://rdrr.io/cran/frailtySurv/man/hdfail.html) | HDD | Cleaned Backblaze subset: 52,422 drives (one row each), 2,885 failures, ~2 years. Columns: `serial`, `model`, `time`, `status`, `temp`, `rsc`, `rer`, `psc` | Free on CRAN | Ready-to-use data for testing survival models before the full pipeline is built |

No public drive-level data was found from Google, Microsoft, or Tencent (Google's 2007 study only published aggregate numbers).
