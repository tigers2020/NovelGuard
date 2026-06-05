# Deprecated: use automation\run-automation.ps1 (webhook + worker together)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
Write-Host "run-worker-loop.ps1 -> run-automation.ps1" -ForegroundColor Yellow
& "$PSScriptRoot\run-automation.ps1" @args
