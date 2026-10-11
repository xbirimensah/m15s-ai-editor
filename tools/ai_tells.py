#!/usr/bin/env python3
"""Check a spec for AI tells before rendering (list + reasons: references/ai-tells.md).

Usage:
    python3 tools/ai_tells.py <workspace>/videos/<slug>.json [--creator creator.yaml]

Checks text, icons, theme colours and the beat mix of the spec. Whatever creator.yaml lists under
`ai_tells_allowed` (brand colours) is skipped; --creator defaults to creator.yaml in the config home.
Exit 1 on at least one BAN, else 0. A WARN needs a reason in the report.

Adapted from NextWork ai-editor (style-edit/scripts/ai_tells.py) to the engine's
spec (src/spec.ts). Only what code can see reliably; glass, glow and
paper backgrounds are checked by looking at the stills.
"""
import argparse
import colorsys
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

ICON_BAN = {"sparkle", "star"}
ICON_WARN = {"bolt", "brain"}
# English and German slop words.
SLOP_COPY = re.compile(
    r"\b(unlock|supercharge|game[- ]?changer|next[- ]level|level up|seamless|elevate|revolutioni[sz]e|"
    r"effortless|empower|leverage|unleash|skyrocket|cutting[- ]edge|bahnbrechend|revolutionär|mühelos|"
    r"entfessel\w*|nächste[sn]? level|im handumdrehen)\b", re.I)
MULTIPLIER = re.compile(
    r"\d+(?:[.,]\d+)?\s?x\b.{0,40}\b(schneller|günstiger|billiger|besser|effizienter|als|faster|cheaper|better|than)\b"
    r"|\b(schneller|günstiger|besser|faster|cheaper|better)\b.{0,20}\d+(?:[.,]\d+)?\s?x\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\U0000FE0F]")
# Fields that control layout, not text in the picture.
NOT_TEXT = {"type", "position", "side", "align", "kind", "icon", "icons", "src", "video", "file", "fit", "layout"}
TEXT_ONLY = {"takeover"}


def hsv(hex_color):
    """'#RRGGBB' -> (hue 0-360, saturation 0-1, value 0-1), else None."""
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(hex_color).strip())
    if not m:
        return None
    r, g, b = (int(m.group(1)[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v


def texts(node, key=None):
    """All strings that end up in the picture (recursive, layout fields excluded)."""
    if key in NOT_TEXT:
        return []
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [t for x in node for t in texts(x)]
    if isinstance(node, dict):
        return [t for k, v in node.items() for t in texts(v, k)]
    return []


def icons(node):
    """All icon names in a beat (fields icon and icons, recursive)."""
    if isinstance(node, list):
        return [i for x in node for i in icons(x)]
    if not isinstance(node, dict):
        return []
    own = [node["icon"]] if isinstance(node.get("icon"), str) else []
    own += [i for i in node.get("icons", []) if isinstance(i, str)]
    return own + [i for k, v in node.items() if k not in ("icon", "icons") for i in icons(v)]


def check_theme(theme):
    out = []
    bg = hsv(theme.get("bg", ""))
    accents = {k: hsv(v) for k, v in theme.items() if k in ("accent", "accent2", "capActive") and hsv(v)}
    for k, (h, s, v) in accents.items():
        if 225 <= h <= 295 and s >= 0.40:
            out.append(("BAN", "purple-blue", f"theme.{k} {theme[k]}"))
        if bg and bg[2] < 0.16 and s >= 0.60 and v >= 0.85:
            out.append(("BAN", "neon-on-black", f"theme.{k} {theme[k]} on bg {theme['bg']}"))
    cap = accents.get("capActive")
    if cap and 40 <= cap[0] <= 65 and cap[1] >= 0.6:
        out.append(("WARN", "preset-captions", f"yellow active word {theme['capActive']}"))
    return out


def check_beat(i, beat):
    out, where = [], f"beat {i} ({beat.get('type', '?')})"
    words = texts(beat)
    joined = " ".join(words)
    for icon in icons(beat):
        if icon in ICON_BAN:
            out.append(("BAN", "slop-icon", f"{where}: icon {icon}"))
        elif icon in ICON_WARN:
            out.append(("WARN", "slop-icon", f"{where}: icon {icon}"))
    if icons(beat) and not any(w.strip() for w in words):
        out.append(("BAN", "icon-only", f"{where}: icons only, no text/image"))
    if EMOJI.search(joined):
        out.append(("BAN", "emoji", f"{where}: {EMOJI.findall(joined)}"))
    for m in SLOP_COPY.finditer(joined):
        out.append(("BAN", "slop-copy", f"{where}: '{m.group(0)}'"))
    if MULTIPLIER.search(joined):
        out.append(("BAN", "multiplier-claim", f"{where}: '{MULTIPLIER.search(joined).group(0)}'"))
    if "gradient(" in json.dumps(beat):
        out.append(("WARN", "gradient", where))
    return out


def check(spec, allowed):
    found = check_theme(spec.get("theme", {}))
    beats = spec.get("beats", [])
    for i, beat in enumerate(beats):
        found += check_beat(i, beat)
    n_text = sum(1 for b in beats if b.get("type") in TEXT_ONLY)
    if n_text > 1:
        found.append(("WARN", "text-heavy", f"{n_text}x takeover (max 1 per video)"))
    caption_words = " ".join(w.get("w", "") for w in spec.get("words", []))
    if EMOJI.search(caption_words):
        found.append(("BAN", "emoji", "in the caption words"))
    return [f for f in found if f[1] not in allowed]


def main():
    config.use_venv()
    ap = argparse.ArgumentParser(description="Check a spec for AI tells")
    ap.add_argument("spec")
    ap.add_argument("--creator", default=str(config.creator_path()),
                    help="creator.yaml with ai_tells_allowed (default: the one in the config home)")
    a = ap.parse_args()
    if not os.path.exists(a.spec):
        sys.exit(f"✗ Spec not found: {a.spec}")
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    allowed = set()
    if os.path.exists(a.creator):
        with open(a.creator, encoding="utf-8") as f:
            creator = yaml.safe_load(f) or {}
        # ai_tells_erlaubt: legacy key name, read when ai_tells_allowed is absent
        key = "ai_tells_allowed" if "ai_tells_allowed" in creator else "ai_tells_erlaubt"
        allowed = set(creator.get(key) or [])
    found = check(spec, allowed)
    for level, tell, detail in found:
        print(f"{level:4} {tell:18} {detail}")
    bans = sum(1 for f in found if f[0] == "BAN")
    if allowed:
        print(f"(allowed by creator.yaml: {', '.join(sorted(allowed))})")
    print(f"{'✗' if bans else '✓'} {bans} BAN, {len(found) - bans} WARN")
    sys.exit(1 if bans else 0)


if __name__ == "__main__":
    main()
