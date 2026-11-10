# CLAUDE.md

Notes for Claude assisting us with working in this repo.

## Git
- Don't commit, push, branch, merge, rebase, stash, or run any other git command that changes the repo without asking first. Every time.
- Read-only commands (`git status`, `git diff`, `git log`) are fine.

## Commit messages
Use a prefix, then a short lowercase summary. Match the existing history, e.g. `docs: add data sources overview`.

Never add a `Co-Authored-By: Claude` line, a "Generated with Claude Code" line, or any other AI attribution to commit messages or pull requests.

| Prefix | Use for |
|---|---|
| `feat:` | new scripts or features |
| `fix:` | bug fixes |
| `docs:` | README, SOURCES, plans, other writing |
| `data:` | new or regenerated sample files |
| `refactor:` | code changes that don't change behavior |
| `test:` | tests and checks |
| `chore:` | setup, dependencies, `.gitignore`, housekeeping |

## Writing docs
Keep it simple. Write it the way someone on the team would explain it to a classmate:
- Say each thing once, in plain words.
- Short sentences. Lists over paragraphs when it fits.
- No filler, hype, or long intros.
- Don't explain what the code already makes obvious.

## Project decisions so far
- **Data:** Backblaze Drive Stats (see [SOURCES.md](./SOURCES.md)), queried with Python + DuckDB against Backblaze's hosted Iceberg copy. No full download.
- **Drive life** is measured in power-on hours (`smart_9_raw`), not days in the data.
- **Samples** (fixed seed so they're reproducible):
  - 1000 random failed drives (main sample)
  - 1000 random data HDDs, 1000 random boot HDDs (from Q4 2018 on) and 1000 random SSDs, failed or not (Backblaze doesn't have 1000 failed SSDs)
  - per-model totals (drives, failures, drive-days) so we can work out failure rates
- **HDD vs SSD** is told apart by model name, with a SMART check (`smart_3`/`smart_10` are HDD-only). There's no drive type column.
- **SSDs in this data are boot drives.** HDDs under 1 TB and 2.5" laptop models are also boot drives. The main HDD vs SSD comparison is SSD vs boot HDD (same job). SSD vs data HDD is secondary.
- **Failed drives** mostly drop out after their failure day (96.5%). Samples cut each drive off at its first failure.
- **Spin speed (RPM)** isn't in the data. It needs a hand-made model → RPM lookup.
- **Analysis order:** HDD model vs model → RPM vs failure rate → HDD vs SSD. See [ANALYSIS_PLAN.md](./ANALYSIS_PLAN.md).
- Scope right now is gathering data and planning. No modeling yet.

## Layout
- `build.ps1` / `build.sh` - run every step below in order (sets up the venv and `.env` first if needed)
- `scripts/` - Python scripts. Run in this order:
  1. `drive_types.py` - labels every model HDD/SSD and boot/data, writes `data/drive_models.csv`
  2. `check_failed_rows.py` - checks whether failed drives drop out of later reports
  3. `build_samples.py` - writes the sample files to `data/samples/`
- `scripts/connect.py` - shared DuckDB connection to the Iceberg data
- `data/samples/` - sample CSVs (small, committed)
- Access keys go in `.env` (copy `.env.example`). Never commit `.env`.
