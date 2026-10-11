#!/usr/bin/env python3
"""Seamless cut edges: two-stage waveform edges after tighten.py.

Usage:
    python3 tools/tighten.py plan.json --out plan_tight.json --thresh-db -42 --min-pause 0.15 --keep-pause 0.05
    python3 tools/edges.py plan.json plan_tight.json [--out plan_final.json] [--drop 5.87-5.97 ...]

Why:
  One threshold cannot do both: at -50 dB breaths count as speech (a 1 s gap
  after a sentence), at -42 dB soft word endings are lost ("faster" became "fast").
  So two thresholds per edge:
    - Core: the word itself at --core (-42 dB).
    - Soft: extend from there as long as it stays above --soft (-52 dB) without a break
      (max. 0.16 s at the front, 0.24 s at the back; up to two quiet windows are bridged:
      a soft "-er" ending sits at -50 dB after a dip).
    - A short block (< 0.2 s) separated from the speech by >= 0.2 s of silence is a
      breath, a click or the start of a cut take: it is dropped.
    - Parts of ONE take less than 0.2 s apart are never split (otherwise plosives go missing).
  Edges never go past the take boundary from plan.json or half the gap to the neighbour.
  So the first segment starts right on the first sound (rule: no lead-in).

Always check afterwards:
    python3 tools/cut.py plan_final.json
    ffmpeg -i <cut.mp4> -af silencedetect=noise=-40dB:d=0.12 -f null -   # no hits = no gap
    python3 tools/transcribe.py <cut.mp4>                                  # every word there?
Remove a leftover snippet (start of a cut take) with --drop START-END.
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
    fd, wav = tempfile.mkstemp(suffix=".wav", prefix="edges_")
    os.close(fd)
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", source, "-vn", "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", wav], check=True)
        with wave.open(wav) as w:
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        fail(f"Audio extraction failed: {e}")
    finally:
        os.remove(wav)
    hop = int(16000 * HOP_S)
    n = len(a) // hop
    return 20 * np.log10(np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)


def core_runs(db, core, i0, i1):
    """Loud core blocks in [i0, i1); gaps of up to 2 windows are bridged."""
    out, i = [], i0
    while i < i1:
        if db[i] <= core:
            i += 1
            continue
        j = i
        while j < i1 and (db[j] > core or (j + 2 < i1 and (db[j + 1] > core or db[j + 2] > core))):
            j += 1
        out.append([i, j])
        i = j
    return out


def drop_blips(r):
    """Short block at the edge, separated by >= 0.2 s of silence: breath, click, neighbouring take."""
    while len(r) > 1 and (r[0][1] - r[0][0]) * HOP_S < 0.2 and (r[1][0] - r[0][1]) * HOP_S >= 0.2:
        r.pop(0)
    while len(r) > 1 and (r[-1][1] - r[-1][0]) * HOP_S < 0.2 and (r[-1][0] - r[-2][1]) * HOP_S >= 0.2:
        r.pop()
    return r


def refine(db, s, e, lo, hi, a):
    """One edge: find the core, extend it softly, keep it inside [lo, hi]. None = nothing audible."""
    i0 = int(round(max(lo, s - 0.2) / HOP_S))
    i1 = min(int(round(min(hi, e + 0.2) / HOP_S)), len(db) - 1)
    r = drop_blips(core_runs(db, a.core, i0, i1))
    if not r:
        return None
    st, en = r[0][0], r[-1][1]
    k = 0
    while st - 1 > i0 and db[st - 1] > a.soft and k < 8:
        st, k = st - 1, k + 1
    k = 0
    while en < i1 and k < 12 and (db[en] > a.soft or bool((db[en + 1:en + 3] > a.soft).any())):
        en, k = en + 1, k + 1
    ns, ne = max(lo, st * HOP_S - 0.02), min(hi, en * HOP_S + 0.05)
    return (ns, ne) if ne - ns >= 0.15 else None


def main():
    ap = argparse.ArgumentParser(description="Seamless cut edges (two-stage waveform)")
    ap.add_argument("plan", help="plan.json with the wide keep segments (take boundaries)")
    ap.add_argument("tight", help="plan_tight.json from tighten.py --thresh-db -42")
    ap.add_argument("--out", default=None)
    ap.add_argument("--core", type=float, default=-42.0)
    ap.add_argument("--soft", type=float, default=-52.0)
    ap.add_argument("--drop", nargs="*", default=[], help="Remove snippets START-END (source time)")
    a = ap.parse_args()

    try:
        plan, tight = json.load(open(a.plan)), json.load(open(a.tight))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"Plan not readable: {e}")
    fps = plan.get("fps", 30)
    drops = [tuple(map(float, d.split("-"))) for d in a.drop]
    segs = [s for s in tight["segments"]
            if not any(s[0] >= x - 0.05 and s[1] <= y + 0.05 for x, y in drops)]
    db = loudness_db(plan["source"])

    final = []
    for ks, ke in plan["segments"]:
        subs = [s for s in segs if s[0] < ke and s[1] > ks]
        for n, (s, e) in enumerate(subs):
            lo = ks if n == 0 else (subs[n - 1][1] + s) / 2
            hi = ke if n == len(subs) - 1 else (e + subs[n + 1][0]) / 2
            got = refine(db, s, e, lo, hi, a)
            if not got:
                continue
            ns, ne = got
            if final and final[-1][2] == (ks, ke) and ns - final[-1][1] < 0.18:
                final[-1][1] = ne      # never split inside a take across < 0.2 s
            else:
                final.append([ns, ne, (ks, ke)])

    out = [[round(math.floor(s * fps) / fps, 5), round(math.ceil(e * fps) / fps, 5)] for s, e, _ in final]
    target = a.out or a.plan.replace(".json", "_final.json")
    json.dump(dict(plan, segments=out), open(target, "w"), indent=1)
    print(f"✓ {target}: {len(out)} segments, {sum(e - s for s, e in out):.1f}s; first starts at {out[0][0]:.2f}s")


if __name__ == "__main__":
    main()
