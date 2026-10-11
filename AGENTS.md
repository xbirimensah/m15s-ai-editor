# Working on this repo

This repo IS an Agent Skill: `SKILL.md` is the entry point an agent loads to edit videos. These notes
are for changing the skill itself.

## Layout

- `SKILL.md` front door (routes + gates + rules), `references/*.md` one file per phase.
- `tools/` the Python/bash tools the skill runs (`config.py` resolves every path).
- `engine/` the Remotion overlay engine; `setup/install.sh` copies `src/` and `scripts/` into the
  user's workspace, so the workspace never holds hand edits.
- `hyperframes/` the HyperFrames skills as a plugin root (`plugin.json` pins the release). Never edit
  `hyperframes/skills/` by hand: `bash tools/sync_hyperframes.sh [version]` replaces it from upstream and
  pins the engine's CLI to the same version. `hyperframes/template/` is ours (the b-roll start).
- `nextwork/` vendored NextWork AI video editor (MIT). Keep local changes small and marked
  "local patch"; list them in `THIRD_PARTY_NOTICES.md`.

## Rules

1. **No personal data, ever.** Names, handles, client names, brand colours, e-mails, home or volume
   paths and keys belong in the user's config home (`~/.m15s-ai-editor`), never here. The pre-commit
   hook (`tools/privacy_check.py --staged`) blocks them; run `python3 tools/privacy_check.py` before
   any push. Examples use placeholders (Alex, @examplechannel, example.com).
2. **Agent-neutral.** Instructions name no vendor tool. Asking and delegating follow SKILL.md's
   "Asking" and "Delegating" fallbacks. Paths are `<skill>`, `<workspace>`, `<config home>`.
3. **Code measures, the agent decides.** Anything checkable goes into a tool with a clear FAIL/WARN
   line, not into prose.
4. English everywhere; on-screen text follows the video's language.
5. Keep the SKILL.md description under 1024 characters and `name` equal to the folder name.

## Test

```bash
bash tests/run_tests.sh      # syntax, unit tests, NextWork cut tests, privacy scan
python3 setup/doctor.py      # the installed pieces
```

An end-to-end change to the cut or the engine is tested on a real take: `tools/cutflow.py` through
`tools/motion.py render`, and the result watched.
