# Run one automation job (Task Scheduler friendly)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path "automation\config.yaml")) {
    Copy-Item "automation\config.example.yaml" "automation\config.yaml"
    Write-Host "Created automation\config.yaml from example. Set cursor.dry_run or install CLI."
}

python -m automation.runners.job_worker --once
exit $LASTEXITCODE
