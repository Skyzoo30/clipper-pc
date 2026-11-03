@echo off
REM Launcher Clipper PC (Windows) — klik 2x file ini.
cd /d %~dp0
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe clipper_gui.py
) else (
  python clipper_gui.py
)
pause
