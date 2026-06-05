# Linear automation: webhook + worker (single process, single instance)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path "automation\config.yaml")) {
    Copy-Item "automation\config.example.yaml" "automation\config.yaml"
}

$Python = if (Test-Path ".venv\Scripts\python.exe") {
    (Resolve-Path ".venv\Scripts\python.exe").Path
} else {
    "python"
}

Write-Host "Using Python: $Python"
Write-Host "Stopping stale automation processes..."
& $Python scripts/automation_stop.py --kill-port

Write-Host "Starting NovelGuard automation daemon (webhook + worker)..."
Write-Host "Requires ngrok in another terminal: ngrok http 8765"
Write-Host "Diagnostics: $Python scripts/linear_webhook_doctor.py"
& $Python -u scripts/automation_daemon.py @args
