---
name: m15s-ai-editor
description: >
  Edits talking-head videos end to end for Reels, Shorts, TikTok and VSLs, with any AI coding agent.
  Cuts raw takes (retakes, false starts, director talk, pauses) by quoting the transcript and joins
  them seamlessly on the waveform; adds Remotion motion graphics (3-second hook bar, one-line
  captions, kickers, panels, diagrams, stats, end card) and HyperFrames b-roll; approval gates before
  every render. Also hook variants, clips from long videos or podcasts, creator teardowns,
  creator-style edits, product films and export to Final Cut, Premiere, Resolve or CapCut. Learns
  every correction as a rule. Use when the user drops raw footage or a video path, or says "edit this
  video", "cut this", "schneide das Video", "remove the pauses", "motion graphics", "captions",
  "b-roll", "hook bar", "make it look like @creator", "clips from this podcast", "export to Final
  Cut", or gives feedback on a cut or render.
---

# m15s AI Editor

One skill, three phases, three approval gates. NextWork decides WHAT to cut (quotes, paper edit,
re-transcribe diff); the waveform cutter decides WHERE the edges sit (seamless joins, no drift);
Remotion lays the editorial beats; HyperFrames makes custom b-roll.

`<skill>` = the folder of this file. Run every tool as `python3 <skill>/tools/<tool>.py ...` from any
shell: each one switches to the editor's own Python (the venv setup made) by itself. Personal data lives only in the config home
(`~/.m15s-ai-editor`: creator.yaml, taste, terms, b-roll style); this folder is a public repo and
must never receive any of it.

Works with any agent that can run shell commands and read files (Claude Code, Codex, OpenCode, Kimi,
Gemini, Cursor, ...). Two agent features are used when they exist, with a plain fallback:

- **Asking**: when this skill says *ask*, use your agent's structured question tool if it has one
  (2-4 options, the recommended one first, free text allowed); otherwise ask one short numbered
  question in chat. Then wait for the answer.
- **Delegating**: when it says *sub-agent*, start one if your agent can (a fast, cheap model is
  enough), with the prompt file named and the paths; otherwise do that step yourself, one at a time.

## 0. Ready? (every session, before the first tool)

```bash
python3 <skill>/setup/doctor.py          # FIX lines: bash <skill>/setup/install.sh, then again
python3 <skill>/tools/taste.py show --video <slug>
python3 <skill>/tools/config.py show     # workspace, delivery folder, config home
```

Follow every taste rule (they beat this file and creator.yaml defaults; if one conflicts with this
skill, say so once and follow the rule). creator.yaml missing or incomplete: the intake in
`references/motion.md` step 0 fills it (for a cut alone only `language` and `format` are needed).

## 1. Route

| The user wants | Read and follow |
|---|---|
| Raw footage edited ("edit this", a video path, "schneide das") | phase 1 `references/cut.md`, then offer phase 2 |
| Only the cut, retakes and pauses out | `references/cut.md` |
| Motion graphics / captions / overlays on a cut (also an external cut) | `references/motion.md` |
| A b-roll moment animated, an app or tool shown | `references/broll.md` (inside phase 2) |
| Alternate hooks as separate versions | `references/cut.md` step 7 |
| Clips from a long video or podcast, a creator teardown, a creator-style edit with live captures, a product film from a website, NLE export | `references/extras.md` |
| A correction ("too slow", "captions higher", "always ...") | `references/taste.md`, then redo |

## 2. The flow and its gates

1. **Cut plan** (phase 1): transcript -> quoted spans -> paper edit -> REPORT.md. Gate 1: the user
   approves the plan before the first render.
2. **Cut** (phase 1): render, verify (MISSING/SURVIVED, gaps, sync, head, level), cut-check page.
   The user approves the cut.
3. **Motion** (phase 2): prepare -> beats -> check -> stills sheet + stills critic. Gate 3: the user
   approves the sheet. Then render, verify, deliver.

Never skip a gate, never start phase 2 unasked, never hand over a file that has not been verified.
Between steps, one line on what happens next. Long renders run in the background.

## 3. Rules that never bend

- The source file is never modified, moved or copied.
- Every cut quotes the transcript. Order stays chronological; no word reordering, no micro-cuts
  between single words.
- The video starts on the first sound of the first word and ends right after the last sound of the
  last word; no silence over 0.12 s at any join; audio length = video length.
- On screen only the speaker's words: no invented numbers, no hype, no emoji, no em dash, no dates.
- Captions: one line, below the head, inside the Instagram safe zone. Hook bar: the first 3 s.
- Nothing covers the face. Real things over made-up visuals. No AI looks (`references/ai-tells.md`).
- Output file names lowercase; every version numbered with a plain name in one folder per video
  (`tools/deliver.py`), the folder opened in Finder, the file in QuickTime.
- Music only on request with a track the user owns. No images of people scraped from the web.

## 4. Files

- `tools/cutflow.py` phase 1 end to end; `tools/motion.py` phase 2; `tools/broll.py` HyperFrames
  beats; `tools/deliver.py` hand-over; `tools/taste.py` the rules; `tools/ai_tells.py`;
  `tools/privacy_check.py` (pre-commit); `tools/config.py` paths and creator.yaml.
- `tools/cut.py` the frame-accurate cutter; `tools/sync_check.py` lip sync per segment; `tools/eyes.py`
  eye contact at segment edges; `tools/take.sh` one take heard alone. The waveform edges live in
  NextWork's `build_timeline.py --edges waveform`; `tools/tighten.py`, `edges.py`, `snap.py` are the
  same method as standalone tools.
- `engine/` the Remotion overlay engine (copied into the workspace by setup; spec types in
  `engine/src/spec.ts`, example `engine/videos/example.json`).
- `hyperframes/template/` the b-roll starting point. `agents/stills-critic.md` the sheet reviewer.
- `nextwork/` NextWork ai-editor + creator-teardown (MIT), used by phase 1 and the extras.
- `config/*.template.*` what setup copies into the config home.
