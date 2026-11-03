#!/usr/bin/env python3
"""clipper.py — PC clipper prototype v0.1 (SCL-style, fully local, no API key).

What it does:
  1. Transcribes a local video with faster-whisper (runs on your CPU, no cloud,
     no API key, no account).
  2. Builds word-by-word captions: the currently spoken word is highlighted,
     the rest of the line stays white — the SCL/OpusClip look.
  3. Renders a vertical 1080x1920 clip: blurred-pad background (full frame
     kept) with the video centred, captions burned in, original audio kept.

What it does NOT do yet (next steps after this prototype is approved):
  - Auto moment-finding (picking the best 30-60s from a long video).
  - GUI, batch queue, .exe packaging.

Requirements on the PC:
  - Python 3.10+, ffmpeg in PATH, then:  pip install faster-whisper
  - First run downloads the tiny model (~75 MB) into ~/.cache/huggingface.

Usage:
  python clipper.py input.mp4 output.mp4
  python clipper.py input.mp4 output.mp4 --model base --language en --font Arial
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def fmt_time(seconds: float) -> str:
    """ASS timestamp: H:MM:SS.cc"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ffmpeg_exe() -> str:
    """Resolve ffmpeg: explicit env override, PATH, else bundled binary.

    The bundled path matters for the frozen .exe, where the user's PC may
    not have ffmpeg installed at all: imageio-ffmpeg ships a static build.
    """
    env = os.environ.get("CLIPPER_FFMPEG")
    if env:
        return env
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        return get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def transcribe(path: Path, model_name: str, language: str | None,
               log=print):
    """Local transcription with word timestamps. Returns list of words."""
    from faster_whisper import WhisperModel

    log(f"[1/3] Loading local model '{model_name}' (CPU, int8)...")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(
        str(path), language=language, word_timestamps=True
    )
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append((float(w.start), float(w.end), text))
    if not words:
        raise RuntimeError("No speech detected — nothing to caption.")
    log(f"      {len(words)} words transcribed, all on-device.")
    return words


def chunk_words(words, max_words: int = 5):
    """Split words into caption chunks: max N words, cut at sentence ends."""
    chunks, current = [], []
    for word in words:
        current.append(word)
        ended = word[2][-1] in ".!?…" if word[2] else False
        if len(current) >= max_words or ended:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def build_ass(words, font: str, font_size: int, highlight: str) -> str:
    """One ASS event per word-span: current word highlighted, rest white.

    Events tile each chunk end-to-end, so there are no caption gaps and no
    karaoke-tag quirks — the render is identical on every ffmpeg build.
    """
    white = r"{\1c&H00FFFFFF&}"
    hi_open = r"{\1c&" + highlight + r"&}"
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Clip,{font},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,"
        f"&H80000000,-1,0,0,0,100,100,0,0,3,2,0,2,60,60,320,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text",
    ]
    for chunk in chunk_words(words):
        for i, (start, _end, _text) in enumerate(chunk):
            end = chunk[i + 1][0] if i + 1 < len(chunk) else chunk[-1][1]
            if end <= start:
                end = start + 0.05
            parts = []
            for j, (_s, _e, text) in enumerate(chunk):
                if j == i:
                    parts.append(f"{hi_open}{text}{white}")
                else:
                    parts.append(text)
            text = " ".join(parts)
            lines.append(
                f"Dialogue: 0,{fmt_time(start)},{fmt_time(end)},Clip,,0,0,0,,{text}"
            )
    return "\n".join(lines) + "\n"


def render(video: Path, ass_path: Path, output: Path, log=print):
    """Vertical 1080x1920 render: blurred-pad background + burned captions."""
    # Quotes inside the filter must survive the shell: pass argv, not a string.
    fc = (
        "[0:v]split[a][b];"
        "[a]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=25[bg];"
        "[b]scale=1080:-2[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,subtitles='{ass_path}'[v]"
    )
    cmd = [
        ffmpeg_exe(), "-y", "-v", "error",
        "-i", str(video),
        "-filter_complex", fc,
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output),
    ]
    log("[3/3] Rendering vertical clip...")
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", type=Path, help="Local video file (mp4/mov/mkv...)")
    ap.add_argument("output", type=Path, help="Vertical output clip (mp4)")
    ap.add_argument("--model", default="tiny",
                    help="Whisper model: tiny/base/small (default: tiny)")
    ap.add_argument("--language", default=None,
                    help="e.g. en, id — default: auto-detect")
    ap.add_argument("--font", default="DejaVu Sans",
                    help="Caption font (Windows: Arial, macOS: Helvetica)")
    ap.add_argument("--font-size", type=int, default=72)
    ap.add_argument("--highlight", default="H00FFFF",
                    help="ASS BGR colour for the spoken word, no leading & "
                    "(default: yellow)")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2

    words = transcribe(args.input, args.model, args.language)
    ass_text = build_ass(words, args.font, args.font_size, args.highlight)
    ass_path = args.output.with_suffix(".ass")
    ass_path.write_text(ass_text, encoding="utf-8")
    print(f"[2/3] Captions written: {ass_path} "
          f"({ass_text.count('Dialogue:')} caption events)")
    render(args.input, ass_path, args.output)
    print(f"Done: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
