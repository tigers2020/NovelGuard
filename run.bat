@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title NovelGuard

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo [warn] .venv not found - using current Python on PATH
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [error] npm not found. Install Node.js and retry.
  exit /b 1
)

if not exist "web\node_modules\" (
  echo [1/3] npm install in web...
  pushd web
  call npm install
  if errorlevel 1 (
    popd
    exit /b 1
  )
  popd
)

if not exist "web\dist\index.html" (
  echo [2/3] Building web UI...
  pushd web
  call npm run build
  if errorlevel 1 (
    popd
    exit /b 1
  )
  popd
) else (
  echo [2/3] web\dist present - skip build
)

pip show pywebview >nul 2>&1
if errorlevel 1 (
  echo [3/3] pip install -e ".[gui]" ...
  pip install -e ".[gui]"
  if errorlevel 1 (
    exit /b 1
  )
) else (
  echo [3/3] pywebview installed - skip pip
)

echo.
echo Starting NovelGuard desktop...
novelguard-webview 2>nul
if errorlevel 1 (
  set "PYTHONPATH=src"
  python src\app\webview_main.py
)

endlocal
exit /b %ERRORLEVEL%
