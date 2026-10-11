#!/usr/bin/env python3
"""One line per piece the editor needs: ok, or FIX with what to do.

    python3 setup/doctor.py          exit 0 when everything the core flow needs is ready
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import config  # noqa: E402

REQUIRED_CREATOR = ("language", "format", "brand", "captions", "hookbar", "workspace")


def version(cmd) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[0]
    except (OSError, IndexError, subprocess.TimeoutExpired):
        return ""


def main():
    config.use_venv()
    problems = 0

    def line(good: bool, name: str, detail: str, fix: str = ""):
        nonlocal problems
        if not good:
            problems += 1
        print(f"{'ok ' if good else 'FIX'}  {name:<14} {detail}" + ("" if good else f"  -> {fix}"))

    line(bool(shutil.which("ffmpeg")), "ffmpeg", version(["ffmpeg", "-version"])[:40], "brew install ffmpeg")
    node = version(["node", "-v"])
    major = int(node.lstrip("v").split(".")[0]) if node else 0
    line(major >= 22, "node", node or "missing", "brew install node (22 or newer, HyperFrames needs it)")

    py = config.python()
    venv_ok = subprocess.run([py, "-c", "import mlx_whisper, numpy, yaml, cv2, PIL"], capture_output=True).returncode == 0
    line(venv_ok, "python venv", py, "bash setup/install.sh")

    cp = config.creator_path()
    c = config.creator() if cp.exists() and venv_ok else {}
    missing = [k for k in REQUIRED_CREATOR if k not in c]
    line(cp.exists() and not missing, "creator.yaml", str(cp) if not missing else f"missing: {', '.join(missing)}",
         "fill it in (the skill's intake asks for it)")

    ws = config.workspace() if venv_ok else Path("?")
    mods = ws / "node_modules"
    engine_ok = all((mods / p).exists() for p in ("remotion", "@remotion/renderer", "@remotion/bundler", "gsap",
                                                     "hyperframes"))
    line(engine_ok, "engine", str(ws), "bash setup/install.sh (npm install in the workspace)")
    same_src = engine_ok and subprocess.run(["diff", "-rq", str(config.SKILL / "engine" / "src"), str(ws / "src")],
                                            capture_output=True).returncode == 0
    line(same_src, "engine code", "matches the skill" if same_src else "workspace src differs from the skill",
         "bash setup/install.sh (copies the skill's engine code)")

    hf_bin = ws / "node_modules" / ".bin" / "hyperframes"
    hf = version([str(hf_bin), "--version"]) if hf_bin.exists() else ""
    line(bool(hf), "hyperframes", hf or "not installed in the workspace", "bash setup/install.sh (npm install)")

    taste = config.home() / "taste.json"
    print(f"{'ok ' if taste.exists() else '-- '}  {'taste':<14} {taste if taste.exists() else 'no rules yet (they come with corrections)'}")
    extras = Path.home() / ".ai-video-editor" / "venv"
    print(f"{'ok ' if extras.exists() else '-- '}  {'extras':<14} "
          + ("NextWork tools installed" if extras.exists() else "not installed (bash setup/install.sh --extras)"))

    if (config.SKILL / ".git").exists():
        r = subprocess.run([py, str(config.TOOLS / "privacy_check.py")], capture_output=True, text=True)
        line(r.returncode == 0, "privacy", (r.stdout.strip().splitlines() or [""])[-1][:70],
             "python3 tools/privacy_check.py lists every hit")

    print("Ready." if not problems else f"{problems} to fix.")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
