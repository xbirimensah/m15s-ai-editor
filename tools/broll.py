#!/usr/bin/env python3
"""HyperFrames b-roll beats that drop straight into the Remotion overlay as `broll` beats.

    python3 tools/broll.py new    <slug> <NN-name> [--seconds 3]
    python3 tools/broll.py check  <slug> <NN-name>
    python3 tools/broll.py render <slug> <NN-name> [--at-word "word" | --from-frame F] [--draft]

new     copies hyperframes/template into <workspace>/work/<slug>/broll/<NN-name>/, portrait 1080x1920,
        the beat length set, the creator's brand colours filled in, GSAP copied in locally (renders work
        offline). The agent builds the metaphor in its index.html (look: broll-style.md in the config home).
check   hyperframes lint, then check --strict (the bundled release). Both must report 0 errors and 0 warnings.
render  hyperframes render -> <workspace>/public/broll/<slug>-<NN-name>.mp4 (30 fps, delivery
        quality), verifies size, fps and length, writes a middle and a last frame to qa/, and prints the
        beat to paste into videos/<slug>.json. --at-word places it on the first word that matches
        in words.engine.json; --from-frame sets it directly.

A broll beat stays under 100 frames (the engine fades and zooms it): 3 s = 90 frames.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

TEMPLATE = config.SKILL / "hyperframes" / "template"
HF_ROOT = config.SKILL / "hyperframes"                      # a HyperFrames plugin root (plugin.json)
HF_CLI = HF_ROOT / "skills" / "hyperframes" / "scripts" / "plugin-cli.mjs"
FPS = 30
MAX_FRAMES = 99
DEFAULTS = {"BG": "#F6F5F2", "INK": "#151515", "ACCENT": "#2F6FEB", "CARD": "#FFFFFF", "MUTED": "#7A7770"}


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def beat_dir(slug, name, must_exist=True) -> Path:
    if not re.fullmatch(r"\d{2}-[a-z0-9-]+", name):
        fail(f"name '{name}': two digits, a dash, lowercase words (e.g. 03-inbox-fills)")
    d = config.work_dir(slug) / "broll" / name
    if must_exist and not (d / "index.html").exists():
        fail(f"no {d / 'index.html'}: run `broll.py new {slug} {name}` first")
    return d


def rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a: str, b: str, t: float) -> str:
    """a blended toward b by t (0..1), as hex."""
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(rgb(a), rgb(b)))


def luminance(hex_color: str) -> float:
    r, g, b = (c / 255 for c in rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def palette() -> dict:
    """Brand colours for the b-roll: creator.yaml brand.broll overrides, else the brand colours. Card and
    muted follow the ground: a dark brand gets a lifted dark card, a light one a white card, so text keeps
    its contrast either way."""
    brand = config.creator().get("brand") or {}
    colors = {**(brand.get("colors") or {}), **(brand.get("broll") or {})}
    out = dict(DEFAULTS)
    for key, src in (("BG", "bg"), ("INK", "ink"), ("ACCENT", "accent")):
        if colors.get(src):
            out[key] = colors[src]
    dark = luminance(out["BG"]) < 0.4
    out["CARD"] = colors.get("card") or (mix(out["BG"], out["INK"], 0.08) if dark else "#FFFFFF")
    out["MUTED"] = colors.get("muted") or mix(out["INK"], out["BG"], 0.45 if dark else 0.5)
    return out


def hf(*args):
    """HyperFrames through its own plugin launcher: exactly the bundled release (plugin.json), no run-time
    skill installs, run in the workspace (its node_modules holds that same version, so it is instant)."""
    if not (HF_ROOT / "plugin.json").exists() or not HF_CLI.exists():
        fail(f"the HyperFrames bundle is missing in {HF_ROOT}: bash tools/sync_hyperframes.sh")
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1"}
    return subprocess.run(["node", str(HF_CLI), *map(str, args)], cwd=config.engine(), env=env)


def cmd_new(a):
    d = beat_dir(a.slug, a.name, must_exist=False)
    if d.exists():
        fail(f"{d} exists: edit it, or pick a new NN-name")
    frames = round(a.seconds * FPS)
    if frames > MAX_FRAMES:
        fail(f"{a.seconds} s is {frames} frames; a broll beat stays under {MAX_FRAMES + 1} (3 s = 90)")
    gsap = config.engine() / "node_modules" / "gsap" / "dist" / "gsap.min.js"
    if not gsap.exists():
        fail(f"no {gsap}: run setup/install.sh (installs the engine's npm packages, gsap included)")
    shutil.copytree(TEMPLATE, d)
    shutil.copy(gsap, d / "gsap.min.js")
    html = (d / "index.html").read_text()
    fills = {"TITLE": a.name, "SECONDS": f"{a.seconds:g}", **palette()}
    for key, value in fills.items():
        html = html.replace(f"__{key}__", str(value))
    (d / "index.html").write_text(html)
    style = config.broll_style()
    print(f"✓ {d / 'index.html'} ({a.seconds:g} s, 1080x1920)")
    print(f"  look: {style}" if style.exists() else "  no broll-style.md yet: the brand colours alone set the look")


def cmd_check(a):
    d = beat_dir(a.slug, a.name)
    lint = hf("lint", d)
    chk = hf("check", d, "--strict")
    sys.exit(1 if lint.returncode or chk.returncode else 0)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    st = json.loads(out)["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    return int(st["width"]), int(st["height"]), float(num) / float(den), int(st.get("nb_frames") or 0)


def start_frame(slug, word):
    spec = config.engine() / "videos" / f"{slug}.json"
    words = json.loads(spec.read_text()).get("words") if spec.exists() else None
    words = words or json.loads((config.work_dir(slug) / "words.engine.json").read_text())
    key = re.sub(r"\W+", "", word.lower())
    for w in words:
        if re.sub(r"\W+", "", w["w"].lower()) == key:
            return round(w["s"] * FPS)
    fail(f"'{word}' is not in words.engine.json (run motion.py prepare first, or use --from-frame)")


def cmd_render(a):
    d = beat_dir(a.slug, a.name)
    m = re.search(r'data-duration="([\d.]+)"', (d / "index.html").read_text())
    seconds = float(m.group(1)) if m else 3.0
    out_dir = config.engine() / "public" / "broll"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{a.slug}-{a.name}.mp4"
    r = hf("render", d, "--fps", FPS, "--quality", "draft" if a.draft else "delivery", "--output", out)
    if r.returncode or not out.exists():
        fail("hyperframes render failed")
    w, h, fps, n = probe(out)
    frames = round(seconds * FPS)
    problems = [p for p in (
        f"size {w}x{h}, want 1080x1920" if (w, h) != (1080, 1920) else "",
        f"{fps:.2f} fps, want {FPS}" if abs(fps - FPS) > 0.01 else "",
        f"{n} frames, want at least {frames}" if n and n < frames else "",
    ) if p]
    qa = d / "qa"
    qa.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{seconds / 2:.3f}", "-i", str(out), "-frames:v", "1",
                    str(qa / "middle.png")])
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.3", "-i", str(out), "-update", "1",
                    str(qa / "last.png")])   # seeking to duration - 1 frame can land past the last frame
    for p in problems:
        print(f"✗ {p}")
    print(f"{'✗' if problems else '✓'} {out}")
    print(f"  look at {qa}/middle.png and last.png (is it still moving at the end? inside y 480-1350?)")
    frm = a.from_frame if a.from_frame is not None else (start_frame(a.slug, a.at_word) if a.at_word else None)
    beat = {"type": "broll", "from": frm if frm is not None else "<frame of the spoken word>",
            "dur": min(frames, MAX_FRAMES), "video": f"broll/{out.name}"}
    print("  beat: " + json.dumps(beat))
    sys.exit(1 if problems else 0)


def main():
    config.use_venv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("slug")
    n.add_argument("name")
    n.add_argument("--seconds", type=float, default=3.0)
    c = sub.add_parser("check")
    c.add_argument("slug")
    c.add_argument("name")
    r = sub.add_parser("render")
    r.add_argument("slug")
    r.add_argument("name")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--at-word", default=None)
    g.add_argument("--from-frame", type=int, default=None)
    r.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    {"new": cmd_new, "check": cmd_check, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    main()
