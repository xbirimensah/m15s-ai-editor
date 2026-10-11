#!/usr/bin/env python3
"""Eye-contact sheet of every segment edge: is the speaker looking into the lens when a segment
starts and ends?

    python3 tools/eyes.py <workdir> [--out eyes.png] [--eyes x0,y0,x1,y1] [--head 0.4] [--tail 0.6]
                          [--step 2] [--skip 7,8]

One strip per segment of <workdir>/plan.json: the first --head and last --tail seconds, every
--step-th frame, cropped to the eye band. Labels are SOURCE times, so an edge can be set straight in
the plan (or cut with `cutflow.py render --drop`). --skip: segments that sit under full-screen b-roll.

The eye band comes from face detection on the cut (<workdir>/face.json, made here if missing) when
the cut keeps the source framing; --eyes (fractions of the frame) overrides it.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

THUMB_W = 240
DEFAULT_EYES = (0.18, 0.33, 0.78, 0.47)      # a centred talking head
FACE = config.NEXTWORK / "skills" / "style-edit" / "scripts" / "face.py"


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def eye_band(d: Path) -> tuple | None:
    """Median head box -> the band from brow to below the eyes, as fractions of the frame."""
    face = d / "face.json"
    if not face.exists():
        subprocess.run([config.python(), str(FACE), str(d)], capture_output=True)
    if not face.exists():
        return None
    boxes = [h["box"] for h in json.loads(face.read_text())["heads"] if h.get("box")]
    if not boxes:
        return None
    mid = lambda i: sorted(b[i] for b in boxes)[len(boxes) // 2]
    x, y, w, h = (mid(i) / 100 for i in range(4))
    return (max(0.0, x - 0.05 * w), max(0.0, y + 0.22 * h), min(1.0, x + 1.05 * w), min(1.0, y + 0.55 * h))


def grab(src, t, box):
    """One frame at source time t, cropped to the eye band (fractions of the displayed frame, so a
    rotated phone clip crops right)."""
    x0, y0, x1, y1 = box
    vf = f"crop=iw*{x1 - x0:.4f}:ih*{y1 - y0:.4f}:iw*{x0:.4f}:ih*{y0:.4f},scale={THUMB_W}:-2"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
                          "-vf", vf, "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if raw.returncode or not raw.stdout:
        fail(f"cannot read the frame at {t:.3f}s: {raw.stderr.decode()[-200:]}")
    from PIL import Image
    return Image.open(BytesIO(raw.stdout)).convert("RGB")


def frame_times(s, e, fps, head, tail, step):
    """Source times at the start and end of a segment, on the frame grid."""
    f0, f1 = round(s * fps), round(e * fps)
    head_f = list(range(f0, min(f1, f0 + round(head * fps)), step))
    tail_f = list(range(max(f0, f1 - round(tail * fps)), f1, step))
    if tail_f and tail_f[-1] != f1 - 1:
        tail_f.append(f1 - 1)          # always show the very last frame
    return [f / fps for f in head_f], [f / fps for f in tail_f]


def main():
    config.use_venv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--eyes", default=None)
    ap.add_argument("--head", type=float, default=0.4)
    ap.add_argument("--tail", type=float, default=0.6)
    ap.add_argument("--step", type=int, default=2)
    ap.add_argument("--skip", default="", help="segment indices not to check (under b-roll)")
    a = ap.parse_args()

    from PIL import Image, ImageDraw
    d = Path(a.workdir)
    plan_file = d / "plan.json"
    if not plan_file.exists():
        fail(f"no {plan_file}: render the cut first")
    plan = json.loads(plan_file.read_text())
    src, fps = plan["source"], plan.get("fps", 30)
    meta_file = d / "meta.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    portrait_src = meta.get("height", 0) > meta.get("width", 0)
    same_framing = (plan.get("crop_x") is None and plan.get("fit") == "cover"
                    and portrait_src == str(plan.get("format", "916")).startswith("916"))
    box = tuple(float(v) for v in a.eyes.split(",")) if a.eyes else \
        ((eye_band(d) if same_framing else None) or DEFAULT_EYES)
    skip = {int(v) for v in a.skip.split(",") if v.strip()}

    rows = []
    for i, (s, e) in enumerate(plan["segments"]):
        if i in skip:
            continue
        head_t, tail_t = frame_times(s, e, fps, a.head, a.tail, a.step)
        rows.append((i, [(t, grab(src, t, box)) for t in head_t], [(t, grab(src, t, box)) for t in tail_t]))
    if not rows:
        fail("no segments to check")

    th = rows[0][1][0][1].height if rows[0][1] else 60
    label_h, gap, left = 16, 24, 70
    cols = max(len(hd) + len(tl) for _, hd, tl in rows)
    sheet = Image.new("RGB", (left + cols * THUMB_W + gap, len(rows) * (th + label_h + 6)), "white")
    draw = ImageDraw.Draw(sheet)
    for r, (i, hd, tl) in enumerate(rows):
        y = r * (th + label_h + 6)
        draw.text((4, y + th // 2), f"seg{i:02d}", fill="black")
        x = left
        for n, (t, im) in enumerate(hd + tl):
            if n == len(hd):
                x += gap                # gap between start and end
            sheet.paste(im, (x, y))
            draw.text((x + 2, y + th + 1), f"{t:.2f}", fill="red" if n >= len(hd) else "blue")
            x += THUMB_W
    out = Path(a.out) if a.out else d / "eyes.png"
    sheet.save(out)
    print(f"✓ {out}: {len(rows)} segments, blue = start, red = end (source time); eye band {box}")


if __name__ == "__main__":
    main()
