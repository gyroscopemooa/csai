@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run start_windows.bat first to install dependencies.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 echo Tests failed. Review error output.
pause
