# m15s AI Editor

An Agent Skill that edits talking-head videos end to end: raw take in, finished Reel, Short or VSL
out. It works with any AI coding agent that can run shell commands: Claude Code, Codex, OpenCode,
Kimi Code, Gemini CLI, Cursor and others. It combines two editing systems:

- **The Creator Engine**: a waveform cutter that joins takes without gaps or audio drift, and a
  Remotion overlay engine with editorial beats (hook bar, one-line word captions, kickers, panels,
  diagrams, stats, takeovers, end card).
- **The NextWork AI video editor** (MIT, vendored in `nextwork/`): cutting by quoting the transcript, a
  paper edit you read before rendering, a re-transcribe check that catches eaten words and surviving
  stumbles, an approval page, hook variants, clips from long videos, creator teardowns, creator-style
  edits with live captures, product films and NLE export.

Plus **HyperFrames** (HeyGen, Apache-2.0), bundled complete and pinned to one release: custom b-roll
beats that drop into the Remotion edit, and every HyperFrames workflow (designed captions, overlay cards,
faceless explainers, motion graphics, launch promos, music videos, slideshows, PR explainers, Figma).

You approve three things: the cut plan, the cut, the stills sheet. Every correction you give becomes
a rule, so you never say it twice.

## Install (Mac with Apple Silicon)

```bash
git clone <this repo> ~/Dev/m15s-ai-editor
bash ~/Dev/m15s-ai-editor/setup/install.sh            # core
bash ~/Dev/m15s-ai-editor/setup/install.sh --extras   # + NextWork's clips, teardown, product films
```

The installer checks Homebrew, ffmpeg, Node 22+ and Python, creates a venv (mlx-whisper, OpenCV,
Pillow, PyYAML), sets up the workspace with the Remotion engine, pre-loads the Whisper model, checks
HyperFrames, and links the skill into the agents' skill folders. Run it again any time. Restart your
agent, then say: *"edit this video: ~/Movies/take.mov"*.

### Your agent

| Agent | Where it finds the skill | Notes |
|---|---|---|
| Claude Code | `~/.claude/skills/m15s-ai-editor` (linked by the installer) | `/m15s-ai-editor` or just ask |
| Codex | `~/.agents/skills/m15s-ai-editor` (linked) | `$m15s-ai-editor` or just ask |
| OpenCode | `~/.agents/skills` and `~/.claude/skills` (both linked) | loads it through its skill tool |
| Kimi Code | `~/.agents/skills` (linked) | `/skill:m15s-ai-editor` or just ask |
| Any other agent with skills (Gemini CLI, Cursor, ...) | `bash setup/install.sh --link-to <its skills folder>` | |
| An agent without skill support | point it at `SKILL.md`: *"read <repo>/SKILL.md and edit this video"* | |

Agents with a structured question tool or sub-agents use them; everywhere else the skill asks a
numbered question in chat and does the steps itself.

`python3 setup/doctor.py` prints one line per piece: ok, or FIX with what to do.

## Your data stays yours

The repo holds no personal data. Everything about you lives in `~/.m15s-ai-editor/`
(`M15S_EDITOR_HOME` moves it):

| File | What |
|---|---|
| `creator.yaml` | brand colours and fonts, CTA, no-gos, pronunciation fixes, captions, hook bar, folders |
| `taste.json` / `TASTE.md` | every correction as a counted rule |
| `terms.txt` | words Whisper should spell your way |
| `broll-style.md` | the look of your b-roll |
| `private-terms.txt` | words that must never reach a repo |
| `assets/` | your own images and proof |

A pre-commit hook (`tools/privacy_check.py`) blocks any commit containing your private terms, your
creator.yaml values, e-mail addresses, home or volume paths or API keys.

## How it works

```
raw take ─ transcribe (mlx-whisper) ─ quoted cuts (spans.json) ─ paper edit ─ [approve plan]
        ─ tighten + two-threshold edges ─ frame-accurate cut ─ verify ─ cut page ─ [approve cut]
        ─ captions + head detection ─ beats (Remotion) + b-roll (HyperFrames) ─ checks
        ─ stills sheet + critic ─ [approve stills] ─ render ─ 4:5 crop check ─ numbered delivery
```

Details: `SKILL.md` and `references/` (`cut.md`, `motion.md`, `broll.md`, `hyperframes.md`, `extras.md`,
`taste.md`, `ai-tells.md`). Contributing: `AGENTS.md`.

## Requirements

macOS on Apple Silicon, Homebrew, an AI coding agent. No API keys needed for the core flow. Optional:
a Groq key for cloud transcription, the NextWork extras' own optional keys (TypeSafe, Gemini,
ElevenLabs), Modal, GitHub Actions or AWS for cloud renders.

## Licences

This repo: MIT (`LICENSE`). Third-party parts: `THIRD_PARTY_NOTICES.md` (NextWork ai-video-editor
MIT, HyperFrames skills Apache-2.0, fonts under the SIL Open Font License). Remotion is installed from npm under its own licence;
companies above its free-use threshold need a Remotion company licence (remotion.dev/license).
