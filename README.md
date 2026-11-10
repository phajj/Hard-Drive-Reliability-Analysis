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
Needs Python 3.12+. First time only, from the repo root (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Don't rerun `python -m venv .venv` while the venv is active, you'll get a "Permission denied" on `python.exe`. It's harmless but means the venv already exists.

Then activate the venv and run the scripts from inside `scripts/`, in this order. Each one queries the full Backblaze dataset remotely, so they take a few minutes.

```powershell
.venv\Scripts\Activate.ps1
cd scripts
python connect.py            # quick test, prints the table's columns
python drive_types.py        # labels models HDD/SSD and boot/data -> data/drive_models.csv
python check_failed_rows.py  # checks if failed drives drop out of later reports
python build_samples.py      # builds the samples -> data/samples/
```

If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope Process RemoteSigned` first.

Checking the output:
- Each file in `data/samples/` should have 1000 drives.
- Every drive in `failed_1000.csv` should have `failed = 1`.
- Running `build_samples.py` again should give the same files (the seed is fixed).

## Resources:
- [SOURCES](./SOURCES.md): where the data comes from
- [ANALYSIS_PLAN](./ANALYSIS_PLAN.md): what's in the samples and what we're looking at first
