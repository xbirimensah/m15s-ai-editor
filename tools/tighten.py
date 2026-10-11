#!/usr/bin/env python3
"""Put cut edges on the REAL waveform + shorten long pauses.

Usage:
    python3 tighten.py plan.json [--out plan_tight.json] [--in-pad 0.04] [--out-pad 0.06]
                                 [--min-pause 0.30] [--keep-pause 0.07]

Why: snap.py works with Whisper timestamps + generous pads (0.22/0.32 s).
Whisper is often 0.3-0.6 s off at the start of a take; the result is visible
and audible gaps at every join. This tool measures the loudness
(20 ms windows) of the source instead:

  - Speech threshold = noise floor (10th percentile) + 12 dB, capped at -50 dB.
    --thresh-db sets it explicitly: breaths often sit around -45 dB and otherwise count as speech
    (e.g. a 1 s breath gap after a sentence that only goes away at -42 dB).
  - Start = first loud block (>= 3 windows above the threshold, filters clicks)
    in the window [s, s + 0.8], minus in_pad. Never search BEFORE s: that is where
    the end of the previous take sits (snap.py already puts s after the previous word).
  - End   = last loud window in the window [e - 1.0, e], plus out_pad,
    never past the old end (otherwise the next take may bleed in).
  - Pauses inside a segment >= min_pause are shortened to 2 x keep_pause
    (the segment is split at the pause).
  - Everything quantised to the frame grid.

Input: plan.json from snap.py (field "source" = raw footage). Output: a new plan.json
for tools/cut.py.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

HOP_S = 0.02


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def loudness_db(source):
    """Loudness in dB per 20 ms window (16 kHz mono)."""
    fd, wav = tempfile.mkstemp(suffix=".wav", prefix="tighten_")
    os.close(fd)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", source, "-vn", "-ac", "1",
             "-ar", "16000", "-c:a", "pcm_s16le", wav],
            check=True,
        )
        with wave.open(wav) as w:
            sr = w.getframerate()
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        fail(f"Audio extraction failed: {e}")
    finally:
        os.remove(wav)
    a = a.astype(np.float32) / 32768
    hop = int(sr * HOP_S)
    n = len(a) // hop
    rms = np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(1))
    return 20 * np.log10(rms + 1e-9)


def idx(t):
    return int(round(t / HOP_S))


def find_onset(loud, lo, hi):
    """First index in [lo, hi) from which >= 3 windows in a row are loud."""
    for i in range(max(lo, 0), min(hi, len(loud) - 2)):
        if loud[i] and loud[i + 1] and loud[i + 2]:
            return i
    return None


def find_offset(loud, lo, hi):
    """Last loud index in [lo, hi)."""
    for i in range(min(hi, len(loud)) - 1, max(lo, 0) - 1, -1):
        if loud[i]:
            return i
    return None


def tighten_segment(s, e, loud, a):
    on = find_onset(loud, idx(s), idx(s + 0.8))
    off = find_offset(loud, idx(e - 1.0), idx(e))
    start = s if on is None else max(s, on * HOP_S - a.in_pad)
    end = e if off is None else min(e, (off + 1) * HOP_S + a.out_pad)
    if end - start < 0.2:
        return [[s, e]]

    # Shorten long pauses inside the segment.
    parts, cur = [], start
    i, last = idx(start), idx(end)
    min_run = int(round(a.min_pause / HOP_S))
    while i < last:
        if loud[i]:
            i += 1
            continue
        j = i
        while j < last and not loud[j]:
            j += 1
        if j - i >= min_run and j < last and i > idx(start):
            parts.append([cur, i * HOP_S + a.keep_pause])
            cur = j * HOP_S - a.keep_pause
        i = j
    parts.append([cur, end])
    return parts


def main():
    ap = argparse.ArgumentParser(description="Put cut edges on the waveform")
    ap.add_argument("plan")
    ap.add_argument("--out", default=None)
    ap.add_argument("--in-pad", type=float, default=0.04)
    ap.add_argument("--out-pad", type=float, default=0.06)
    ap.add_argument("--min-pause", type=float, default=0.30)
    ap.add_argument("--keep-pause", type=float, default=0.07)
    ap.add_argument("--thresh-db", type=float, default=None,
                    help="Set the speech threshold explicitly (e.g. -42) when breaths sit above the auto threshold")
    a = ap.parse_args()

    try:
        plan = json.load(open(a.plan))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"plan.json not readable: {e}")
    if not os.path.isfile(plan.get("source", "")):
        fail(f"Source not found: {plan.get('source')}")

    fps = plan.get("fps", 30)
    db = loudness_db(plan["source"])
    floor = float(np.percentile(db, 10))
    thr = a.thresh_db if a.thresh_db is not None else min(-50.0, floor + 12.0)
    loud = db > thr
    print(f"→ Noise floor {floor:.1f} dB, speech threshold {thr:.1f} dB")

    segs = []
    for s, e in plan["segments"]:
        for ps, pe in tighten_segment(s, e, loud, a):
            q = [math.floor(ps * fps) / fps, math.ceil(pe * fps) / fps]
            segs.append([round(q[0], 5), round(q[1], 5)])
            print(f"  [{s:8.2f}, {e:8.2f}] → [{q[0]:8.3f}, {q[1]:8.3f}]")

    before = sum(e - s for s, e in plan["segments"])
    after = sum(e - s for s, e in segs)
    out = dict(plan, segments=segs)
    target = a.out or a.plan.replace(".json", "_tight.json")
    json.dump(out, open(target, "w"), indent=2)
    print(f"✓ {target}: {len(segs)} segments, {before:.1f}s → {after:.1f}s")


if __name__ == "__main__":
    main()
