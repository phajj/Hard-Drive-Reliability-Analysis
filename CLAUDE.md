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
  - 1000 random data HDDs, failed or not
  - per-model totals (drives, failures, drive-days) so we can work out failure rates
- **HDDs only.** SSDs are in the data but we don't analyze them. They're told apart by model name, with a SMART check (`smart_3`/`smart_10` are HDD-only), so they can be filtered out. There's no drive type column.
- **Manufacturer** also comes from the model name (no column for it either). Only the big three are analyzed: Seagate, Western Digital and Toshiba. HGST and Hitachi count as Western Digital (WD owns them). Everything else is `Other` and gets dropped. Note: `rpm_analysis/` has its own older labels that keep HGST separate.
- **Boot vs data:** HDDs under 1 TB and 2.5" laptop models are boot drives for Backblaze's servers. Everything else is a data drive.
- **Failed drives** mostly drop out after their failure day (96.5%). Samples cut each drive off at its first failure.
- **Spin speed (RPM)** isn't in the data. It needs a hand-made model → RPM lookup.
- **Analysis order:** HDD model vs model (run per manufacturer) → RPM vs failure rate → Seagate vs WD vs Toshiba. See [ANALYSIS_PLAN.md](./ANALYSIS_PLAN.md).
- Scope right now is gathering data and planning. No modeling yet.

## Layout
- `build.ps1` / `build.sh` - run every step below in order (sets up the venv and `.env` first if needed)
- `scripts/` - Python scripts. Run in this order:
  1. `drive_types.py` - labels every model HDD/SSD, boot/data and manufacturer, writes `data/drive_models.csv`
  2. `check_failed_rows.py` - checks whether failed drives drop out of later reports
  3. `build_samples.py` - writes the sample files to `data/samples/`
  4. `split_by_maker.py` - splits the samples by manufacturer into `data/samples/by_maker/`
- `scripts/connect.py` - shared DuckDB connection to the Iceberg data
- `scripts/plot_makers.py <maker>` - per-maker scatter of power-on hours at failure: PNG in `plots/manufacturers/`, data for `site/manufacturers/`
- `data/samples/` - sample CSVs (small, committed)
- `site/` - the results website: homepage, shared nav (`site/assets/nav.js`), one folder per topic
- `server.js` - Express app that serves `site/` (`npm start`)
- Access keys go in `.env` (copy `.env.example`). Never commit `.env`.
