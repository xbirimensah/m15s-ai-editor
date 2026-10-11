#!/usr/bin/env python3
"""Nothing personal reaches the repo. Run by the pre-commit hook (.githooks/pre-commit) and doctor.

    python3 tools/privacy_check.py [--staged] [--root DIR]

Blocks, in every tracked (or, with --staged, every staged) text file:
  - each line of <config home>/private-terms.txt (names, handles, clients, brand words), plus the
    creator's own values from creator.yaml (name, handle, website, CTA, brand colours): the list of
    what to hide lives outside the repo, so the list itself never leaks
  - e-mail addresses (example.com / noreply addresses excepted)
  - home and volume paths (/Users/<name>/, /home/<name>/, /Volumes/<disk>/)
  - API-key shapes (sk-, gsk_, ghp_, AIza, xox., AKIA)
  - with --staged (the pre-commit hook): a commit author whose name or e-mail is private, or whose
    e-mail is not a GitHub noreply address (commit metadata is published with the repo)
Exit 1 with file:line for every hit. A line that must stay can end in `privacy: allow`.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

SKIP_ANYWHERE = {".git", "node_modules", "__pycache__"}
SKIP_TOP = {"out", "work", "renders"}       # workspace-style folders, only at the repo root
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".wav", ".mp3", ".woff2", ".woff", ".ttf",
               ".onnx", ".lock", ".ico", ".pdf", ".zip"}
ALLOW_MARK = "privacy: allow"
PLACEHOLDER_USERS = {"me", "you", "user", "username", "name", "runner", "<name>", "<user>"}
PATTERNS = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b"),
    "home path": re.compile(r"/(?:Users|home)/([^/\s\"'`]+)/"),
    "volume path": re.compile(r"/Volumes/[^/\s\"'`<\[]+"),
    "api key": re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}"
                          r"|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})"),
}
SAFE_EMAIL = re.compile(r"@(example\.(com|org)|(site|domain|test)\.com|users\.noreply\.github\.com|anthropic\.com)$"
                        r"|^noreply@|^git@", re.I)


def private_terms() -> list[str]:
    terms = []
    f = config.home() / "private-terms.txt"
    if f.exists():
        terms += [t.strip() for t in f.read_text().splitlines() if t.strip() and not t.startswith("#")]
    c = config.creator()
    who = c.get("creator") or {}
    terms += [str(who.get(k) or "") for k in ("name", "instagram", "website")]
    terms += [str((c.get("cta") or {}).get("url") or "")]
    for color in ((c.get("brand") or {}).get("colors") or {}).values():
        terms.append(str(color))
    return sorted({t for t in terms if len(t) >= 3}, key=len, reverse=True)


def skipped(rel: Path) -> bool:
    return (rel.suffix.lower() in SKIP_SUFFIX or bool(SKIP_ANYWHERE.intersection(rel.parts))
            or (len(rel.parts) > 1 and rel.parts[0] in SKIP_TOP))


def files(root: Path, staged: bool) -> list[Path]:
    """Relative paths to scan. -z keeps non-ASCII names unquoted."""
    if (root / ".git").exists():
        cmd = ["git", "-C", str(root), "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"] if staged \
            else ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
        names = [n for n in subprocess.run(cmd, capture_output=True, text=True).stdout.split("\0") if n]
        rels = [Path(n) for n in names]
    else:
        rels = [p.relative_to(root) for p in root.rglob("*") if p.is_file()]
    return [r for r in rels if not skipped(r) and (staged or (root / r).is_file())]


def read(root: Path, rel: Path, staged: bool) -> str | None:
    """The text to scan: the staged blob in --staged mode (what the commit will hold), else the file."""
    try:
        if staged:
            out = subprocess.run(["git", "-C", str(root), "show", f":{rel.as_posix()}"], capture_output=True)
            return out.stdout.decode("utf-8") if out.returncode == 0 else None
        return (root / rel).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def scan(root: Path, staged: bool = False) -> list[str]:
    terms = private_terms()
    term_re = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(t) for t in terms) + r")(?!\w)", re.I) if terms else None
    hits = []
    for rel in files(root, staged):
        text = read(root, rel, staged)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if ALLOW_MARK in line:
                continue
            if term_re and (m := term_re.search(line)):
                hits.append(f"{rel}:{n}: private term {m.group(0)!r}")
            for kind, rx in PATTERNS.items():
                for m in rx.finditer(line):
                    if kind == "email" and SAFE_EMAIL.search(m.group(0)):
                        continue
                    if kind == "home path" and m.group(1).lower() in PLACEHOLDER_USERS:
                        continue
                    hits.append(f"{rel}:{n}: {kind} {m.group(0)!r}")
    return hits


def identity_hits(root: Path) -> list[str]:
    """The commit's author: a real name or private e-mail in the metadata is published with the repo."""
    out = subprocess.run(["git", "-C", str(root), "var", "GIT_AUTHOR_IDENT"], capture_output=True, text=True)
    if out.returncode:
        return []
    ident = out.stdout.strip()
    name, _, rest = ident.partition(" <")
    email = rest.split(">")[0]
    hits = []
    terms = [t.lower() for t in private_terms()]
    noreply = email.endswith("@users.noreply.github.com")   # GitHub links it to the pushing account anyway
    if any(t in name.lower() or (not noreply and t in email.lower()) for t in terms):
        hits.append(f"commit author '{name} <{email}>' contains a private term")
    if not noreply:
        hits.append(f"commit e-mail <{email}> is not a GitHub noreply address")
    if hits:
        hits.append("set a repo-only identity once: git config user.name \"<public name>\" && "
                    "git config user.email \"<id>+<user>@users.noreply.github.com\" "
                    "(GitHub: Settings > Emails shows your noreply address)")
    return hits


def main():
    config.use_venv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--root", default=str(config.SKILL))
    a = ap.parse_args()
    root = Path(a.root).resolve()
    hits = scan(root, a.staged)
    if a.staged:                       # commit time: the author goes public with the commit
        hits += identity_hits(root)
    for h in hits:
        print(f"✗ {h}")
    if hits:
        print(f"\n✗ {len(hits)} privacy hit(s): remove them, or end the line with '# {ALLOW_MARK}' if public")
        sys.exit(1)
    print(f"✓ privacy: nothing personal found ({len(private_terms())} private terms checked)")


if __name__ == "__main__":
    main()
