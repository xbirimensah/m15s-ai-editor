#!/usr/bin/env python3
"""Motion graphics on an approved cut: Remotion overlays, one continuous video track underneath.

    python3 tools/motion.py prepare <slug> [--aspect 916|169]
    python3 tools/motion.py check   <slug>
    python3 tools/motion.py stills  <slug> [--open]
    python3 tools/motion.py render  <slug> [--draft]
    python3 tools/motion.py srt     <slug>
    python3 tools/motion.py export  <slug>

prepare  cut.mp4 -> <workspace>/public/cut/<slug>.mp4; caption words from what the verify pass heard in
         the cut, corrected to the approved text, the creator's pronunciation fixes and every
         `retakes.py fix`; where the head is (face.json) and the caption line / panel side that keeps
         it clear (layout.json); a spec skeleton <workspace>/videos/<slug>.json (theme, words, captions,
         a hook bar for the first hookbar.seconds) that the agent fills with beats. Never overwrites a spec.
check    every beat and cue inside the video, hook bar length, cue spacing, longest stretch without a
         visual, on-screen text bans (em dash, dates), captions inside the Instagram safe zone,
         AI tells (tools/ai_tells.py) and the TypeScript check. Exit 1 on a FAIL.
stills   one still per beat at the moment it is complete, rendered in one bundle, plus
         stills/sheet.png: numbered, labelled, safe-zone lines drawn. The approval gate before render.
render   the full render to <workspace>/out/<slug>.mp4 (--draft: half size, quick look), then checks:
         duration, audio present, 4:5 crop frames in qa/.
srt      captions.srt next to the cut, one line per caption, for an editor or a platform upload.
export   work/<slug>/export/: cut.mp4, overlay.mov (the beats alone, ProRes 4444 with alpha) and
         captions.srt. Put the cut on track 1 and the overlay on track 2 in Final Cut, Premiere,
         Resolve or CapCut to finish by hand. Captions are part of the overlay unless --no-captions.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

CUT = config.NEXTWORK / "skills" / "cut" / "scripts"
FACE = config.NEXTWORK / "skills" / "style-edit" / "scripts" / "face.py"
FPS = 30
FRAME_H = {"916": 1920, "169": 1080}
IG_TOP, IG_BOTTOM = 250, 1420          # engine IG_SAFE_916: nothing above / below these lines
CAPTION_Y_MAX = 1340                   # the caption line's y the engine still keeps inside IG_BOTTOM
CAPTION_GAP_PX = 40                    # caption line sits this far under the lowest point of the head
CUE_SPACING = 60                       # two entries closer than this read as one movement
HOOKBAR_H = 230                        # the hook bar's height at most (two lines of 76 px type)
FACE_FROM = 0.25                       # the face starts this far down the head box (above it: hair)
MAX_EMPTY_S = 10                       # longest stretch with nothing but captions
CAPTION_CHARS = {"sans": 26, "serif": 34}
DEFAULT_THEME = {"bg": "#16121C", "ink": "#F7F4EF", "accent": "#D4AF37", "accent2": "#C9A961",
                 "capActive": "#D4AF37", "serif": "Playfair Display", "sans": "Plus Jakarta Sans"}
CUE_KEYS = ("at", "verdictAt")
LOCALES = {"de": "de-DE", "en": "en-US", "fr": "fr-FR", "es": "es-ES", "it": "it-IT", "nl": "nl-NL"}
MONTHS = ("january|february|march|april|june|july|august|september|october|november|december|"
          "januar|februar|märz|juni|juli|oktober|dezember")
DATE_RE = re.compile(rf"\b\d{{1,2}}\.\d{{1,2}}\.|\b\d{{1,2}}/\d{{1,2}}/|\b({MONTHS})\b", re.I)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")         # a year, or just a number like 2000: WARN only


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def edit_dir(slug) -> Path:
    d = config.work_dir(slug)
    if not (d / "cut.mp4").exists():
        fail(f"no {d / 'cut.mp4'}: cut and approve first (tools/cutflow.py)")
    return d


def meta(d: Path) -> dict:
    f = d / "meta.json"
    return json.loads(f.read_text()) if f.exists() else {}


def save_meta(d: Path, **kw):
    (d / "meta.json").write_text(json.dumps({**meta(d), **kw}, indent=1))


def spec_path(slug) -> Path:
    return config.engine() / "videos" / f"{slug}.json"


def composition(d: Path) -> str:
    return "Overlay169" if meta(d).get("aspect") == "169" else "Overlay916"


def seconds(path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=nw=1:nk=1", str(path)], capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def run(cmd, cwd=None, check=True):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd)
    if check and r.returncode:
        fail(f"{Path(str(cmd[1] if len(cmd) > 1 else cmd[0])).name} stopped (exit {r.returncode})")
    return r


# ---------------------------------------------------------------------------------------------
def theme() -> dict:
    brand = config.creator().get("brand") or {}
    colors, fonts = brand.get("colors") or {}, brand.get("fonts") or {}
    t = dict(DEFAULT_THEME)
    t.update({k: v for k, v in {"bg": colors.get("bg"), "ink": colors.get("ink"), "accent": colors.get("accent"),
                                "accent2": colors.get("accent2"), "capActive": colors.get("cap_active"),
                                "serif": fonts.get("serif"), "sans": fonts.get("sans")}.items() if v})
    return t


def caption_words(d: Path) -> list:
    """captions.json (NextWork: heard words, corrected) with the creator's pronunciation fixes."""
    fixes_file = d / "fixes.json"
    fixes = json.loads(fixes_file.read_text()) if fixes_file.exists() else {}
    for old, new in config.pronunciation_fixes().items():
        fixes.setdefault(str(old), str(new))
    fixes_file.write_text(json.dumps(fixes, indent=1, ensure_ascii=False))
    run([config.python(), CUT / "retakes.py", "captions", d])
    words = json.loads((d / "captions.json").read_text())
    return [{"w": w["text"].strip(), "s": round(w["start"], 3), "e": round(w["end"], 3)}
            for w in words if w.get("text", "").strip()]


def layout(d: Path, aspect: str) -> dict:
    """Lowest point of the head over the whole cut -> caption line and panel side that keep it clear."""
    r = subprocess.run([config.python(), str(FACE), str(d)], capture_output=True, text=True)
    if r.returncode or not (d / "face.json").exists():
        print("⚠ face.py found no head data (look at a frame and place captions by hand): "
              + (r.stderr.strip().splitlines() or ["no output"])[-1])
        return {}
    heads = [h["box"] for h in json.loads((d / "face.json").read_text())["heads"] if h.get("box")]
    if not heads:
        return {}
    h_px = FRAME_H[aspect]
    bottoms = sorted(b[1] + b[3] for b in heads)
    centres = sorted(b[1] + b[3] / 2 for b in heads)
    tops = sorted(b[1] for b in heads)
    heights = sorted(b[3] for b in heads)
    low = bottoms[int(0.95 * (len(bottoms) - 1))] / 100 * h_px
    centre = centres[len(centres) // 2] / 100 * h_px
    top = tops[int(0.05 * (len(tops) - 1))] / 100 * h_px
    face_top = top + FACE_FROM * heights[len(heights) // 2] / 100 * h_px
    out = {
        "head_top_px": round(top),
        "face_top_px": round(face_top),
        "head_bottom_px": round(low),
        "head_centre_px": round(centre),
        "caption_y": int(min(CAPTION_Y_MAX, max(1010, low + CAPTION_GAP_PX))),
        "panel_position": "bottom" if centre < h_px / 2 else "top",
        "head_found_share": round(len(heads) / len(json.loads((d / "face.json").read_text())["heads"]), 2),
    }
    if low + CAPTION_GAP_PX > CAPTION_Y_MAX:
        out["note"] = "the head reaches below the caption zone: captions will touch the chin; consider plain style"
    if face_top - IG_TOP >= HOOKBAR_H + 10:           # room above the face (over the hair is fine)
        out["hookbar_y"] = int(face_top - HOOKBAR_H - 10)
    elif out["caption_y"] - (low + 20) >= HOOKBAR_H + 10:   # room between the chin and the captions
        out["hookbar_y"] = int(low + 20)
    else:
        out["hookbar_y"] = IG_TOP
        out["hookbar_note"] = "no free band: the hook bar sits at the top of the safe zone, over the forehead"
    (d / "layout.json").write_text(json.dumps(out, indent=1))
    return out


def first_line(words, n=7) -> str:
    text = []
    for w in words:
        text.append(w["w"])
        if len(text) >= n or w["w"].endswith((".", "?", "!")):
            break
    return " ".join(text).rstrip(".,")


def cmd_prepare(a):
    d = edit_dir(a.slug)
    aspect = a.aspect or meta(d).get("aspect") or str(config.creator().get("format") or "916")
    save_meta(d, aspect=aspect)
    pub = config.engine() / "public" / "cut"
    pub.mkdir(parents=True, exist_ok=True)
    shutil.copy(d / "cut.mp4", pub / f"{a.slug}.mp4")
    print(f"✓ cut      {pub / (a.slug + '.mp4')}")

    if not (d / "cut.transcript.json").exists():
        run([config.python(), CUT / "verify_cut.py", d], check=False)
    words = caption_words(d)
    (d / "words.engine.json").write_text(json.dumps(words, indent=1, ensure_ascii=False))
    print(f"✓ words    {len(words)} caption words (proofread {d / 'captions.txt'})")

    lay = layout(d, aspect)
    if lay:
        print(f"✓ layout   face from y {lay['face_top_px']} down to y {lay['head_bottom_px']}, captions y "
              f"{lay['caption_y']}, hook bar y {lay['hookbar_y']}, panels {lay['panel_position']}"
              + "".join(f"  ⚠ {lay[k]}" for k in ("note", "hookbar_note") if lay.get(k)))

    sp = spec_path(a.slug)
    if sp.exists():
        if a.refresh_words:
            spec = json.loads(sp.read_text())
            spec["words"] = words
            sp.write_text(json.dumps(spec, indent=1, ensure_ascii=False))
            print(f"✓ spec     {sp}: words replaced, beats kept")
        else:
            print(f"• spec     {sp} exists, left as it is (after a word fix: prepare --refresh-words)")
        return
    c = config.creator()
    cap = c.get("captions") or {}
    hook_s = float((c.get("hookbar") or {}).get("seconds", 3))
    y = cap.get("y")
    if lay and (y is None or y < lay["head_bottom_px"] + CAPTION_GAP_PX):
        y = lay["caption_y"]
    spec = {
        "video": f"cut/{a.slug}.mp4",
        "durationInFrames": round(seconds(d / "cut.mp4") * FPS),
        "fps": FPS,
        "theme": theme(),
        "words": words,
        "captions": {k: v for k, v in {"enabled": True, "y": y, "font": cap.get("font", "sans"),
                                       "style": cap.get("style")}.items() if v is not None},
        "music": None,
        "locale": LOCALES.get(str(c.get("language") or "en")[:2], "en-US"),
        "beats": [{"type": "hookbar", "from": 0, "dur": round(hook_s * FPS), "text": first_line(words),
                   **({"y": lay["hookbar_y"]} if lay.get("hookbar_y") is not None else {})}],
    }
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    print(f"✓ spec     {sp} (theme, words, captions, hook bar {hook_s:g} s): add the beats next")


# ---------------------------------------------------------------------------------------------
def beat_cues(b) -> list:
    cues = [b.get(k) for k in CUE_KEYS if isinstance(b.get(k), (int, float))]
    cues += list(b.get("itemAt") or [])
    for key in ("rows", "items", "steps"):
        cues += [x["at"] for x in b.get(key) or [] if isinstance(x, dict) and isinstance(x.get("at"), (int, float))]
    return cues


def beat_texts(b) -> list:
    out = []
    for key in ("text", "title", "eyebrow", "sub", "label", "value", "name", "cta"):
        if isinstance(b.get(key), str):
            out.append(b[key])
    for key in ("lines", "items"):
        out += [x if isinstance(x, str) else x.get("text", "") for x in b.get(key) or []]
    for key in ("rows", "steps"):
        out += [x.get("text") or x.get("label") or "" for x in b.get(key) or []]
    for key in ("left", "right"):
        if isinstance(b.get(key), dict):
            out.append(b[key].get("label", ""))
    return [t for t in out if t]


def plan_findings(spec, d: Path) -> tuple[list, list]:
    fails, warns = [], []
    fps = spec.get("fps", FPS)
    total = spec["durationInFrames"]
    cut_frames = round(seconds(d / "cut.mp4") * fps)
    if abs(cut_frames - total) > 2:
        fails.append(f"durationInFrames {total} but the cut is {cut_frames} frames")
    beats = spec.get("beats", [])
    c = config.creator()
    bans = c.get("text_bans") or {"em_dash": True, "dates": True}
    hook_s = float((c.get("hookbar") or {}).get("seconds", 3))
    hookbars = [b for b in beats if b["type"] == "hookbar"]
    if not hookbars:
        warns.append("no hook bar (every reel opens with one unless the user said otherwise)")
    lay = json.loads((d / "layout.json").read_text()) if (d / "layout.json").exists() else {}
    for b in hookbars:
        bar = (b.get("y", 880), b.get("y", 880) + HOOKBAR_H)
        if lay and "face_top_px" in lay and bar[0] < lay["head_bottom_px"] and bar[1] > lay["face_top_px"]:
            if lay.get("hookbar_note"):
                warns.append(f"hook bar y {bar[0]} touches the face; {lay['hookbar_note']}")
            else:
                fails.append(f"hook bar y {bar[0]}-{bar[1]} covers the face (y {lay['face_top_px']}-"
                             f"{lay['head_bottom_px']}): set its y to {lay['hookbar_y']}")
        if b["from"] != 0 or b["dur"] != round(hook_s * fps):
            fails.append(f"hook bar must run from frame 0 for {hook_s:g} s ({round(hook_s * fps)} frames), "
                         f"is from {b['from']} for {b['dur']}")
    for i, b in enumerate(beats):
        end = b["from"] + b["dur"]
        if b["from"] < 0 or end > total:
            fails.append(f"beat {i} {b['type']} runs {b['from']}-{end}, outside 0-{total}")
        for cue in beat_cues(b):
            if not b["from"] <= cue < end:
                fails.append(f"beat {i} {b['type']}: cue {cue} outside its beat {b['from']}-{end}")
        for t in beat_texts(b):
            if bans.get("em_dash") and "—" in t:
                fails.append(f"beat {i} {b['type']}: em dash in {t!r}")
            if bans.get("dates") and DATE_RE.search(t):
                fails.append(f"beat {i} {b['type']}: a date in {t!r} (on-screen text stays evergreen)")
            elif bans.get("dates") and t != b.get("value") and YEAR_RE.search(t):   # a stat's number is no year
                warns.append(f"beat {i} {b['type']}: {t!r} looks like a year (evergreen?)")
    entries = sorted([b["from"] for b in beats if b["type"] != "kicker"]
                     + [cue for b in beats for cue in beat_cues(b)])
    close = [(x, y) for x, y in zip(entries, entries[1:]) if 0 < y - x < CUE_SPACING]
    if close:
        warns.append(f"{len(close)} pair(s) of entries under {CUE_SPACING} frames apart, e.g. "
                     + ", ".join(f"{x}/{y}" for x, y in close[:4]))
    visual = sorted((b["from"], b["from"] + b["dur"]) for b in beats if b["type"] not in ("kicker",))
    t, longest = 0, (0, 0)
    for s, e in visual:
        if s - t > longest[1] - longest[0]:
            longest = (t, s)
        t = max(t, e)
    if total - t > longest[1] - longest[0]:
        longest = (t, total)
    if (longest[1] - longest[0]) / fps > MAX_EMPTY_S:
        warns.append(f"{(longest[1] - longest[0]) / fps:.0f} s with nothing but captions "
                     f"({longest[0] / fps:.1f}-{longest[1] / fps:.1f} s): add a beat or a kicker change")
    cap = spec.get("captions") or {}
    if composition(d) == "Overlay916" and cap.get("y") is not None and not IG_TOP <= cap["y"] <= CAPTION_Y_MAX:
        fails.append(f"captions y {cap['y']} outside the Instagram safe zone ({IG_TOP}-{CAPTION_Y_MAX})")
    if lay and cap.get("y") is not None and cap["y"] < lay["head_bottom_px"]:
        if lay.get("note"):     # a close-up: no line is both under the chin and inside the safe zone
            warns.append(f"close-up: the head reaches y {lay['head_bottom_px']}, below the lowest safe caption "
                         f"line ({CAPTION_Y_MAX}); captions will touch the chin. Ask the user: plain style, or "
                         f"captions over the chin")
        else:
            fails.append(f"captions y {cap['y']} sits on the head (head reaches y {lay['head_bottom_px']})")
    return fails, warns


def cmd_check(a):
    d = edit_dir(a.slug)
    sp = spec_path(a.slug)
    if not sp.exists():
        fail(f"no spec {sp}: run prepare first")
    spec = json.loads(sp.read_text())
    fails, warns = plan_findings(spec, d)
    for w in warns:
        print(f"WARN  {w}")
    for f in fails:
        print(f"FAIL  {f}")
    tells = run([config.python(), config.TOOLS / "ai_tells.py", sp], check=False)
    tsc = run(["npx", "tsc", "--noEmit"], cwd=config.engine(), check=False)
    bad = bool(fails) or tells.returncode != 0 or tsc.returncode != 0
    print(("✗" if bad else "✓") + f" plan {sp.name}: {len(fails)} fail, {len(warns)} warn"
          + (", AI tells failed" if tells.returncode else "") + (", tsc failed" if tsc.returncode else ""))
    sys.exit(1 if bad else 0)


# ---------------------------------------------------------------------------------------------
def still_frames(spec) -> list:
    """(frame, label): each beat when it is complete, and a captions-only frame in each long gap."""
    fps = spec.get("fps", FPS)
    total = spec["durationInFrames"]
    out = []
    for i, b in enumerate(spec.get("beats", [])):
        cues = beat_cues(b)
        settle = round(0.6 * fps)
        # no cues: wait until entrances and count-ups have landed (1.5 s), never past the beat
        f = (max(cues) + settle) if cues else b["from"] + min(b["dur"] - 1, round(1.5 * fps))
        if b["type"] == "hookbar":
            f = min(b["from"] + 15, b["from"] + b["dur"] - 1)
        out.append((min(f, b["from"] + b["dur"] - 1, total - 1), f"{i + 1:02d}-{b['type']}"))
    busy = sorted((b["from"], b["from"] + b["dur"]) for b in spec.get("beats", []) if b["type"] != "kicker")
    t = 0
    for s, e in busy + [(total, total)]:
        if s - t > 4 * fps:
            out.append(((t + s) // 2, f"zz-captions-{(t + s) // 2}"))
        t = max(t, e)
    return sorted(out)


def contact_sheet(stills, labels, out: Path, aspect: str):
    from PIL import Image, ImageDraw, ImageFont
    tw = 270 if aspect == "916" else 480
    th = 480 if aspect == "916" else 270
    cols = 6 if aspect == "916" else 4
    rows = (len(stills) + cols - 1) // cols
    pad, label_h = 10, 34
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + label_h + pad) + pad), "#1c1c1c")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=18)
    except TypeError:
        font = ImageFont.load_default()
    for n, (img_path, label) in enumerate(zip(stills, labels)):
        im = Image.open(img_path).convert("RGB")
        scale = th / im.height
        im = im.resize((tw, th))
        x = pad + (n % cols) * (tw + pad)
        y = pad + (n // cols) * (th + label_h + pad)
        sheet.paste(im, (x, y))
        if aspect == "916":   # Instagram safe zone: nothing above / below these lines
            for line_y in (IG_TOP, IG_BOTTOM):
                yy = y + round(line_y * scale)
                draw.line([(x, yy), (x + tw, yy)], fill="#ff4d4d", width=1)
        draw.text((x + 4, y + th + 6), f"{n + 1}  {label}", fill="#f2f2f2", font=font)
    sheet.save(out)


def cmd_stills(a):
    d = edit_dir(a.slug)
    sp = spec_path(a.slug)
    spec = json.loads(sp.read_text())
    frames = still_frames(spec)
    sd = d / "stills"
    shutil.rmtree(sd, ignore_errors=True)
    sd.mkdir(parents=True)
    fps = spec.get("fps", FPS)
    args = [f"{f}:{label}" for f, label in frames]
    run(["node", "scripts/stills.mjs", composition(d), sp, sd, *args], cwd=config.engine())
    pngs = [sd / f"{label}.png" for _, label in frames]
    labels = [f"{label.split('-', 1)[1]} {f / fps:.1f}s" for f, label in frames]
    contact_sheet(pngs, labels, sd / "sheet.png", meta(d).get("aspect", "916"))
    print(f"✓ {sd / 'sheet.png'} ({len(pngs)} stills; red lines = Instagram safe zone)")
    if a.open:
        subprocess.run(["open", str(sd / "sheet.png")])


# ---------------------------------------------------------------------------------------------
def cmd_render(a):
    d = edit_dir(a.slug)
    sp = spec_path(a.slug)
    spec = json.loads(sp.read_text())
    name = f"{a.slug}-draft.mp4" if a.draft else f"{a.slug}.mp4"
    out = config.engine() / "out" / name
    cmd = ["npx", "remotion", "render", composition(d), f"out/{name}", f"--props={sp}", "--concurrency=2"]
    if a.draft:
        cmd.append("--scale=0.5")
    run(cmd, cwd=config.engine())
    ok = True
    want = spec["durationInFrames"] / spec.get("fps", FPS)
    got = seconds(out)
    if abs(got - want) > 0.1:
        ok = False
        print(f"✗ duration {got:.2f}s, spec says {want:.2f}s")
    else:
        print(f"✓ duration {got:.2f}s")
    vol = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(out), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    peak = re.search(r"max_volume: (-?[\d.inf]+) dB", vol)
    if not peak or "inf" in peak.group(1):
        ok = False
        print("✗ audio    silent render (the cut's sound is missing)")
    else:
        print(f"✓ audio    peak {peak.group(1)} dB")
    if composition(d) == "Overlay916" and not a.draft:
        qa = d / "qa"
        qa.mkdir(exist_ok=True)
        fps = spec.get("fps", FPS)
        for f, label in still_frames(spec)[:4]:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{f / fps:.3f}", "-i", str(out), "-frames:v", "1",
                            "-vf", "crop=1080:1350:0:285", str(qa / f"crop45-{label}.png")])
        print(f"✓ 4:5 crop frames in {qa} (look: is every caption and card inside?)")
    print(f"{'✓' if ok else '✗'} {out}")
    sys.exit(0 if ok else 1)


def spec_words(slug, d: Path) -> list:
    """The words as proofread in the spec, else as prepare wrote them."""
    sp = spec_path(slug)
    if sp.exists():
        return json.loads(sp.read_text()).get("words") or []
    return json.loads((d / "words.engine.json").read_text())


def cmd_srt(a):
    d = edit_dir(a.slug)
    words = spec_words(a.slug, d)
    font = ((config.creator().get("captions") or {}).get("font") or "sans")
    limit = CAPTION_CHARS.get(font, 26)
    lines, cur = [], []
    for w in words:
        if cur and (len(" ".join(x["w"] for x in cur + [w])) > limit or w["s"] - cur[-1]["e"] > 0.6):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)

    def ts(t):
        ms = round(t * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    body = [f"{n}\n{ts(l[0]['s'])} --> {ts(l[-1]['e'])}\n{' '.join(x['w'] for x in l)}\n" for n, l in enumerate(lines, 1)]
    (d / "captions.srt").write_text("\n".join(body), encoding="utf-8")
    print(f"✓ {d / 'captions.srt'} ({len(lines)} one-line captions)")


def cmd_export(a):
    d = edit_dir(a.slug)
    sp = spec_path(a.slug)
    spec = json.loads(sp.read_text())
    ex = d / "export"
    ex.mkdir(exist_ok=True)
    overlay_spec = {**spec, "overlayOnly": True}
    if a.no_captions:
        overlay_spec["captions"] = {**(spec.get("captions") or {}), "enabled": False}
    tmp = d / "overlay.props.json"
    tmp.write_text(json.dumps(overlay_spec, ensure_ascii=False))
    out = ex / "overlay.mov"
    run(["npx", "remotion", "render", composition(d), out, f"--props={tmp}", "--concurrency=2",
         "--codec=prores", "--prores-profile=4444", "--pixel-format=yuva444p10le", "--image-format=png"],
        cwd=config.engine())
    shutil.copy(d / "cut.mp4", ex / "cut.mp4")
    if not (d / "captions.srt").exists():
        cmd_srt(a)
    shutil.copy(d / "captions.srt", ex / "captions.srt")
    print(f"✓ {ex}: cut.mp4 on track 1, overlay.mov (alpha) on track 2, captions.srt")


def main():
    config.use_venv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("slug")
    p.add_argument("--aspect", choices=("916", "169"), default=None)
    p.add_argument("--refresh-words", action="store_true", help="replace the words in an existing spec")
    for name in ("check", "srt"):
        sub.add_parser(name).add_argument("slug")
    s = sub.add_parser("stills")
    s.add_argument("slug")
    s.add_argument("--open", action="store_true")
    r = sub.add_parser("render")
    r.add_argument("slug")
    r.add_argument("--draft", action="store_true")
    e = sub.add_parser("export")
    e.add_argument("slug")
    e.add_argument("--no-captions", action="store_true")
    a = ap.parse_args()
    {"prepare": cmd_prepare, "check": cmd_check, "stills": cmd_stills, "render": cmd_render,
     "srt": cmd_srt, "export": cmd_export}[a.cmd](a)


if __name__ == "__main__":
    main()
