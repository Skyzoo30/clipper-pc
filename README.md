# Clipper PC Prototype v0.1 — mesin, v0.2 — software GUI

## Versi software (GUI, v0.2) — yang baru

Bukan terminal lagi: jendela beneran. Pilih video → pilih model/bahasa →
tombol RENDER → log jalan di jendela → tombol "Buka hasil".

```bash
# Windows: klik 2x run_gui.bat
# macOS/Linux: bash run_gui.sh
# Manual: python clipper_gui.py
```

Syaratnya sama: Python 3.10+, ffmpeg di PATH, dan `pip install -r
requirements.txt` sekali (di `.venv` kalau pakai venv). GUI-nya memakai
tkinter (bawaan Python) jadi tidak butuh install tambahan.

Jujur soal status: GUI ini sudah dicek syntax-nya, tapi tampilannya belum
bisa dites di mesin ini (VM tidak ada layar) — jadi kamu yang pertama
mencobanya di PC-mu. Kalau ada tombol/ukuran yang aneh, kabarin, aku
benerin.

## Packaging Windows (.exe) — sudah disiapkan

Dua jalur, mesinnya sama:

1. **Build di PC sendiri (tanpa GitHub):** klik 2x [build_exe.bat](build_exe.bat).
   Hasil: `dist\ClipperPC\ClipperPC.exe` + file pendukung di folder yang
   sama. Folder dist cukup besar (ratusan MB) karena membungkus Python +
   runtime transkripsi — model Whisper tetap download sekali saat render
   pertama, jadi tidak ikut membengkak.
2. **Build di cloud (GitHub Actions):** push repo ini ke GitHub, workflow
   [.github/workflows/build-windows.yml](.github/workflows/build-windows.yml)
   otomatis build di `windows-latest`, hasil jadi release `build-N` berisi
   `ClipperPC-windows.zip` (download dari tab Releases).

Kenapa .exe tidak bisa di-build dari VM Linux ini: PyInstaller hanya bisa
membuat binary untuk OS tempat dia jalan. Jadi .exe Windows harus di-build
di Windows (PC-mu atau runner Actions) — spec-nya
[clipper_gui.spec](clipper_gui.spec) sudah ditulis untuk itu.

Perubahan teknis yang dilakukan demi .exe: GUI sekarang memanggil mesin
`clipper.py` lewat import (bukan subprocess Python terpisah), karena di
dalam .exe tidak ada interpreter Python lain. Dan `clipper.py` sekarang
mencari ffmpeg lewat `imageio-ffmpeg` kalau ffmpeg tidak ada di PATH.

---

# Clipper PC Prototype v0.1

Aplikasi clipper gaya SCL VSL, tapi **100% lokal: tanpa API key, tanpa
server, tanpa langganan**. Bukti konsep bahwa model bisnis "sekali bayar +
generate tanpa limit" itu mungkin — karena komputasinya numpang di PC
pembeli, bukan di server developer.

## Yang sudah jalan (v0.1)

1. **Transkrip lokal** — video lokal → teks + timestamp per kata, pakai
   `faster-whisper` (model Whisper yang jalan di CPU). Nol panggilan cloud.
2. **Caption per kata** — kata yang sedang diucapkan disorot kuning, sisanya
   putih, gaya SCL/OpusClip. Dibakar permanen ke video (file `.ass` juga
   disimpan di samping output, bisa diedit manual).
3. **Render vertikal 1080x1920** — video landscape jadi klip vertikal siap
   Shorts/Reels/TikTok, pakai latar blur (frame asli tetap utuh, bukan
   di-crop habis), audio asli dipertahankan.

## Yang BELUM ada (tahap berikut, setelah prototipe ini di-ACC)

- Cari momen otomatis dari video panjang (saat ini: kamu yang pilih potongan
  videonya, atau masukkan video pendek langsung).
- GUI, antrean batch, multi-bahasa preset, dan packaging `.exe`/installer.

## Cara jalanin di PC

**Syarat:** Python 3.10+ dan ffmpeg terinstall & masuk PATH.

```bash
# 1. (Sekali saja) siapkan environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
# Isinya: faster-whisper==1.2.1 + av==13.1.0 — kombinasi yang sudah dites.
# Jangan asal upgrade av: av 19.x mencopot API yang dipakai faster-whisper,
# dan av terlalu tua belum punya API itu. (Ini bug nyata yang ketemu pas
# ngetes prototipe ini, jadi versinya dikunci.)

# 2. Jalanin (jalan pertama download model tiny ~75 MB, sekali saja)
python clipper.py video_panjang.mp4 klip_vertikal.mp4

# 3. Opsi yang berguna
python clipper.py video.mp4 klip.mp4 --model base --language id --font Arial
```

Opsi:

| Flag | Default | Keterangan |
|---|---|---|
| `--model` | `tiny` | `tiny` (cepat) / `base` (lebih akurat) / `small` |
| `--language` | auto | `en`, `id`, dst — kosongkan untuk auto-detect |
| `--font` | `DejaVu Sans` | Windows: `Arial`. Harus terinstall di PC |
| `--font-size` | `72` | Ukuran caption di kanvas 1080x1920 |
| `--highlight` | kuning | Warna kata aktif, format ASS BGR |

## Demo yang sudah dites

- Input: potongan 28 detik video NASA "How To Eat In Space"
  (landscape 1080x608 + audio narasi Inggris).
- Output: `demo_output.mp4` — vertikal 1080x1920, caption per kata,
  ditranskrip & dirender 100% lokal di mesin ini.
- Perintah demo (pakai `--model base` biar transkripnya lebih akurat;
  default `tiny` lebih cepat tapi kualitasnya draft, file-nya tersimpan
  sebagai `demo_output_tiny.mp4` buat perbandingan):
  `python clipper.py demo_input.mp4 demo_output.mp4 --language en --model base`

## Kenapa tanpa API key itu mungkin

- Transkripsi: model Whisper lokal, bukan API cloud.
- Render: ffmpeg lokal, bukan render farm.
- Lisensi (nanti): satu-satunya yang butuh server hanyalah cek lisensi
  aktivasi — persis seperti SCL VSL: internet hanya untuk aktivasi &
  ambil video dari link, proses editing tetap di perangkat.
