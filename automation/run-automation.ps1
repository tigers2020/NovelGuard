# Linear automation: webhook + worker (single process, single instance)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$RequiredPython = "3.12"

function Get-PythonMinorVersion {
    param([string]$PythonExe)
    & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
}

if (-not (Test-Path "automation\config.yaml")) {
    Copy-Item "automation\config.example.yaml" "automation\config.yaml"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating Python $RequiredPython venv..."
    & py -$RequiredPython -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create .venv with Python $RequiredPython. Install Python $RequiredPython or run: py -$RequiredPython -m venv .venv"
    }
}

$Python = (Resolve-Path ".venv\Scripts\python.exe").Path
$PythonVersion = Get-PythonMinorVersion $Python
if ($PythonVersion -ne $RequiredPython) {
    Write-Error ".venv uses Python $PythonVersion, expected $RequiredPython. Recreate it with: py -$RequiredPython -m venv .venv"
}

Write-Host "Using Python: $Python"

# pip on PATH may target a different Python than .venv — install extras into $Python
$richOk = & $Python -c "import rich" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing automation deps (rich) into venv..."
    & $Python -m ensurepip --upgrade 2>$null | Out-Null
    & $Python -m pip install -e ".[automation]"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install .[automation]. Run: $Python -m pip install -e `".[automation]`""
    }
}

Write-Host "Stopping stale automation processes..."
& $Python scripts/automation_stop.py --kill-port

Write-Host "Starting NovelGuard automation daemon (webhook + worker)..."
Write-Host "Requires ngrok in another terminal: ngrok http 8765"
Write-Host "Diagnostics: $Python scripts/linear_webhook_doctor.py"
& $Python -u scripts/automation_daemon.py @args
