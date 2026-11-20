# Hard-Drive-Reliability-Analysis
Data Modeling and Simulation project, analyzing the lifespans and reliability of hard drives.

## Team
- Peter Hajj
- Jackson Higgins

## Overview
This project will model hard drive reliability from real world failure rate data and potentially use the model to simulate the long-term risk of data loss using different storage arrays. Using datasets that record daily health checkin or drives and failures we will build drive lifetime records and fit survival models. A simulation will then use these failure models to estimate how likely different storage setups, such as mirrors and RAIDZ arrays, are to lose data over 5–10 years.

## Tech stack
| Tool | What we use it for |
|---|---|
| Python 3.12 | All the scripts |
| DuckDB (+ `iceberg` and `httpfs` extensions) | Querying the full dataset remotely with SQL, no download needed |
| pandas | Working with query results and writing the CSVs |
| python-dotenv | Loading the Backblaze access keys from `.env` |
| Backblaze Drive Stats | The data: daily reports on every drive in Backblaze's data centers |
| Apache Iceberg on Backblaze B2 | Backblaze's hosted copy of the data that DuckDB reads from |
| Git + GitHub | Version control |
| Claude Code | AI coding assistant, used to help write the scripts and docs |

## Running it
Needs Python 3.12+. From the repo root, run the build script for your system:

```powershell
 # Windows-based systems (PowerShell)
.\build.ps1
```
```bash
# Unix-based systems, ie Linux/MacOs (Bash)
./build.sh
```
It sets up `.venv` and `.env` the first time, then runs these in order (about 10 minutes total, since each one queries the full Backblaze dataset remotely):

| Step | What it does |
|---|---|
| `connect.py` | Quick connection test, prints the table's columns |
| `drive_types.py` | Labels models HDD/SSD, boot/data and manufacturer -> `data/drive_models.csv` |
| `check_failed_rows.py` | Checks if failed drives drop out of later reports |
| `build_samples.py` | Builds the samples -> `data/samples/` |
| `split_by_maker.py` | Splits the samples by manufacturer -> `data/samples/by_maker/` |

It stops at the first step that fails. To run one step on its own, activate the venv and run it from inside `scripts/`, e.g. `python build_samples.py`.

If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope Process RemoteSigned` first.

Checking the output:
- Each `_1000` file in `data/samples/` should have 1000 drives.
- Every drive in `failed_1000.csv` should have `failed = 1`.
- Running `build_samples.py` again should give the same files (the seed is fixed).

## Website
The results website is a small Node app (Express) that serves the `site/` folder.

- `site/index.html`: homepage, one card per topic
- `site/assets/nav.js`: the list of topics. It builds the nav bar on every page and the homepage cards.
- `site/<topic>/`: one folder per topic, e.g. `site/rpm/` (made by `rpm_analysis/make_website.py`)
- `site/manufacturers/`: one scatter per maker. Run `python plot_makers.py seagate` (or `wd`, `toshiba`) from `scripts/` to rebuild its data file and the PNG in `plots/manufacturers/`.

Adding a topic: make `site/<topic>/index.html`, add it to `TOPICS` in `nav.js`, and put this in the page's `<head>` and top of `<body>`:
```html
<link rel="stylesheet" href="/assets/nav.css">
<script src="/assets/nav.js" defer></script>
<nav id="site-nav" class="site-nav"></nav>
```

Running it locally (needs Node 20+):
```bash
npm install
npm start        # http://localhost:3000
```

`/healthz` returns `ok` for uptime checks.

## Resources:
- [SOURCES](./SOURCES.md): where the data comes from
- [ANALYSIS_PLAN](./ANALYSIS_PLAN.md): what's in the samples and what we're looking at first
- [rpm_analysis](./rpm_analysis/README.md): spin speed (RPM) vs failure rate: download pipeline, RPM-stratified samples and a results website
