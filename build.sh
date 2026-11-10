#!/usr/bin/env bash
# Sets up the venv (first time only) and runs every build step in order.
# Works on macOS, Linux and Git Bash on Windows.
# Usage, from the repo root:  ./build.sh
set -euo pipefail
cd "$(dirname "$0")"

PYTHON=$(command -v python3 || command -v python)
if [ ! -d .venv ]; then
    echo "Creating .venv..."
    "$PYTHON" -m venv .venv
fi

# The venv puts python in bin/ on macOS/Linux and Scripts/ on Windows
if [ -x .venv/bin/python ]; then
    PY="$PWD/.venv/bin/python"
else
    PY="$PWD/.venv/Scripts/python.exe"
fi
"$PY" -m pip install -q -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

cd scripts
for step in connect.py drive_types.py check_failed_rows.py build_samples.py; do
    echo
    echo "=== $step ==="
    "$PY" "$step"
done
echo
echo "Done. Samples are in data/samples/"
