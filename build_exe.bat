@echo off
REM Build ClipperPC.exe di PC Windows (jalankan file ini sekali).
REM Hasil: dist\ClipperPC\ClipperPC.exe  (+ file pendukung di folder yang sama)
REM Catatan: folder dist cukup besar (ratusan MB) karena membungkus Python +
REM runtime transkripsi. Model Whisper tetap download sekali saat render pertama.
cd /d %~dp0
if exist .venv\Scripts\python.exe (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)
%PY% -m pip install -r requirements.txt pyinstaller
%PY% -m PyInstaller clipper_gui.spec
echo.
echo SELESAI. EXE ada di dist\ClipperPC\ClipperPC.exe
pause
