#!/bin/bash
# QC check: transcribes the first 4 seconds of a cut and shows the
# word timings. Rule: the first word must land BEFORE 0.5 s, otherwise
# there is dead air or a dead frame at the start.
#
# Usage: tools/verify_head.sh <cut.mp4>
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: verify_head.sh <cut.mp4>" >&2
  exit 1
fi

CUT="$1"
if [ ! -f "$CUT" ]; then
  echo "✗ File not found: $CUT" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${M15S_PY:-$(python3 "$SCRIPT_DIR/config.py" get python 2>/dev/null || echo python3)}"
TMPDIR_HEAD="$(mktemp -d /tmp/verify_head.XXXXXX)"
trap 'rm -rf "$TMPDIR_HEAD"' EXIT

HEAD_CLIP="$TMPDIR_HEAD/head.wav"

echo "→ Extracting the first 4 seconds …"
ffmpeg -y -v error -i "$CUT" -t 4 -vn -ac 1 -ar 16000 -c:a pcm_s16le "$HEAD_CLIP"

echo "→ Transcribing the head (mlx-whisper) …"
"$PY" "$SCRIPT_DIR/transcribe.py" "$HEAD_CLIP" --out "$TMPDIR_HEAD/head.words.json" >/dev/null

python3 - "$TMPDIR_HEAD/head.words.json" <<'PY'
import json, sys

words = json.load(open(sys.argv[1]))
if not words:
    print("✗ NO words detected in the first 4 seconds: check the cut!")
    sys.exit(1)

print("\nWord timings (first 4 s):")
for w in words[:12]:
    print(f"  {w['s']:6.2f}s – {w['e']:6.2f}s  {w['w']}")

first = words[0]["s"]
if first < 0.5:
    print(f"\n✓ First word at {first:.2f}s: the head is clean.")
else:
    print(f"\n✗ First word only at {first:.2f}s (target: < 0.5 s): dead air at the start, check the segment start!")
    sys.exit(1)
PY
