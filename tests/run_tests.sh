#!/bin/bash
# Everything that runs without footage: syntax, our unit tests, NextWork's cut tests, privacy.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$(python3 "$ROOT/tools/config.py" get python 2>/dev/null || echo python3)"
CUT="$ROOT/nextwork/ai-editor/skills/cut/scripts"
fail=0
step() { echo "── $1"; shift; "$@" || { echo "✗ $*"; fail=1; }; }

step "syntax (python)" "$PY" -m py_compile "$ROOT"/tools/*.py "$ROOT"/setup/doctor.py
step "syntax (bash)" bash -n "$ROOT"/tools/*.sh "$ROOT"/setup/install.sh "$ROOT"/.githooks/pre-commit
step "unit tests" "$PY" "$ROOT/tests/test_tools.py"
step "nextwork build_timeline" "$PY" "$CUT/test_build_timeline.py"
step "nextwork retakes" "$PY" "$CUT/test_retakes.py"
step "privacy" "$PY" "$ROOT/tools/privacy_check.py"
[ "$fail" -eq 0 ] && echo "✓ all green" || { echo "✗ something failed"; exit 1; }
