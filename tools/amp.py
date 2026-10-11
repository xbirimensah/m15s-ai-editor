#!/usr/bin/env python3
"""Per-frame loudness (RMS) of a WAV, for audio-reactive effects later.

Usage:
    python3 amp.py input.wav [--fps 30] [--out amp.json]

Splits the WAV into fps windows, computes RMS per window and normalises to
0..1 (95th percentile as the ceiling, so single peaks don't squash everything).
Output: JSON array [a0, a1, ...], one value per frame.
(No numpy needed.)
"""
import argparse
import json
import math
import struct
import sys
import wave


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Per-frame RMS from a WAV")
    ap.add_argument("wav", help="WAV file (16-bit PCM, mono or stereo)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", default=None, help="Target JSON (default: <stem>.amp.json)")
    args = ap.parse_args()

    try:
        w = wave.open(args.wav)
    except (FileNotFoundError, wave.Error) as e:
        fail(f"Could not open the WAV: {e}")

    if w.getsampwidth() != 2:
        fail("Expected 16-bit PCM. Convert with: ffmpeg -i in -c:a pcm_s16le -ar 16000 out.wav")

    channels = w.getnchannels()
    sr = w.getframerate()
    raw = w.readframes(w.getnframes())
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)

    # Stereo → mono (channel mean)
    if channels == 2:
        samples = [(samples[i] + samples[i + 1]) / 2 for i in range(0, len(samples) - 1, 2)]

    hop = sr / args.fps
    amps = []
    i = 0.0
    while i < len(samples):
        chunk = samples[int(i):int(i + hop)]
        if not chunk:
            break
        amps.append(math.sqrt(sum(s * s for s in chunk) / len(chunk)))
        i += hop

    if not amps:
        fail("No samples: empty WAV?")

    ceil = sorted(amps)[int(len(amps) * 0.95)] or 1.0
    norm = [round(min(1.0, a / ceil), 3) for a in amps]

    out = args.out or (args.wav.rsplit(".", 1)[0] + ".amp.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(norm, f, separators=(",", ":"))

    print(f"✓ {out}: {len(norm)} frames @ {args.fps} fps, ceiling {ceil:.0f}")


if __name__ == "__main__":
    main()
