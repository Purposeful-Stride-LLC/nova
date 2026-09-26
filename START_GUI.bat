@echo off
REM NOVA cosmic console ? palace QTableWidget lives here (not app_enhanced)
cd /d "%~dp0"
set PYTHONPATH=%~dp0
set NOVA_FAST=1
"C:\Python314\python.exe" -m nova.gui
if errorlevel 1 (
  echo GUI exited. Try: pip install PySide6
  pause
)
