#!/usr/bin/env python3
"""Lip sync per segment: cross-correlate every segment's sound in the cut against the source.

    python3 tools/sync_check.py plan.json cut.mp4 [--max-lag 1.2]

Why: length, silence and transcript checks do not see a segment whose sound comes from the wrong
place in the source (an audio seek that lands on a keyframe arrives 0.2-1.0 s late, while the picture
is right). For each segment this finds the lag at which the cut's sound best matches the source.
OK = lag 0 ms (within one frame) and correlation >= 0.8. Exit 1 when a segment is offset or silent.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 16000
MIN_CORR = 0.8


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def load(media):
    """The sound as 16 kHz mono, decoded once from the start (no seek)."""
    fd, wav = tempfile.mkstemp(suffix=".wav", prefix="sync_")
    os.close(fd)
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", media, "-vn", "-ac", "1", "-ar", str(SR),
                        "-c:a", "pcm_s16le", wav], check=True)
        with wave.open(wav) as w:
            return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    except subprocess.CalledProcessError as e:
        fail(f"cannot read the sound of {media}: {e}")
    finally:
        os.remove(wav)


def best_lag(cut_part, src, start, max_lag):
    """The lag (s) with the highest normalised correlation: 5 ms steps, then 1 ms."""
    def corr(lag):
        a = int(round((start + lag) * SR))
        x = src[a: a + len(cut_part)]
        if a < 0 or len(x) < len(cut_part):
            return -1.0
        return float(np.dot(cut_part, x) / (np.linalg.norm(cut_part) * np.linalg.norm(x) + 1e-9))
    coarse = max(np.arange(-max_lag, max_lag, 0.005), key=corr)
    fine = max(np.arange(coarse - 0.005, coarse + 0.005, 0.001), key=corr)
    return fine, corr(fine)


def check(plan_path, cut_path, max_lag=1.2) -> bool:
    plan = json.load(open(plan_path))
    fps = plan.get("fps", 30)
    xfades = {str(k): float(v) for k, v in (plan.get("xfade") or {}).items()}
    src, cut = load(plan["source"]), load(cut_path)
    t, bad = 0.0, 0
    for i, (s, e) in enumerate(plan["segments"]):
        f0, f1 = round(float(s) * fps), round(float(e) * fps)
        start, dur = f0 / fps, (f1 - f0) / fps
        x_in = xfades.get(str(i - 1), 0.0)         # the start of this segment overlaps the previous one
        x_out = xfades.get(str(i), 0.0)
        part = cut[int((t + x_in) * SR): int((t + dur - x_out) * SR)]
        lag, r = best_lag(part, src, start + x_in, max_lag) if len(part) > SR // 10 else (0.0, 1.0)
        ok = abs(lag) <= 1 / fps and r >= MIN_CORR
        bad += not ok
        print(f"{'✓' if ok else '✗'} seg{i:02d} source {start:7.2f}s  {dur:4.2f}s  lag {lag * 1000:+5.0f} ms  corr {r:.2f}")
        t += dur - x_out
    if bad:
        print(f"✗ {bad} segment(s) offset or silent")
        return False
    print(f"✓ all {len(plan['segments'])} segments in sync")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("cut")
    ap.add_argument("--max-lag", type=float, default=1.2)
    a = ap.parse_args()
    sys.exit(0 if check(a.plan, a.cut, a.max_lag) else 1)


if __name__ == "__main__":
    main()
