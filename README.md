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
| `drive_types.py` | Labels models HDD/SSD and boot/data -> `data/drive_models.csv` |
| `check_failed_rows.py` | Checks if failed drives drop out of later reports |
| `build_samples.py` | Builds the samples -> `data/samples/` |

It stops at the first step that fails. To run one step on its own, activate the venv and run it from inside `scripts/`, e.g. `python build_samples.py`.

If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope Process RemoteSigned` first.

Checking the output:
- Each file in `data/samples/` should have 1000 drives.
- Every drive in `failed_1000.csv` should have `failed = 1`.
- Running `build_samples.py` again should give the same files (the seed is fixed).

## Resources:
- [SOURCES](./SOURCES.md): where the data comes from
- [ANALYSIS_PLAN](./ANALYSIS_PLAN.md): what's in the samples and what we're looking at first
