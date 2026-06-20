@echo off
REM NHS School ERP — one-click launcher
REM Double-click this file, or run `start.bat` from the terminal.
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3.13 run.py
) else (
  python run.py
)
pause
