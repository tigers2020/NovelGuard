@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title NovelGuard - Kanban Dry Run Once

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo [warn] .venv not found - using current Python on PATH
)

python scripts\kanban\kanban_inbox_to_scheduled.py --once --dry-run
set "INBOX_EXIT=%ERRORLEVEL%"

python scripts\kanban\kanban_scheduled_to_inprogress.py --once --dry-run
set "SCHEDULED_EXIT=%ERRORLEVEL%"

python scripts\kanban\kanban_verify_gate.py --once --dry-run
set "VERIFY_EXIT=%ERRORLEVEL%"

if not "%INBOX_EXIT%"=="0" exit /b %INBOX_EXIT%
if not "%SCHEDULED_EXIT%"=="0" exit /b %SCHEDULED_EXIT%
if not "%VERIFY_EXIT%"=="0" exit /b %VERIFY_EXIT%

endlocal & exit /b 0
