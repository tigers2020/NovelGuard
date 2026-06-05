@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title NovelGuard - install gui

set "PY=%CD%\.venv\Scripts\python.exe"
set "BOOT=py -V:Astral/CPython3.12.13"

echo Ensuring Python 3.12 .venv and gui extras...
%BOOT% scripts\ensure_dev_venv.py --recreate-if-wrong --install-gui 2>nul ^|^| python scripts\ensure_dev_venv.py --recreate-if-wrong --install-gui
if errorlevel 1 exit /b 1

if not exist "%PY%" (
  echo [error] .venv missing after bootstrap: %PY%
  exit /b 1
)

echo.
echo [ok] %PY%
echo [ok] pywebview in .venv — run run.bat or:
echo       "%PY%" -m app.webview_main

endlocal
exit /b 0
