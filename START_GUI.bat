@echo off
REM NOVA 2.1 operator console (read-only; actions go to the daemon via the command inbox).
cd /d "%~dp0"
set PYTHONPATH=%~dp0
set NOVA_HOME=%~dp0
if exist "%~dp0STAGED" (
  set NOVA_HOME=%~dp0_scratch_home
) else if exist "%~dp0NOVA_HOME.txt" (
  set /p _NH=<"%~dp0NOVA_HOME.txt"
)
if defined _NH for %%I in ("%~dp0%_NH%") do set NOVA_HOME=%%~fI\
set NOVA_FAST=1
python -m nova.gui
if errorlevel 1 (
  echo GUI exited. Try: pip install PySide6
  pause
)
