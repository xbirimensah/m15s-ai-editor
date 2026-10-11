#!/usr/bin/env python3
"""Hand a version over: one folder per video, every version numbered with a plain-language name.

    python3 tools/deliver.py <slug> <file> "<what this version is>" [--nn NN] [--no-open]

Folder: <delivery_dir>/<NN>_<slug>/ when creator.yaml sets delivery_dir (NN = the script number,
remembered in work/<slug>/meta.json once given), else <workspace>/work/<slug>/VIDEOS/.
work/<slug>/VIDEOS then links to it, so both places show the same files.
File:   <n>-<label>.mp4, n counting up (1-cut-v1.mp4, 2-captions-only.mp4, 3-final-APPROVED.mp4).
Opens the folder in Finder and the file in QuickTime unless --no-open.
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


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def label_slug(text: str) -> str:
    keep = re.sub(r"[^A-Za-z0-9]+", "-", text.strip()).strip("-")
    approved = keep.upper().endswith("APPROVED")
    keep = keep.lower()
    return (keep[: -len("approved")] + "APPROVED") if approved else keep


def target_folder(slug: str, d: Path, nn: str | None) -> Path:
    base = config.delivery_dir()
    if not base:
        return d / "VIDEOS"
    meta_file = d / "meta.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    if nn is not None and not str(nn).isdigit():
        fail(f"--nn must be a number (the script number), got {nn!r}")
    nn = nn or meta.get("nn")
    if nn:
        meta["nn"] = nn
        meta_file.write_text(json.dumps(meta, indent=1))
    return base / (f"{int(nn):02d}_{slug}" if nn else slug)


def main():
    config.use_venv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("file")
    ap.add_argument("label")
    ap.add_argument("--nn", default=None, help="script number, e.g. 31")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()

    src = Path(a.file).expanduser()
    if not src.exists():
        fail(f"no such file: {src}")
    d = config.work_dir(a.slug)
    d.mkdir(parents=True, exist_ok=True)
    folder = target_folder(a.slug, d, a.nn)
    folder.mkdir(parents=True, exist_ok=True)

    link = d / "VIDEOS"
    if folder != link:
        if link.is_symlink() and link.resolve() != folder.resolve():
            link.unlink()
        if not link.exists():
            link.symlink_to(folder, target_is_directory=True)
        elif not link.is_symlink():
            print(f"⚠ {link} is a real folder from before delivery_dir was set; new versions go to {folder}")

    n = 1 + max([int(m.group(1)) for f in folder.iterdir() if (m := re.match(r"(\d+)-", f.name))], default=0)
    dst = folder / f"{n}-{label_slug(a.label)}{src.suffix.lower()}"
    shutil.copy2(src, dst)
    print(f"✓ {dst}")
    if not a.no_open and sys.platform == "darwin":
        subprocess.run(["open", str(folder)])
        subprocess.run(["open", "-a", "QuickTime Player", str(dst)])


if __name__ == "__main__":
    main()
