# Poll job queue forever (Task Scheduler / background service)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path "automation\config.yaml")) {
    Copy-Item "automation\config.example.yaml" "automation\config.yaml"
}

while ($true) {
    python scripts/automation_worker.py --once
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) {
        exit $LASTEXITCODE
    }
    Start-Sleep -Seconds 15
}
