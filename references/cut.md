# Phase 1: the cut

Raw talking-head footage in, a clean, dense cut out. Nothing new, nothing reordered: only the best
of what was recorded. **You propose, the user approves, then you render.**

`NW` below means `<skill>/nextwork/ai-editor/skills/cut`. Everything lands in `<workspace>/work/<slug>/`.
Never modify, move or copy the source file.

## 1. Intake (only what is missing)

- The footage path. A folder with several clips: one slug per clip, or ask which clip is the take.
- `slug`: lowercase from the file or the topic (`DJI_..._0013.MP4` -> `0013-topic`).
- A script, if there is one: it breaks ties between takes; nothing is cut for being off-script.
- Format comes from creator.yaml (`format`); ask only if it is missing.

## 2. Transcribe

```bash
python3 <skill>/tools/cutflow.py transcribe <source> <slug> [--lang de]
```

mlx-whisper large-v3-turbo on the Apple GPU (about 1 min for a 4-min take; say the time first),
with `terms.txt` as the vocabulary. Writes `words.raw.json` (never read it), `transcript.txt`
(read this), `candidates.md` (every place code flagged: restarts, unfinished phrases, talking to
self, fillers) and `hooks.json` (alternate hooks recorded after the body). A misheard word:
`python3 <skill>/nextwork/ai-editor/skills/cut/scripts/retakes.py fix <workdir> wrong=Right` (timings kept, reused for captions).

Set `language` in creator.yaml instead of `auto` for non-English footage: on auto, Whisper
translates stretches of German (and other languages) into English.

## 3. Decide what goes: spans.json

Read `transcript.txt` and `candidates.md`, then read and follow
`<skill>/nextwork/ai-editor/skills/cut/references/retake-detection.md` (kinds, last-take-wins, alternate hooks, mistakes to avoid).
Write `spans.json` as `<skill>/nextwork/ai-editor/skills/cut/references/shapes.md` describes: every cut QUOTES the transcript, never a
timestamp, never a span for a pause (pauses are the waveform cutter's job).

On top of those rules (these come from real edits and win over them):

- **Whisper merges restarts.** When a passage has several takes, listen to each candidate take
  alone: `bash <skill>/tools/take.sh <source> <label> <start> <end> win [lang]` prints text, length,
  words per second and the longest pause per take. Pick the fluent, energetic one. The last clean
  take is usually the one the speaker settled on.
- **Grammar beats the best single take.** If no take of a sentence is clean (typical at the CTA),
  keep the first half of one take and the second half of another when background and head position
  match; check the join in the paper edit.
- **Never reorder words or move a verb by cutting, and no micro-cuts between single words.** That
  reads hectic. A sentence that only works rearranged is a reshoot from a corrected script.
- **A line only an earlier take has right** (the script breaks the tie toward it): a `move` span
  (see shapes.md) plays that line from the earlier run in the right place; remove the later take of
  it with its own span. Prefer the last take in place when it is as good: a move is a jump back in time.
- **Director talk goes**: "wait, again", instructions to the camera, side conversations. Exception:
  a second voice that is part of the format (an interview question) stays, say why in the report.
- **Logic holes**: if a kept line refers to something you cut ("this problem" without the problem),
  find a replacement line in the discarded takes or list it as an open point. Order stays
  chronological, always.
- **Several complete run-throughs**: compare them whole and recommend one (or two versions if both
  are strong).
- **Greenscreen / changing backgrounds**: look at a contact sheet
  (`ffmpeg -i <src> -vf "fps=1/12,scale=216:-1,tile=7x3" -frames:v 1 sheet.png`); if the background
  changes per block, pick each sentence's take on the matching background.
- Only when the user wants it shorter: `<skill>/nextwork/ai-editor/skills/cut/references/editorial-rules.md` (`redundant` cuts).

## 4. Paper edit, then the plan (CHECKPOINT)

```bash
python3 <skill>/tools/cutflow.py build <slug> --dry-run     # fix every ERROR (a quote that does not match, a phrase found twice)
python3 <skill>/tools/cutflow.py build <slug>               # decisions.json + paper-edit.md
```

Read `paper-edit.md` straight through: it is what the viewer hears, `<<n>>` at every join. A flub
still in it: add a span. A join that reads wrong or a sentence nobody said: move the span. A good line
gone that no better take replaces: drop that span. Loop until it reads clean (free; a render costs
minutes).

Then write `work/<slug>/REPORT.md` and show the core of it in chat:
- the narrative chain in one line (Hook > Problem > ... > CTA)
- what goes and why, grouped (takes, false starts, director talk, fillers; pauses are automatic)
- length before / after (paper edit), alternate hooks found
- weak spots in the SOURCE that no cut can fix, honestly
- open decisions for the user

Ask: **"Does the plan work, or should I cut anything differently?"** (options: Render it
(Recommended) / Change something). Wait. Feedback goes into spans.json and REPORT.md.

## 5. Render (after approval)

```bash
python3 <skill>/tools/cutflow.py render <slug> [--fit cover --crop-x <px>]
```

`build` already set every edge on the audio (`build_timeline.py --edges waveform`): each run of kept
words starts on its first sound and ends on its last, pauses over 0.15 s become 2 x 0.05 s, each edge
is found in two stages (the word core at -42 dB, soft endings out to -52 dB, so "reicher" never
becomes "reich"), breaths, clicks and stray starts of cut takes at the joins are dropped, and words
the edges took for silence are put back. `render` then turns decisions.json into plan.json (format
and fps from the source: a 4K portrait take stays 4K, `916_4k`; DJI 3K `916_3k`), cuts it with
`cut.py` (frame-accurate picture; sound cut from one exact PCM decode so no segment drifts; 12 ms
fades at every join; gentle loudness), runs `verify_cut.py` and the checks, and opens
`cut-check.html`.

Landscape source into 9:16: extract a frame, LOOK where the person stands, pass `--crop-x` on them.
Never crop blind to the centre.

## 6. Verify before showing (the command does it; read every line)

- **MISSING** (verify_cut): a kept word is not in the render: an edge is too tight (or the word
  was mumbled: listen before changing anything). **SURVIVED**: a
  stumble is still there: add the printed span, build, render. HEARD DIFFERENTLY is transcriber noise.
- **gaps**: no silence over 0.12 s at -40 dB. A leftover snippet (the start of a cut take): quote it
  as a span, build, render.
- **REPEAT** (verify_cut): each run of the render is heard again on its own; a line said twice inside
  a run or across a join is listed with its source time (Whisper hearing the whole render collapses a
  line said three times into one). Add a span for the extra take.
- **sync**: decoded audio length = video length. **lipsync**: every segment's sound cross-correlated
  against the source at lag 0 (`tools/sync_check.py`): catches sound taken from the wrong place. **head**: first word under 0.5 s. **level**: peak
  present (never -inf).
- Listen to 2-3 joins (`ffplay -ss <t-1> -t 2 cut.mp4`) when the report flagged a tricky splice.
- The last word must be complete, with no tail after it.
- **Eye contact at the edges** (when the taste asks for it, or the speaker reads off a script):
  `python3 <skill>/tools/eyes.py <workdir>` -> `eyes.png`, every segment's first and last frames cropped to
  the eyes, labelled in source time. A look-away at an edge while speaking: quote those words as a span
  (`meta`, note "looks away"), build, render. Segments under full-screen b-roll: `--skip`.

One fix cycle, then show the user what is left.

## 7. The user approves the cut

`cut-check.html` shows the whole transcript with every removed word struck through and the video.
Tell the user in two lines how many seconds came out and what the page shows. Hand the file over with
`tools/deliver.py <slug> work/<slug>/cut.mp4 "cut v1"`. Wait. "keep <line>": narrow or drop that span.
"cut <line>": add one. Then build, render, verify again (`v2`, keep v1).

`hooks.json` has alternates: after approval ask once: **Just the main cut
(Recommended)** / **One version per hook**. Per hook: `python3 <skill>/tools/cutflow.py hook <slug> <n>`, then build + render the
printed `<slug>-hook<n>`; they share nothing, so run them in parallel shell jobs.

Approved: offer phase 2 (motion graphics). Never start it on your own.

## Two people, two mics (interviews, podcasts, walk-and-talks)

The waveform cutter assumes one voice; for two:
- Transcribe with the language forced, in 60-s chunks, and each speaker's own mic channel separately
  (L, R): energy per channel tells who speaks. Re-probe unsure phrases in tight clips.
- Never mix two lavalier channels into one: the mics are a millisecond apart and the sum sounds
  hollow (comb filter). Per segment use the active speaker's channel, short crossfades between.
- In a loud room the -42 dB thresholds are useless: set edges where the speaker's mic stops being
  clearly (about 1.5 dB) louder than the other's.
- Whisper on short probe clips is flaky: verify by transcribing the whole finished cut.

## Corrections

Every correction becomes a rule (`references/taste.md`): find the behaviour, not the instance
("too slow at 0:14" -> "pauses before a number max 0.2 s").
