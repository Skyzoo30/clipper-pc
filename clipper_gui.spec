# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ClipperPC (Windows onedir build).

Build on Windows with:  pyinstaller clipper_gui.spec
Result: dist/ClipperPC/ClipperPC.exe  (+ support files in the same folder)

Notes:
- onedir (bukan onefile): jauh lebih andal untuk dependensi native besar
  (ctranslate2, av, tokenizers) dan start-up lebih cepat.
- console=False: tidak ada jendela terminal; log tampil di GUI.
- Model Whisper TIDAK dibungkus: di-download sekali saat render pertama
  (seperti versi script), jadi folder dist tidak membengkak oleh model.
- ffmpeg dibungkus dari imageio-ffmpeg (lihat clipper.ffmpeg_exe()).
"""

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
for _pkg in ("faster_whisper", "ctranslate2", "tokenizers", "av", "numpy"):
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        binaries += _b
        hiddenimports += _h
    except Exception:
        pass
try:
    import imageio_ffmpeg

    binaries.append((imageio_ffmpeg.get_ffmpeg_exe(), "."))
except Exception:
    pass

a = Analysis(
    ["clipper_gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ClipperPC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="ClipperPC",
)
