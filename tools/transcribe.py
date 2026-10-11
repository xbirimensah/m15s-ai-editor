#!/usr/bin/env python3
"""Transcription with word timestamps (mlx-whisper, Apple Silicon).

Usage:
    python3 transcribe.py <media> [--lang de] [--out words.json]

Writes TWO files:
  1. Word JSON  [{"w": "...", "s": 1.23, "e": 1.51}, ...]   (seconds, absolute)
     → the format the engine (src/spec.ts: words) expects.
  2. Plain transcript <stem>.txt with sentence segments + timestamps
     → for reading/planning the cut.

Defaults: <stem>.words.json and <stem>.txt next to the source file.
Language: auto-detected unless --lang is given. Lines of terms.txt in the config home
(blank lines and # comments skipped) go to Whisper as initial_prompt, so it spells them that way.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402


def fail(msg: str) -> None:
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def extract_wav(media: str) -> str:
    """Extract a 16 kHz mono WAV into a temp file (Whisper input)."""
    fd, wav = tempfile.mkstemp(suffix=".wav", prefix="transcribe_")
    os.close(fd)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", media,
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        wav,
    ]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        fail("ffmpeg not found: run setup/install.sh.")
    except subprocess.CalledProcessError:
        fail(f"ffmpeg could not extract audio from {media}.")
    return wav


def initial_prompt() -> Optional[str]:
    """Terms from config.terms_file() as one Whisper prompt; None without the file or terms."""
    path = config.terms_file()
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        terms = [line.strip() for line in f]
    terms = [t for t in terms if t and not t.startswith("#")]
    return ", ".join(terms) or None


def fmt_ts(t: float) -> str:
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:05.2f}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcription with word timestamps (mlx-whisper)")
    ap.add_argument("media", help="Video or audio file")
    ap.add_argument("--lang", default=None, help="Language code, e.g. de or en (default: auto-detect)")
    ap.add_argument("--out", default=None, help="Path for the word JSON (default: <stem>.words.json)")
    args = ap.parse_args()

    if not os.path.exists(args.media):
        fail(f"File not found: {args.media}")

    try:
        import mlx_whisper
    except ImportError:
        fail("mlx_whisper missing: run setup/install.sh (pip3 install --user mlx-whisper).")

    stem = os.path.splitext(args.media)[0]
    out_words = args.out or f"{stem}.words.json"
    # always put the .txt NEXT TO the word JSON (never fill up the source folder)
    _base = out_words
    for _suf in (".words.json", "_words.json", ".json"):
        if _base.endswith(_suf):
            _base = _base[: -len(_suf)]
            break
    out_txt = f"{_base}.txt"

    prompt = initial_prompt()
    wav = extract_wav(args.media)
    try:
        print(f"→ Transcribing {os.path.basename(args.media)} (language: {args.lang or 'auto'}) …")
        result = mlx_whisper.transcribe(
            wav,
            path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
            language=args.lang,
            initial_prompt=prompt,
            word_timestamps=True,
            condition_on_previous_text=False,
        )
    finally:
        os.unlink(wav)

    words = []
    lines = []
    for seg in result.get("segments", []):
        text = seg.get("text", "").strip()
        if text:
            lines.append(f"[{fmt_ts(seg['start'])} – {fmt_ts(seg['end'])}] {text}")
        for w in seg.get("words", []):
            token = w.get("word", "").strip()
            if not token:
                continue
            words.append({
                "w": token,
                "s": round(float(w["start"]), 3),
                "e": round(float(w["end"]), 3),
            })

    for _p in (out_words, out_txt):
        _d = os.path.dirname(os.path.abspath(_p))
        os.makedirs(_d, exist_ok=True)
    with open(out_words, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    dur = words[-1]["e"] if words else 0.0
    print(f"✓ {len(words)} words, last word ends at {fmt_ts(dur)}")
    print(f"✓ Word JSON:   {out_words}")
    print(f"✓ Transcript:  {out_txt}")


if __name__ == "__main__":
    main()
