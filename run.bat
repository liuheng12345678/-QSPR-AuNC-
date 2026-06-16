@echo off
cd /d "%~dp0"
python run_all.py
if errorlevel 1 (
  py run_all.py
)
pause
