@echo off
REM Full boot: titled Pocket TTS :8000 + titled NOVA daemon + GUI
REM (nova.launch uses spawn_titled so consoles stay visible with names)
cd /d "%~dp0"
set PYTHONPATH=%~dp0
set NOVA_FAST=1
"C:\Python314\python.exe" -m nova.launch
pause
