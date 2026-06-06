@echo off
setlocal
set "ROOT=%~dp0..\.."
python "%ROOT%\scripts\git_guard.py" %*
