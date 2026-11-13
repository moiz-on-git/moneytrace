@echo off
REM Double-click launcher: runs the daily brief and opens the report.
cd /d "%~dp0"
python -m moneytrace run --open
if errorlevel 1 (
  echo.
  echo Run failed. Check that Python is on PATH and .env has OPENROUTER_API_KEY.
)
pause
