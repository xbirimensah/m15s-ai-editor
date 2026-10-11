#!/usr/bin/env python3
"""Word-boundary snapping: rough keep segments → clean cut plan.

Usage:
    python3 snap.py words.json segments.json --name my-video --source /path/raw.mp4 \
        [--format 916] [--fps 30] [--fit pad] [--in-pad 0.22] [--out-pad 0.32] [--out plan.json]

Input:
  words.json     [{"w": "...", "s": 1.23, "e": 1.51}, ...]  (from transcribe.py)
  segments.json  [[s, e], [s, e], ...]                       (rough seconds)

Logic (seg_bounds):
  - Segment bounds snap to the nearest word.
  - Start = word start − in_pad, but never before the middle of the pause to the previous word.
  - End   = word end + out_pad, but never past the middle of the pause to the next word.
  - Then quantised to the frame grid (fps), so the cut is frame-accurate.

Output: a ready plan.json for tools/cut.py.
"""
import argparse
import json
import sys


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def word_at(words, t):
    """Index + word whose start is closest to t."""
    idx = min(range(len(words)), key=lambda i: abs(words[i]["s"] - t))
    return idx, words[idx]


def seg_bounds(words, t_first, t_last, in_pad, out_pad):
    """Snap the bounds of a keep segment to word boundaries (pause midpoint)."""
    i0, w0 = word_at(words, t_first)
    i1, w1 = word_at(words, t_last)
    start = w0["s"] - in_pad
    if i0 > 0:
        start = max(start, (words[i0 - 1]["e"] + w0["s"]) / 2)
    end = w1["e"] + out_pad
    if i1 + 1 < len(words):
        end = min(end, (w1["e"] + words[i1 + 1]["s"]) / 2)
    return max(0.0, start), end, w0["w"], w1["w"]


def main():
    ap = argparse.ArgumentParser(description="Snap rough segments to word boundaries → plan.json")
    ap.add_argument("words", help="words.json from transcribe.py")
    ap.add_argument("segments", help="JSON file with rough keep segments [[s,e],...]")
    ap.add_argument("--name", required=True, help="Output name of the cut (lowercase)")
    ap.add_argument("--source", required=True, help="Path to the raw footage")
    ap.add_argument("--format", default="916", choices=["916", "169"])
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--fit", default="pad", choices=["pad", "cover"])
    ap.add_argument("--in-pad", type=float, default=0.22, help="Lead-in before the first word (s)")
    ap.add_argument("--out-pad", type=float, default=0.32, help="Tail after the last word (s)")
    ap.add_argument("--out", default="plan.json", help="Target file (default: plan.json)")
    args = ap.parse_args()

    with open(args.words, encoding="utf-8") as f:
        words = json.load(f)
    with open(args.segments, encoding="utf-8") as f:
        rough = json.load(f)

    if not words:
        fail("words.json is empty.")
    if not rough:
        fail("No segments given.")

    fps = args.fps
    snapped = []
    print(f"→ Snapping ({len(rough)} segments, in_pad {args.in_pad}s, out_pad {args.out_pad}s):")
    for s, e in rough:
        if e <= s:
            fail(f"Invalid segment [{s}, {e}].")
        start, end, w0, w1 = seg_bounds(words, float(s), float(e), args.in_pad, args.out_pad)
        # Quantise to the frame grid
        fstart = round(start * fps) / fps
        fend = round(end * fps) / fps
        snapped.append([round(fstart, 5), round(fend, 5)])
        print(f"  [{s:8.2f}, {e:8.2f}] → [{fstart:8.3f}, {fend:8.3f}]  ({w0} … {w1})")

    # Merge overlaps after snapping. Only true overlap: a segment that starts before the previous
    # one is an earlier take (a sentence from take 1 after take 2) and stays separate.
    merged = [snapped[0]]
    for s, e in snapped[1:]:
        if merged[-1][0] <= s <= merged[-1][1]:
            print(f"⚠ Segments overlap after snapping: merged at {s:.3f}s.")
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    plan = {
        "name": args.name.lower(),
        "source": args.source,
        "format": args.format,
        "fps": fps,
        "speed": 1.0,
        "fit": args.fit,
        "crop_x": None,
        "segments": merged,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    total = sum(e - s for s, e in merged)
    print(f"✓ {args.out} written: {len(merged)} segments, {total:.1f}s total.")
    print(f"  → cut with: python3 tools/cut.py {args.out}")


if __name__ == "__main__":
    main()
