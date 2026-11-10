# Sets up the venv (first time only) and runs every build step in order.
# Usage, from the repo root:  .\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    Write-Host "Creating .venv..."
    python -m venv .venv
}
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $py -m pip install -q -r requirements.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example"
}

Set-Location scripts
foreach ($step in "connect.py", "drive_types.py", "check_failed_rows.py", "build_samples.py") {
    Write-Host "`n=== $step ==="
    & $py $step
    if ($LASTEXITCODE -ne 0) { throw "$step failed" }
}
Write-Host "`nDone. Samples are in data/samples/"
