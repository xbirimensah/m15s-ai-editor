#!/bin/bash
# =============================================================================
# m15s-ai-editor setup. Idempotent: run it again any time, it only adds what is missing.
#
#   bash setup/install.sh            core: cut, motion graphics, HyperFrames b-roll
#   bash setup/install.sh --extras   also NextWork's own tools (clips, creator teardown, product
#                                    videos, creator-style edits, cloud renders): ~/.ai-video-editor
#   bash setup/install.sh --link-to DIR   also link the skill into another agent's skills folder
#   bash setup/install.sh --no-link  do not link the skill anywhere
#
# The skill is linked into ~/.agents/skills (the shared Agent Skills folder: Codex, OpenCode,
# Kimi Code and others) and ~/.claude/skills (Claude Code; OpenCode reads it too).
#
# Needs a Mac with Apple Silicon (mlx-whisper runs on the Apple GPU) and Homebrew.
# Creates:
#   ~/.m15s-ai-editor/   your config home (creator.yaml, taste, terms, b-roll style, venv)
#   the workspace        Remotion engine + node_modules, work/, public/, out/ (creator.yaml workspace:)
# =============================================================================
set -uo pipefail

SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
HOME_DIR="${M15S_EDITOR_HOME:-$HOME/.m15s-ai-editor}"
EXTRAS=0
LINK=1
LINK_DIRS=("$HOME/.agents/skills" "$HOME/.claude/skills")
while [ $# -gt 0 ]; do
  case "$1" in
    --extras) EXTRAS=1 ;;
    --no-link) LINK=0 ;;
    --link-to) shift; [ $# -gt 0 ] || { echo "--link-to needs a folder"; exit 2; }; LINK_DIRS+=("$1") ;;
    *) echo "unknown option: $1"; exit 2 ;;
  esac
  shift
done

ok()   { printf "✓ %s\n" "$1"; }
warn() { printf "⚠ %s\n" "$1"; }
err()  { printf "✗ %s\n" "$1"; }

echo "m15s-ai-editor setup"
echo "  skill: $SKILL"
echo "  home:  $HOME_DIR"

# --- 0. Platform -------------------------------------------------------------
if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  err "needs a Mac with Apple Silicon (M1 or newer)"; exit 1
fi
ok "Apple Silicon"
if ! xcode-select -p >/dev/null 2>&1; then
  err "Xcode Command Line Tools missing: run 'xcode-select --install', then this again"; exit 1
fi
if ! command -v brew >/dev/null 2>&1; then
  err "Homebrew missing. Install it yourself from https://brew.sh (not done automatically), then run this again"
  exit 1
fi
ok "Homebrew"

# --- 1. ffmpeg, Node 22+, Python 3.10+ ---------------------------------------
command -v ffmpeg >/dev/null 2>&1 || brew install ffmpeg || { err "brew install ffmpeg failed"; exit 1; }
ok "ffmpeg"
NODE_MAJOR="$(node -v 2>/dev/null | sed 's/^v//' | cut -d. -f1)"
if [ -z "$NODE_MAJOR" ] || [ "$NODE_MAJOR" -lt 22 ]; then
  echo "→ Node 22+ is needed (HyperFrames): brew install node"
  brew install node || { err "brew install node failed"; exit 1; }
fi
ok "Node $(node -v)"
PY_OK="$(python3 -c 'import sys; print(int(sys.version_info >= (3, 10)))' 2>/dev/null || echo 0)"
if [ "$PY_OK" != "1" ]; then
  brew install python3 || { err "brew install python3 failed"; exit 1; }
fi
ok "Python $(python3 -V 2>&1 | awk '{print $2}')"

# --- 2. Config home -----------------------------------------------------------
mkdir -p "$HOME_DIR/assets"
copy_once() { [ -f "$HOME_DIR/$2" ] || { cp "$SKILL/config/$1" "$HOME_DIR/$2"; ok "created $HOME_DIR/$2 (fill it in, or let the skill ask)"; }; }
copy_once creator.template.yaml creator.yaml
copy_once terms.template.txt terms.txt
copy_once broll-style.template.md broll-style.md
copy_once private-terms.template.txt private-terms.txt
ok "config home $HOME_DIR"

# --- 3. Python venv -----------------------------------------------------------
VENV="$HOME_DIR/venv"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV" || { err "python3 -m venv failed"; exit 1; }
if "$VENV/bin/python" -c "import mlx_whisper, numpy, yaml, cv2, PIL" >/dev/null 2>&1; then
  ok "venv packages"
else
  echo "→ installing mlx-whisper, numpy, PyYAML, OpenCV, Pillow into $VENV …"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r "$SKILL/setup/requirements.txt" || { err "pip install failed"; exit 1; }
  ok "venv packages installed"
fi
PY="$VENV/bin/python"

# --- 4. Workspace: the Remotion engine ---------------------------------------
WS="$("$PY" "$SKILL/tools/config.py" get workspace)"
[ -n "$WS" ] && [ "$WS" != "/" ] || { err "no workspace path (creator.yaml workspace:)"; exit 1; }
MARK="$WS/.m15s-ai-editor-workspace"
if [ -d "$WS/src" ] && [ ! -f "$MARK" ] && ! diff -rq "$SKILL/engine/src" "$WS/src" >/dev/null 2>&1; then
  err "$WS/src exists and is not from this skill: pick another workspace in creator.yaml (nothing changed)"
  exit 1
fi
mkdir -p "$WS"/{videos,public/cut,public/broll,out,work}
touch "$MARK"
# Engine code always follows the skill (src/ and scripts/ are replaced); your videos/, public/,
# out/ and work/ are never touched.
rsync -a --delete "$SKILL/engine/src/" "$WS/src/"
rsync -a --delete "$SKILL/engine/scripts/" "$WS/scripts/"
cp "$SKILL/engine/package.json" "$SKILL/engine/tsconfig.json" "$SKILL/engine/remotion.config.ts" "$WS/"
[ -f "$WS/videos/example.json" ] || cp "$SKILL/engine/videos/example.json" "$WS/videos/"
if [ -d "$WS/node_modules/remotion" ] && [ -d "$WS/node_modules/gsap" ] && [ -d "$WS/node_modules/@remotion/renderer" ] \
   && [ -x "$WS/node_modules/.bin/hyperframes" ]; then
  ok "engine packages"
else
  echo "→ npm install in $WS (a few minutes the first time) …"
  (cd "$WS" && npm install --no-fund --no-audit) || { err "npm install failed in $WS"; exit 1; }
  ok "engine packages installed"
fi
ok "workspace $WS"

# --- 5. Whisper model (first run downloads it) -------------------------------
SILENT="$(mktemp -t m15s_silence).wav"
ffmpeg -y -v error -f lavfi -i anullsrc=r=16000:cl=mono -t 1 -c:a pcm_s16le "$SILENT"
if "$PY" "$SKILL/tools/transcribe.py" "$SILENT" --out "${SILENT%.wav}.json" >/dev/null 2>&1; then
  ok "Whisper model ready"
else
  warn "Whisper model check failed; the first real run downloads it (needs internet)"
fi
rm -f "$SILENT" "${SILENT%.wav}" "${SILENT%.wav}".json "${SILENT%.wav}".txt 2>/dev/null

# --- 6. HyperFrames -----------------------------------------------------------
HF="$WS/node_modules/.bin/hyperframes"
if [ -x "$HF" ] && HYPERFRAMES_NO_TELEMETRY=1 "$HF" --version >/dev/null 2>&1; then
  ok "HyperFrames $(HYPERFRAMES_NO_TELEMETRY=1 "$HF" --version 2>/dev/null | tail -1)"
else
  warn "HyperFrames not installed in the workspace (npm install there); b-roll beats need it"
fi

# --- 7. Repo guard + skill link ----------------------------------------------
if [ -d "$SKILL/.git" ]; then
  git -C "$SKILL" config core.hooksPath .githooks && ok "pre-commit privacy check active"
fi
if [ "$LINK" -eq 1 ]; then
  for DIR in "${LINK_DIRS[@]}"; do
    mkdir -p "$DIR"
    TARGET="$DIR/m15s-ai-editor"
    if [ -e "$TARGET" ] && [ "$(cd "$TARGET" && pwd -P)" = "$(cd "$SKILL" && pwd -P)" ]; then
      ok "skill in $DIR"
    elif [ -L "$TARGET" ] || [ ! -e "$TARGET" ]; then
      ln -sfn "$SKILL" "$TARGET" && ok "skill linked: $TARGET"
    else
      warn "$TARGET exists and is not this skill; left as it is"
    fi
  done
fi

# --- 8. NextWork extras (optional) -------------------------------------------
if [ "$EXTRAS" -eq 1 ]; then
  echo "→ NextWork tools (venv, transcription model, renderer) into ~/.ai-video-editor …"
  python3 "$SKILL/nextwork/ai-editor/skills/setup/scripts/setup.py" bootstrap || warn "NextWork bootstrap reported something to fix (see above)"
fi

echo ""
"$PY" "$SKILL/setup/doctor.py" || true
echo ""
ok "Setup done. Restart your agent (Claude Code, Codex, OpenCode, Kimi, ...), then say: \"edit this video: <path>\""
