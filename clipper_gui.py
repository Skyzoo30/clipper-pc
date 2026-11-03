#!/usr/bin/env python3
"""clipper_gui.py — Clipper PC v0.2, versi SOFTWARE (jendela, bukan terminal).

Jendela ini memanggil mesin clipper.py langsung (import, bukan subprocess
Python lain) supaya bisa dibungkus PyInstaller jadi .exe: di dalam .exe
tidak ada interpreter Python terpisah. Semua proses tetap 100% lokal
(transkrip Whisper di CPU + render ffmpeg), tanpa API key, tanpa akun.

Cara jalanin:
  Windows : klik 2x run_gui.bat
  macOS/Linux : bash run_gui.sh
  Manual  : python clipper_gui.py   (dari folder ini, dengan .venv aktif)
  Build .exe (Windows) : build_exe.bat  (hasil: dist\\ClipperPC\\ClipperPC.exe)
"""

import os
import platform
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import clipper

HERE = Path(__file__).resolve().parent

BG = "#121212"
PANEL = "#1e1e1e"
FG = "#f2f2f2"
ACCENT = "#ffcc00"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Clipper PC — Local Clipper (tanpa API key)")
        self.geometry("660x600")
        self.configure(bg=BG)
        self.resizable(False, False)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG,
                        font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"),
                        foreground=ACCENT)
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("TCombobox", font=("Segoe UI", 10))
        style.configure("TEntry", font=("Segoe UI", 10))

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.model_var = tk.StringVar(value="base")
        self.lang_var = tk.StringVar(value="auto")
        self.font_var = tk.StringVar(value="Arial")
        self.fontsize_var = tk.StringVar(value="72")
        self.status_var = tk.StringVar(value="Siap. Pilih video, lalu Render.")
        self._build()

    # ---- layout ----
    def _build(self):
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="CLIPPER PC", style="Title.TLabel").pack(
            anchor="w")
        ttk.Label(main, text="Video panjang masuk, klip vertikal bercaption "
                             "keluar. Semua diproses di PC kamu.").pack(
            anchor="w", pady=(0, 12))

        self._row(main, "Video:", self.input_var, self._browse_input)
        self._row(main, "Hasil:", self.output_var, self._browse_output)

        opts = ttk.Frame(main)
        opts.pack(fill="x", pady=6)
        self._combo(opts, "Model:", self.model_var,
                    ["tiny", "base", "small"], 0)
        self._combo(opts, "Bahasa:", self.lang_var,
                    ["auto", "en", "id"], 1)
        self._combo(opts, "Font:", self.font_var,
                    ["Arial", "DejaVu Sans", "Helvetica"], 2)
        ttk.Label(opts, text="Ukuran:").grid(row=0, column=6, padx=(12, 2))
        ttk.Entry(opts, textvariable=self.fontsize_var, width=5).grid(
            row=0, column=7)

        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=10)
        self.render_btn = ttk.Button(btns, text="▶  RENDER",
                                     command=self._start_render)
        self.render_btn.pack(side="left")
        self.open_btn = ttk.Button(btns, text="Buka hasil",
                                   command=self._open_result, state="disabled")
        self.open_btn.pack(side="left", padx=8)
        ttk.Button(btns, text="Buka folder",
                   command=self._open_folder).pack(side="left")

        ttk.Label(main, textvariable=self.status_var).pack(
            anchor="w", pady=(0, 4))
        self.log = tk.Text(main, height=16, bg=PANEL, fg=FG,
                           font=("Consolas", 9), wrap="word")
        self.log.pack(fill="both", expand=True)
        self._log("Clipper PC siap.\n"
                  "Mesin: clipper.py (Whisper lokal + ffmpeg lokal).\n"
                  "Jalan pertama download model sekali, setelah itu offline.\n")

    def _row(self, parent, label, var, cmd):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=3)
        ttk.Label(frame, text=label, width=7).pack(side="left")
        ttk.Entry(frame, textvariable=var).pack(side="left", fill="x",
                                                expand=True, padx=(0, 6))
        ttk.Button(frame, text="Pilih…", command=cmd).pack(side="left")

    def _combo(self, parent, label, var, values, col):
        ttk.Label(parent, text=label).grid(row=0, column=col * 2,
                                           padx=(0, 2))
        box = ttk.Combobox(parent, textvariable=var, values=values,
                           width=10, state="readonly")
        box.grid(row=0, column=col * 2 + 1, padx=(0, 10))

    # ---- actions ----
    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Pilih video",
            filetypes=[("Video", "*.mp4 *.mov *.mkv *.webm"), ("Semua", "*.*")])
        if path:
            self.input_var.set(path)
            src = Path(path)
            self.output_var.set(str(src.with_name(
                f"{src.stem}_vertical.mp4")))

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Simpan klip sebagai",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4")])
        if path:
            self.output_var.set(path)

    def _log(self, text):
        self.log.insert("end", text)
        self.log.see("end")

    def _log_ts(self, text):
        """Thread-safe log: worker thread jangan sentuh widget langsung."""
        self.after(0, self._log, text if text.endswith("\n") else text + "\n")

    def _start_render(self):
        src = self.input_var.get().strip()
        out = self.output_var.get().strip()
        if not src or not Path(src).exists():
            messagebox.showerror("Video belum dipilih",
                                 "Pilih dulu file videonya.")
            return
        if not out:
            messagebox.showerror("Hasil belum ditentukan",
                                 "Tentukan dulu nama file hasilnya.")
            return
        try:
            font_size = int(self.fontsize_var.get())
        except ValueError:
            messagebox.showerror("Ukuran font salah",
                                 "Ukuran font harus angka, misal 72.")
            return
        lang = self.lang_var.get()
        params = {
            "src": src, "out": out,
            "model": self.model_var.get(),
            "language": None if lang == "auto" else lang,
            "font": self.font_var.get(), "font_size": font_size,
        }
        self.render_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.status_var.set("Merender… jangan tutup jendela ini.")
        self._log(f"\nModel: {params['model']} | Bahasa: "
                  f"{lang} | Font: {params['font']} {font_size}\n")
        threading.Thread(target=self._run, kwargs=params,
                         daemon=True).start()

    def _run(self, src, out, model, language, font, font_size):
        log = self._log_ts
        try:
            words = clipper.transcribe(Path(src), model, language, log=log)
            ass_text = clipper.build_ass(words, font, font_size, "H00FFFF")
            ass_path = Path(out).with_suffix(".ass")
            ass_path.write_text(ass_text, encoding="utf-8")
            log(f"[2/3] Captions written: {ass_path} "
                f"({ass_text.count('Dialogue:')} caption events)")
            clipper.render(Path(src), ass_path, Path(out), log=log)
            ok = Path(out).exists()
        except Exception as exc:  # noqa: BLE001 — tampilkan apa adanya
            log(f"\nGAGAL: {exc}")
            ok = False
        self.after(0, self._finish, ok, out)

    def _finish(self, ok, out):
        self.render_btn.config(state="normal")
        if ok:
            self.status_var.set(f"Selesai: {out}")
            self.open_btn.config(state="normal")
            self._log("\nSelesai! Klik 'Buka hasil' untuk memutar klipnya.\n")
            messagebox.showinfo("Selesai", f"Klip berhasil dibuat:\n{out}")
        else:
            self.status_var.set("Gagal. Cek log di atas.")
            messagebox.showerror(
                "Gagal",
                "Render gagal. Cek log — biasanya karena ffmpeg belum "
                "terinstall, model belum ke-download, atau font tidak ada.")

    def _open_result(self):
        self._open_path(self.output_var.get())

    def _open_folder(self):
        out = self.output_var.get()
        folder = str(Path(out).parent) if out else str(HERE)
        self._open_path(folder)

    @staticmethod
    def _open_path(path):
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(path)  # noqa: S606 — path dari user sendiri
            elif system == "Darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Tidak bisa dibuka", str(exc))


if __name__ == "__main__":
    App().mainloop()
