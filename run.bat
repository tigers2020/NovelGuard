@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title NovelGuard

set "PY=%CD%\.venv\Scripts\python.exe"
set "BOOT=py -V:Astral/CPython3.12.13"

if not exist "%PY%" (
  echo [1/4] Creating Python 3.12 .venv...
  %BOOT% scripts\ensure_dev_venv.py --recreate-if-wrong 2>nul ^|^| python scripts\ensure_dev_venv.py --recreate-if-wrong
  if errorlevel 1 exit /b 1
) else (
  "%PY%" -c "import sys; raise SystemExit(0 if (3,12) <= sys.version_info[:2] < (3,13) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo [1/4] .venv is not Python 3.12 — recreating...
    %BOOT% scripts\ensure_dev_venv.py --recreate-if-wrong 2>nul ^|^| python scripts\ensure_dev_venv.py --recreate-if-wrong
    if errorlevel 1 exit /b 1
  )
)

if not exist "%PY%" (
  echo [error] .venv missing: %PY%
  echo Run: py -V:Astral/CPython3.12.13 scripts\ensure_dev_venv.py --recreate-if-wrong
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [error] npm not found. Install Node.js and retry.
  exit /b 1
)

if not exist "web\node_modules\" (
  echo [2/4] npm install in web...
  pushd web
  call npm install
  if errorlevel 1 (
    popd
    exit /b 1
  )
  popd
) else (
  echo [2/4] web\node_modules present — skip npm install
)

echo [3/4] Building web UI...
pushd web
call npm run build
if errorlevel 1 (
  popd
  exit /b 1
)
popd

if not exist "web\build\index.html" (
  echo [error] Frontend build missing: web\build\index.html
  exit /b 1
)

echo [4/4] Installing Python package into .venv (editable, gui)...
"%PY%" -m pip install --no-user -e ".[gui]"
if errorlevel 1 (
  echo [error] pip install failed. Try: install-gui.bat
  exit /b 1
)

echo.
echo Starting NovelGuard desktop (%PY%)...
"%PY%" -m app.webview_main
set "EXIT_CODE=%ERRORLEVEL%"

endlocal & exit /b %EXIT_CODE%
