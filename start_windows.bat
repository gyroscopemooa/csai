@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.11 or newer first: https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 goto fail
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 goto fail
if not exist .env copy .env.example .env >nul
start "" http://127.0.0.1:8000
python run.py
pause
exit /b 0
:fail
echo Installation failed. See the errors above.
pause
exit /b 1
