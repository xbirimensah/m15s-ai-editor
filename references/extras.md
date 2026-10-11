# Extras: the NextWork tools inside this skill

The NextWork AI video editor (MIT, `<skill>/nextwork/`, vendored with small local patches) brings
clips from long videos, creator teardowns, creator-style edits with real captures, product launch
films, cloud renders and NLE export. They need its own venv once: `bash <skill>/setup/install.sh --extras`
(installs into `~/.ai-video-editor`).

**How to run a NextWork skill from here.** Read its SKILL.md and follow it with these substitutions:

| NextWork says | here it is |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | `<skill>/nextwork/ai-editor` (creator-teardown: `<skill>/nextwork/creator-teardown`) |
| `${CLAUDE_SKILL_DIR}` | `<skill>/nextwork/ai-editor/skills/<name>` |
| `edits/<name>/` | `<workspace>/work/<slug>/` (same files: cut.mp4, words.json, cut.transcript.json) |
| the `cut` skill | phase 1 here (`references/cut.md`): our cut is better on joins |
| the `taste` skill | `references/taste.md` (`tools/taste.py`) |
| an agent named in `agents/` (clip-editor, template-filler, render-watcher, storyboard-critic, video-analyst) | a sub-agent whose prompt is that file's body plus the paths, or the same steps done yourself |
| the question box, AskUserQuestion | asking as SKILL.md describes |
| Claude, Claude Code | you, the agent running this skill |

Run NextWork commands from the workspace folder (`cd "$(python3 <skill>/tools/config.py get workspace)"`)
so its relative `clips/`, `edits/` and `creator-teardowns/` folders land there.

## Hook variants

Built into phase 1: `references/cut.md` step 7 (`cutflow.py hook`).

## Clips from a long video or podcast

`<skill>/nextwork/ai-editor/skills/clips/SKILL.md`, steps 0-4 as written (link or fetch, ONE
transcript, candidates + shortlist, the picks page, the user picks). Then, instead of its cut and
style-edit steps, per picked clip:

1. `clips.py trim` as written (it makes one folder per clip with a trimmed `source.mp4`).
2. One sub-agent per clip, all started at once (without sub-agents: one clip after another), each told: run phase 1 on that
   trimmed source as slug `<name>-clip<N>` with no plan checkpoint (the picks were the approval), then
   phase 2 up to and including `motion.py stills`; return JSON
   `{"slug", "seconds", "cuts", "sheet", "open_points"}`. Same creator.yaml and taste for all.
3. Show every stills sheet together; render the approved ones (`motion.py render`), in parallel shell
   jobs, then `deliver.py` each.

## Creator teardown: measure a creator, edit like them

`<skill>/nextwork/creator-teardown/skills/creator-teardown/SKILL.md`. 5 videos of the same format
(public Shorts/TikToks, or 10+ reel links: Instagram profiles are login-walled), plus 2 median
"control" videos: a move in the winners AND the controls is a habit, not the lever. Outputs
`creator-teardowns/<handle>/teardown.md` (beat map: time to first word, hook length, WPM per beat,
CTA position), `look.md`, `style.json`.

Two checks before trusting a teardown: `look.py` can report `captions.present: false` for a creator
whose frame sheets clearly show burned-in captions (look at one sheet), and reel links with play
counts are readable logged out in a browser (close the sign-up dialog), then `fetch.py list <handle>
--urls <file>`.

Use it in phase 2 as measurements, not taste: hook length, how often something changes on screen
(card gap), caption words per line and position, zoom rate. Structure is copied, voice never is. The
user's own taste rules and brand beat the creator's style.

## Creator-style edit with real captures (NextWork style-edit)

The alternative phase 2 when the user wants a measured creator look with live website captures,
logos, posts and smooth zooms instead of the editorial beats: run
`<skill>/nextwork/ai-editor/skills/style-edit/SKILL.md` on the approved cut's work folder (it already
has cut.mp4, words.json, cut.transcript.json). Same gates: stills sheet, then render (laptop, Modal,
GitHub Actions or AWS Lambda). Captions stay one line and the hook bar is not part of that engine:
say so when the user picks it.

## Product launch film from a website

Two engines: HyperFrames `product-launch-video` (`references/hyperframes.md`) for a designed promo from
a URL, script or brief; `<skill>/nextwork/ai-editor/skills/product-video/SKILL.md` when the film is a
recorded walk through a real web app (brief, story beats, recorded UI, music with a recorded licence).
Ask which one when it is not obvious.

## Export to an editor (Final Cut, Premiere, Resolve, CapCut)

- Editorial beats (phase 2 here): `motion.py export <slug>` writes cut + transparent overlay
  (ProRes 4444) + SRT. Cut on track 1, overlay on track 2.
- NextWork style-edit: `style-edit/scripts/export_nle.py <workdir> --to fcpxml|premiere|resolve|capcut|edl|srt|all`.

## Everything else NextWork has

`<skill>/nextwork/ai-editor/skills/*/SKILL.md` (setup doctor, improve, motion-design references) and
`<skill>/nextwork/ai-editor/PRINCIPLES.md` (asking, looking real, motion, privacy, cost). Its setup
doctor: `python3 <skill>/nextwork/ai-editor/skills/setup/scripts/setup.py doctor`.
