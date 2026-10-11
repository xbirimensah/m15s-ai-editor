# Third-party notices

| Part | Where | Licence |
|---|---|---|
| NextWork AI video editor (ai-editor, creator-teardown) | `nextwork/` | MIT, Copyright (c) 2026 NextWork: `nextwork/LICENSE`, `nextwork/NOTICE`, its own notices in `nextwork/THIRD_PARTY_NOTICES.md` |
| HyperFrames skills (HeyGen), release in `hyperframes/plugin.json` | `hyperframes/skills/` | Apache-2.0: `hyperframes/LICENSE`; provenance and changes (test files left out) in `hyperframes/VENDORED.md` |
| Inter, JetBrains Mono, Newsreader fonts | `hyperframes/template/assets/fonts/` | SIL Open Font License 1.1: `LICENSE-FONTS.txt` there |

Installed by `setup/install.sh`, not shipped in this repo:

| Package | Licence |
|---|---|
| Remotion (`remotion`, `@remotion/*`) | Remotion License: free for individuals and small companies; larger companies need a company licence (remotion.dev/license) |
| HyperFrames CLI (`hyperframes`, pinned to the bundled release) | Apache-2.0 |
| GSAP | GSAP Standard License (free, including commercial use) |
| mlx-whisper, Whisper large-v3-turbo weights | MIT |
| OpenCV, NumPy, Pillow, PyYAML | Apache 2.0 / BSD / HPND / MIT |

Local patches to the vendored NextWork code (marked "local patch" in the source):
- `skills/cut/scripts/transcribe.py`: mlx-whisper and Groq engines, a terms file from `AI_EDITOR_TERMS`.
- `skills/cut/scripts/build_timeline.py`: `--spans-only` (pauses left to the waveform cutter), taste
  store optional.
- `skills/style-edit/scripts/edit.py`, `remotion/render.mjs`: a 4K cut renders at 4K on a laptop.
- creator-teardown transcribes in the spoken language; the cut reads the clip-edge pad from the taste.
