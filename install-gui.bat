@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title NovelGuard - install gui

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo [warn] .venv not found - using current Python
)

echo Installing: pip install -e ".[gui]"
echo Do NOT add a dot after the closing quote.
echo.

pip uninstall novelguard -y >nul 2>&1
pip install -e ".[gui]"
if errorlevel 1 (
  echo.
  echo [failed] Wrong command often looks like: pip install -e ".[gui]".
  echo Correct command: pip install -e ".[gui]"
  exit /b 1
)

echo.
echo [ok] Done. Run novelguard-webview or run.bat
endlocal
exit /b 0
