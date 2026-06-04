@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title NovelGuard - Kanban Scheduled to In Progress

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo [warn] .venv not found - using current Python on PATH
)

python scripts\kanban\kanban_scheduled_to_inprogress.py %*
set "EXIT_CODE=%ERRORLEVEL%"

endlocal & exit /b %EXIT_CODE%
