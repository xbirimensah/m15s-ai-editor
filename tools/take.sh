#!/bin/bash
# Transcribe a single take on its own (Whisper merges retakes in the full
# transcript; heard on its own, the text is much more accurate).
# Usage: tools/take.sh <source.mp4> <label> <start_s> <end_s> [outdir] [lang]
# Output: absolute time, duration, words/s, longest pause, text. JSON in <outdir>/<label>.json
# lang: optional Whisper language code (e.g. de); without it the language is auto-detected.
set -euo pipefail
[ $# -lt 4 ] && { echo "Usage: take.sh <source> <label> <start> <end> [outdir] [lang]" >&2; exit 1; }
SRC=$1; L=$2; S=$3; E=$4; OUT=${5:-win}; LNG=${6:-}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${M15S_PY:-$(python3 "$SCRIPT_DIR/config.py" get python 2>/dev/null || echo python3)}"
mkdir -p "$OUT"
ffmpeg -y -v error -ss "$S" -to "$E" -i "$SRC" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$OUT/$L.wav"
"$PY" "$SCRIPT_DIR/transcribe.py" "$OUT/$L.wav" ${LNG:+--lang "$LNG"} --out "$OUT/$L.json" >/dev/null 2>&1
python3 - "$OUT/$L.json" "$L" "$S" <<'PY'
import json, sys
path, label, start = sys.argv[1], sys.argv[2], float(sys.argv[3])
w = json.load(open(path))
if not w:
    print(f"{label}: NO WORDS"); sys.exit()
gaps = [(w[i + 1]["s"] - w[i]["e"], w[i]["w"]) for i in range(len(w) - 1)] or [(0, "")]
gap, after = max(gaps)
dur = w[-1]["e"] - w[0]["s"]
print(f"{label:5} [{start + w[0]['s']:7.2f}-{start + w[-1]['e']:7.2f}] {dur:4.1f}s "
      f"{len(w) / dur:3.1f}w/s maxgap {gap:.2f}s after '{after}' | " + " ".join(x["w"] for x in w))
PY
