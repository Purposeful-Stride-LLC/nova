@echo off
REM NOVA fieldkit 2.1 full boot: Pocket TTS :8000 (if down) + NOVA daemon + GUI (nova.launch).
REM Data home: NOVA_HOME.txt beside this file (path relative to this kit), else this kit.
cd /d "%~dp0"
if exist "%~dp0STAGED" (
  echo STAGED kit: full boot disabled. Use START_GUI.bat ^(read-only, scratch home^) or the tests.
  pause
  exit /b 3
)
set PYTHONPATH=%~dp0
set NOVA_HOME=%~dp0
if exist "%~dp0NOVA_HOME.txt" (
  set /p _NH=<"%~dp0NOVA_HOME.txt"
)
if defined _NH for %%I in ("%~dp0%_NH%") do set NOVA_HOME=%%~fI\
set NOVA_FAST=1
python -m nova.launch
pause
