#!/bin/bash
# Launcher Clipper PC (macOS/Linux) — jalankan: bash run_gui.sh
cd "$(dirname "$0")"
if [ -x ".venv/bin/python" ]; then
  .venv/bin/python clipper_gui.py
else
  python3 clipper_gui.py
fi
