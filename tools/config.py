#!/usr/bin/env python3
"""Shared paths and the creator profile.

Personal data never lives in the skill folder (it is a public repo). It lives in the config home:

    $M15S_EDITOR_HOME            default ~/.m15s-ai-editor
      creator.yaml               brand, CTA, no-gos, pronunciation fixes, captions, folders
      taste.json + TASTE.md      every correction as a rule (tools/taste.py)
      terms.txt                  words Whisper should spell a certain way, one per line
      broll-style.md             the HyperFrames b-roll look
      private-terms.txt          words that must never reach the repo (tools/privacy_check.py)
      assets/                    the creator's own images and proof
      venv/                      the Python the tools run with (setup/install.sh)

The workspace (Remotion engine + node_modules, work/<slug>/ edit folders, public/, out/) is
`workspace:` in creator.yaml, else $M15S_WORKSPACE, else ~/M15sEditor.

    python3 tools/config.py show          # every resolved path
    python3 tools/config.py get workspace # one value, for shell scripts
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TOOLS = SKILL / "tools"
NEXTWORK = SKILL / "nextwork" / "ai-editor"
TEARDOWN = SKILL / "nextwork" / "creator-teardown"


def home() -> Path:
    return Path(os.environ.get("M15S_EDITOR_HOME", "~/.m15s-ai-editor")).expanduser()


def creator_path() -> Path:
    return home() / "creator.yaml"


def creator() -> dict:
    """creator.yaml as a dict; {} when it does not exist yet. Without PyYAML in this Python, the venv
    reads it (so hooks and doctor work from any python3)."""
    p = creator_path()
    if not p.exists():
        return {}
    try:
        import yaml
    except ImportError:
        venv = python()
        if venv == sys.executable:
            sys.exit("✗ PyYAML missing: run setup/install.sh")
        out = subprocess.run([venv, "-c", "import json, sys, yaml; print(json.dumps(yaml.safe_load("
                              "open(sys.argv[1], encoding='utf-8')) or {}, default=str))", str(p)],
                             capture_output=True, text=True)
        if out.returncode:
            sys.exit(f"✗ cannot read {p}: {out.stderr.strip()[-200:]}")
        return json.loads(out.stdout)
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _path(value) -> Path | None:
    return Path(str(value)).expanduser() if value else None


def workspace() -> Path:
    return (_path(os.environ.get("M15S_WORKSPACE")) or _path(creator().get("workspace"))
            or Path("~/M15sEditor").expanduser())


def engine() -> Path:
    """The Remotion project: the workspace root holds package.json, src/, public/, videos/, out/."""
    return workspace()


def work_dir(slug: str) -> Path:
    return workspace() / "work" / slug


def delivery_dir() -> Path | None:
    return _path(creator().get("delivery_dir"))


def assets_dir() -> Path:
    return _path(creator().get("assets_dir")) or home() / "assets"


def terms_file() -> Path:
    return home() / "terms.txt"


def broll_style() -> Path:
    return home() / "broll-style.md"


def python() -> str:
    """The venv Python (mlx-whisper, numpy, opencv, Pillow, PyYAML); the current one as a fallback."""
    venv = home() / "venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


def use_venv():
    """Re-run the calling tool with the venv Python when it runs under another one, so every tool can be
    started as plain `python3 <skill>/tools/<tool>.py` from any shell or agent."""
    venv = home() / "venv"
    exe = venv / "bin" / "python"
    if exe.exists() and Path(sys.prefix).resolve() != venv.resolve() and not os.environ.get("M15S_NO_VENV"):
        os.execv(str(exe), [str(exe), *sys.argv])


def pronunciation_fixes() -> dict:
    return dict(creator().get("pronunciation_fixes") or {})


RESOLVERS = {     # lazy: `get python` must work before creator.yaml can be read
    "skill": lambda: str(SKILL),
    "home": lambda: str(home()),
    "creator": lambda: str(creator_path()) + ("" if creator_path().exists() else "  (missing)"),
    "workspace": lambda: str(workspace()),
    "delivery_dir": lambda: str(delivery_dir() or "(none: work/<slug>/VIDEOS)"),
    "assets_dir": lambda: str(assets_dir()),
    "terms": lambda: str(terms_file()),
    "broll_style": lambda: str(broll_style()),
    "python": python,
    "nextwork": lambda: str(NEXTWORK),
}


def resolved() -> dict:
    return {k: f() for k, f in RESOLVERS.items()}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("show", "get"):
        sys.exit(__doc__)
    if sys.argv[1] == "show":
        print(json.dumps(resolved(), indent=1))
        return
    if len(sys.argv) < 3 or sys.argv[2] not in RESOLVERS:
        sys.exit(f"✗ unknown key. Known: {', '.join(RESOLVERS)}")
    print(RESOLVERS[sys.argv[2]]().split("  (")[0])


if __name__ == "__main__":
    main()
