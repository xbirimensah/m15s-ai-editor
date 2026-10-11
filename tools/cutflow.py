#!/usr/bin/env python3
"""The cut, end to end: NextWork decides WHAT goes, the waveform cutter decides WHERE the edges sit.

    python3 tools/cutflow.py transcribe <source> <slug> [--lang de]
    python3 tools/cutflow.py build      <slug> [--dry-run]
    python3 tools/cutflow.py render     <slug> [--format auto|916|916_4k|...] [--fit cover|pad]
                                               [--crop-x PX] [--no-open]
    python3 tools/cutflow.py checks     <slug>
    python3 tools/cutflow.py hook       <slug> <n>

Everything lands in <workspace>/work/<slug>/ (tools/config.py). The source file is never touched.

transcribe  NextWork transcribe.py (mlx-whisper large-v3-turbo, terms.txt as vocabulary) ->
            words.raw.json, then retakes.py propose -> transcript.txt, candidates.md, hooks.json.
            The agent reads transcript.txt + candidates.md and writes spans.json (quoted cuts).
build       build_timeline.py --edges waveform: the quoted spans (and "move" entries) become the final kept
            ranges with edges set on the audio: each run starts on its first sound and ends on its last,
            pauses over 0.15 s become 2 x 0.05 s, each edge in two stages (word core at -42 dB, soft
            endings to -52 dB), breaths and stray take starts dropped, words the edges took for silence
            restored. Writes decisions.json, words.json, paper-edit.md (the cut as text, play order).
render      1. decisions.json -> plan.json (format, size and fps from the source)
            2. cut.py: frame-accurate picture, sound cut from one exact PCM decode (no seek drift),
               12 ms fades, gentle loudness
            3. verify_cut.py (re-transcribes cut.mp4, and each run alone: MISSING / SURVIVED / REPEAT)
               + checks + cut-check.html
checks      no silence over 0.12 s, audio length = video length, every segment's sound in sync with
            the source (tools/sync_check.py), first word under 0.5 s, peak level, every kept word heard.
hook        <slug>-hook<n>: the same cut opening on alternate hook n (hooks.json). Then build + render.
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

CUT = config.NEXTWORK / "skills" / "cut" / "scripts"
TOOLS = config.TOOLS
MAX_GAP_S = 0.12
HEAD_MAX_S = 0.5

# Portrait sources keep their size; landscape sources go to 9:16 with a crop on the person.
PORTRAIT_FORMATS = {(1080, 1920): "916", (1440, 2560): "916_1440", (1728, 3072): "916_3k",
                    (2160, 3840): "916_4k"}
LANDSCAPE_FORMATS = {(1920, 1080): "169", (3840, 2160): "169_4k"}


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def env():
    """NextWork scripts read their engine settings from the environment."""
    e = dict(os.environ)
    py = config.python()
    e.setdefault("AI_EDITOR_MLX_PYTHON", py)
    if config.terms_file().exists():
        e.setdefault("AI_EDITOR_TERMS", str(config.terms_file()))
    lang = (config.creator().get("language") or "").strip()
    if lang and lang != "auto":
        e.setdefault("AI_EDITOR_LANG", lang)
    return e


def run(cmd, check=True, **kw):
    print("→ " + " ".join(str(c) for c in cmd[:4]) + (" …" if len(cmd) > 4 else ""))
    r = subprocess.run([str(c) for c in cmd], env=env(), **kw)
    if check and r.returncode:
        fail(f"{Path(str(cmd[1])).name} stopped (exit {r.returncode})")
    return r


def edit_dir(slug, must_exist=True) -> Path:
    if slug != slug.lower() or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", slug):
        fail(f"slug '{slug}': lowercase letters, digits, '-', '_' and '.' only (macOS is case-insensitive)")
    d = config.work_dir(slug)
    if must_exist and not d.exists():
        fail(f"no edit folder {d}: run `cutflow.py transcribe <source> {slug}` first")
    return d


def meta(d: Path) -> dict:
    f = d / "meta.json"
    return json.loads(f.read_text()) if f.exists() else {}


def probe(source):
    """(width, height, fps) as displayed, rotation applied."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate,avg_frame_rate:stream_side_data=rotation:stream_tags=rotate",
         "-of", "json", str(source)], capture_output=True, text=True, check=True).stdout
    st = json.loads(out)["streams"][0]
    w, h = int(st["width"]), int(st["height"])
    rot = int(st.get("tags", {}).get("rotate", 0) or 0)
    for sd in st.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", rot) or rot)
    if abs(rot) % 180 == 90:
        w, h = h, w
    def rate(text):
        num, _, den = (text or "0/0").partition("/")
        return float(num) / float(den) if den and float(den) else 0.0
    # variable-frame-rate phone video reports its peak as r_frame_rate; the average is the real rate
    return w, h, rate(st.get("avg_frame_rate")) or rate(st.get("r_frame_rate")) or 30.0


def pick_format(w, h, target):
    if target == "169":
        return LANDSCAPE_FORMATS.get((w, h), "169"), "pad" if w < h else "cover"
    if h > w:
        return PORTRAIT_FORMATS.get((w, h), "916"), "cover"
    return "916", "cover"


# ---------------------------------------------------------------------------------------------
def cmd_transcribe(a):
    src = Path(a.source).expanduser().resolve()
    if not src.exists():
        fail(f"no such file: {src}")
    d = edit_dir(a.slug, must_exist=False)
    d.mkdir(parents=True, exist_ok=True)
    w, h, fps = probe(src)
    (d / "meta.json").write_text(json.dumps({"source": str(src), "width": w, "height": h, "fps": fps}, indent=1))
    cmd = [config.python(), CUT / "transcribe.py", src, d / "words.raw.json", "--engine", a.engine]
    if a.lang:
        cmd += ["--lang", a.lang]
    run(cmd)
    r = run([config.python(), CUT / "retakes.py", "propose", d] + (["--force"] if a.force else []), check=False)
    if r.returncode not in (0, 4):
        fail("retakes.py propose failed")
    print(f"\n✓ {d}")
    for f in ("transcript.txt", "candidates.md", "review.md", "hooks.json"):
        if (d / f).exists():
            print(f"  {d / f}")
    print("  next: write spans.json (quoted cuts), then `cutflow.py build " + a.slug + "`")


def cmd_build(a):
    d = edit_dir(a.slug)
    src = meta(d).get("source") or fail("meta.json has no source: run transcribe again")
    cmd = [config.python(), CUT / "build_timeline.py", src, d, "--edges", "waveform"]
    if a.dry_run:
        cmd.append("--dry-run")
    run(cmd)
    if not a.dry_run:
        print(f"\n  read {d / 'paper-edit.md'} straight through before rendering")


def to_plan(d: Path, a) -> Path:
    m = meta(d)
    decisions = json.loads((d / "decisions.json").read_text())
    report = json.loads((d / "report.json").read_text())
    target = a.target or (config.creator().get("format") or "916")
    fmt, fit = pick_format(m["width"], m["height"], target)
    plan = {
        "name": "cut",
        "source": report["source"],
        "format": a.format if a.format != "auto" else fmt,
        "fps": int(round(m["fps"])),
        "speed": 1.0,
        "fit": a.fit or fit,
        "crop_x": a.crop_x,
        "segments": [[s["start"], s["end"]] for s in decisions],
    }
    if m["width"] > m["height"] and plan["format"].startswith("916") and a.crop_x is None:
        print("⚠ landscape source into 9:16: look at a frame and pass --crop-x on the person "
              "(centre crop is used until then)")
    p = d / "plan.json"
    p.write_text(json.dumps(plan, indent=1))
    return p


def cmd_render(a):
    d = edit_dir(a.slug)
    if not (d / "decisions.json").exists():
        fail("no decisions.json: run `cutflow.py build` first")
    plan = to_plan(d, a)
    py = config.python()
    run([py, TOOLS / "cut.py", plan, "--out-dir", d])
    verified = run([py, CUT / "verify_cut.py", d], check=False).returncode == 0
    if not verified:
        print("✗ words  verify_cut found MISSING or SURVIVED words (lines above)")
    ok = checks(d) and verified
    run([py, CUT / "preview_cut.py", d] + (["--no-open"] if a.no_open else []), check=False)
    print(f"\n{'✓' if ok else '✗'} {d / 'cut.mp4'}")
    if not ok:
        sys.exit(1)


# ---------------------------------------------------------------------------------------------
def duration(path, stream):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries",
                          "stream=duration", "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True).stdout.strip().splitlines()
    return float(out[0]) if out and out[0] not in ("", "N/A") else None


def checks(d: Path) -> bool:
    cut = d / "cut.mp4"
    if not cut.exists():
        fail(f"no {cut}")
    ok = True

    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(cut), "-af",
                          f"silencedetect=noise=-40dB:d={MAX_GAP_S}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    gaps = [(s, x) for s, x in re.findall(r"silence_start: (-?[\d.]+).*?silence_duration: ([\d.]+)", log, re.S)
            if float(x) > MAX_GAP_S + 0.005]       # the rule is "over 0.12 s"; ffmpeg reports "at least"
    if gaps:
        ok = False
        print(f"✗ gaps   {len(gaps)} silence(s) over {MAX_GAP_S}s at -40 dB: "
              + ", ".join(f"{float(s):.2f}s ({float(x):.2f}s)" for s, x in gaps[:6]))
    else:
        print(f"✓ gaps   no silence over {MAX_GAP_S}s")

    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(cut), "-vn", "-f", "s16le", "-ac", "2",
                          "-ar", "48000", "-"], capture_output=True).stdout
    a_len, v_len = len(pcm) / 4 / 48000, duration(cut, "v:0")
    if v_len is None or abs(a_len - v_len) > 0.05:
        ok = False
        print(f"✗ sync   decoded audio {a_len:.3f}s vs video {v_len}s")
    else:
        print(f"✓ sync   audio {a_len:.3f}s = video {v_len:.3f}s")

    words = json.loads((d / "cut.transcript.json").read_text()) if (d / "cut.transcript.json").exists() else []
    first = next((w["start"] for w in words if w.get("type", "word") == "word"), None)
    if first is None or first >= HEAD_MAX_S:
        ok = False
        print(f"✗ head   first word at {first}s (must be under {HEAD_MAX_S}s)")
    else:
        print(f"✓ head   first word at {first:.2f}s")

    plan_final = d / "plan.json"
    if plan_final.exists():
        sys.path.insert(0, str(TOOLS))
        import sync_check  # noqa: E402
        lines = []
        import contextlib, io  # noqa: E401,E402
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            synced = sync_check.check(plan_final, cut)
        lines = buf.getvalue().splitlines()
        if synced:
            print(f"✓ lipsync every segment's sound matches the source (lag 0)")
        else:
            ok = False
            print("✗ lipsync " + "; ".join(l.strip("✗ ") for l in lines if l.startswith("✗")))

    vol = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(cut), "-af", "volumedetect", "-vn", "-f",
                          "null", "-"], capture_output=True, text=True).stderr
    peak = re.search(r"max_volume: (-?[\d.inf]+) dB", vol)
    if not peak or "inf" in peak.group(1):
        ok = False
        print("✗ level  no audio")
    else:
        print(f"✓ level  peak {peak.group(1)} dB")
    return ok


def cmd_checks(a):
    sys.exit(0 if checks(edit_dir(a.slug)) else 1)


def cmd_hook(a):
    d = edit_dir(a.slug)
    run([config.python(), CUT / "retakes.py", "hook", d, str(a.n)])
    variant = d.parent / f"{d.name}-hook{a.n}"
    shutil.copy(d / "meta.json", variant / "meta.json")
    for f in ("words.raw.json", "transcript.txt"):
        if (d / f).exists() and not (variant / f).exists():
            shutil.copy(d / f, variant / f)
    print(f"✓ {variant}: now `cutflow.py build {variant.name}` and `cutflow.py render {variant.name}`")


def main():
    config.use_venv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("transcribe")
    t.add_argument("source")
    t.add_argument("slug")
    t.add_argument("--lang", default=None)
    t.add_argument("--engine", default="mlx")
    t.add_argument("--force", action="store_true", help="replace an existing spans.json proposal")
    b = sub.add_parser("build")
    b.add_argument("slug")
    b.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("render")
    r.add_argument("slug")
    r.add_argument("--target", choices=("916", "169"), default=None, help="output aspect (creator.yaml format)")
    r.add_argument("--format", default="auto")
    r.add_argument("--fit", choices=("cover", "pad"), default=None)
    r.add_argument("--crop-x", type=int, default=None)
    r.add_argument("--no-open", action="store_true")
    c = sub.add_parser("checks")
    c.add_argument("slug")
    h = sub.add_parser("hook")
    h.add_argument("slug")
    h.add_argument("n", type=int)
    a = ap.parse_args()
    {"transcribe": cmd_transcribe, "build": cmd_build, "render": cmd_render, "checks": cmd_checks,
     "hook": cmd_hook}[a.cmd](a)


if __name__ == "__main__":
    main()
