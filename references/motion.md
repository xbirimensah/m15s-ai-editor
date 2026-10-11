# Phase 2: motion graphics

ONE approved cut in (from phase 1, or a finished cut from CapCut etc.: put it at
`work/<slug>/cut.mp4`). Motion graphics go ON TOP; the video is never cut again here.

**Work autonomously**: plan every beat from the transcript yourself, show the stills sheet, and ask
only there. No beat-by-beat questions before the sheet.

The engine is the workspace
(`tools/config.py get workspace`): `src/` is the skill's code, `videos/<slug>.json` is the spec,
`public/` holds the cut, images and b-roll, `out/` the renders.

## Architecture (not negotiable)

The cut runs as ONE continuous layer with its own sound. Every beat is a purely visual layer
(Sequence) above it, so sound is always in sync. Subtle punch-ins (4-7 %) at chapter changes are
allowed (the kicker triggers them).

## 0. Brand + intake (only when creator.yaml is missing or incomplete)

1. "Paste the creator's Instagram (and website)." Look at them in the browser. Instagram without a
   login shows bio, highlights and the first grid posts; the link-in-bio page and the website are open
   and usually carry the real brand. DERIVE 2-3 colours (bg, ink, accent, cap_active), a style
   direction (clean / warm / editorial / technical) and Google Fonts (a serif + a sans). Propose: "This
   is the brand I see. Right?" Confirmed or corrected -> creator.yaml.
2. Niche + no-gos. Health creators (doctors!): no healing promises, no before/after suggestion (in
   Germany: HWG). Finance: no return promises.
3. CTA text (+ handle or link) for the end card.
4. Assets, asked for actively: "Any images or proof: result screenshots, press, certificates,
   product photos, photos of people you name? Put them in <assets_dir>." Never scrape images of people.
5. Music: off by default. Only on an explicit request with a track the user owns, quiet (~8 %).
6. Pronunciation fixes: names and terms Whisper mishears go in `pronunciation_fixes` (grows per video).

## 1. Prepare

```bash
python3 <skill>/tools/motion.py prepare <slug>
```

Copies the cut into `public/cut/`, builds the caption words from what the verify pass HEARD in the
cut (corrected to the approved text, the creator's pronunciation fixes and every `retakes.py fix`),
finds the head over the whole cut (`face.json`) and suggests the caption line below it and the panel
side away from it (`layout.json`), then writes a spec skeleton (theme, words, captions, locale, the
hook bar). Proofread `work/<slug>/captions.txt` against the context: wrong words on screen are the
most common defect. Fix with `python3 <skill>/nextwork/ai-editor/skills/cut/scripts/retakes.py fix <workdir> wrong=Right`, then
`motion.py prepare <slug> --refresh-words` (the spec keeps its beats). The verify pass can hear a word
RIGHT that the first transcript got wrong; captions take the approved cut text, so check those spots; put new
finds into creator.yaml `pronunciation_fixes`.

## 2. Plan the beats (videos/<slug>.json)

Read the transcript like an editor. First split it into CHAPTERS (Hook / Problem / Mechanism / Proof /
Application / CTA or similar), then choose per chapter the scene that fits the CONTENT. Every cue hangs
on a SPOKEN WORD from the spec's `words`: frames = seconds x 30, never by feel.

Times: `words[].s/e` in seconds; `beats[].from/dur` and every cue (`itemAt`, `items[].at`,
`rows[].at`, `steps[].at`, `verdictAt`) in absolute frames.

| Content | Beat | Payload core |
|---|---|---|
| The hook, first 3 s (always) | `hookbar` | `text`; `from: 0`, `dur: hookbar.seconds x fps` (3 s = 90) |
| Chapter change | `kicker` (persistent label + automatic punch-in) | `text`, `align?`. None in intro, CTA or honest moments |
| Who is speaking (intro, authority) | `nametag` | `name`, `sub?`, `side?` |
| A list of facts or reasons with substance | `panel` (the workhorse: card, icon badge, eyebrow, serif title, rows building on cues) | `position: top\|bottom` (away from the face, see layout.json), `icon?`, `eyebrow?`, `title?`, `rows[]: {text, at, icon?}` |
| Myth vs fact, A vs B | `diagram` `versus` | `left/right: {label, icon?}`, `verdict`, `verdictAt` |
| A mechanism ("first X, then Y") | `diagram` `flow` | `steps[]: {label, icon?, at}` (2-4) |
| A trade-off ("too much vs too little") | `diagram` `scale` | `left/right`, `verdict` |
| THE one core statement of the video | `takeover` (full canvas, big serif, `*accent*` markup) | `lines[]`, `sub?`, `icons?[]`; 1x per video |
| A strong number the speaker says | `stat` (count-up) | `value`, `label`, `sub?` |
| A 3-item list in the flow of speech | `list` | `items[]`, `itemAt[]`, `onVideo?` (close-up: false) |
| A term or name in passing | `chips` | `items[]: {text, at, icon?}` |
| A named person/product with a real asset | `imagecard` | `image` (in public/), `name`, `sub?`, `side?` |
| Screenshots, results, press | `proof` | `images[]`, `title?` |
| A named app, tool or workflow with no real asset, or a metaphor that needs motion | `broll` from HyperFrames (`references/broll.md`) | `video: broll/<file>.mp4`, under 100 frames |
| The user's own b-roll clip | `broll` | `video`, under 100 frames (Ken Burns added) |
| CTA | `endcard` | `title`, `sub?`, `cta`, `icon?` (from creator.yaml) |
| A punchy line to slam | `hook` (kinetic words) | `lines[]` with `*accent*`; not at the same time as the hook bar |

Icons (`src/components/Icons.tsx`: check, x, leaf, heart, shield, warning, brain, gut, muscle, bowl,
money, chart-up, clock, calendar, scale, bolt, flame, drop, chat, search, lock, arrow-up/down/right,
pill...) are chosen for the CONTENT (shield = safety, warning = myth, scale = trade-off) and always
accompany text or a real image, never alone. `sparkle` and `star` never; `bolt` and `brain` only with a
reason.

**Real things first.** Where a sentence names something real (a product, site, app, post, person, a
figure shown on the page that published it) prefer the real thing: the user's asset (`imagecard`,
`proof`), a screenshot of the real page (with a browser or screenshot tool if your agent has one, else ask the
user for it; save into `public/`), or a
HyperFrames replica that looks like the real app. Never two cards at once. Where nothing is named,
the speaker carries it: a kicker change or a punch-in, never a made-up visual.

**On-screen words are the speaker's words.** No invented numbers, no hype words, no emoji, no em dash,
no dates (`references/ai-tells.md`, creator.yaml `text_bans`).

**Captions** (creator.yaml `captions`): always ONE line (the engine caps 26 characters sans, 34 serif,
no wrap). `y` below the lowest point of the head (layout.json) and inside the Instagram safe zone
(not in the bottom 500 px, not in the top 250 px, 120 px clear on the right; the engine clamps at
y 1340). Greenscreen reels: ask first "captions only, or graphics too?".

**Pacing (vertical)**: something visible happens every 4-8 s; in the first 20-30 s a little denser,
then let it breathe. Entries 0.35-0.5 s. Two cues under 60 frames apart read as one movement: keep
them apart. No 3-second window where only captions move (canvas scenes breathe on their own).

**Style ("restraint is the aesthetic")**: everything ENTERS (fade + ~20 px rise, or scale 0.96 -> 1,
0.4-0.6 s ease-out), nothing cuts in hard; no whoosh SFX, no spins, no hard zooms; max ONE hero effect
per beat besides captions.

## 3. Check, then the stills sheet (APPROVAL GATE)

```bash
python3 <skill>/tools/motion.py check <slug>      # every FAIL fixed; every WARN fixed or given a reason in the report
python3 <skill>/tools/motion.py stills <slug>     # work/<slug>/stills/sheet.png, one numbered tile per beat
```

`check` covers timing, the 3-second hook bar, cue spacing, gaps without visuals, em dash and dates,
captions in the safe zone and off the head, AI tells (`tools/ai_tells.py`) and `tsc`. Then spawn the
stills critic as a sub-agent (prompt = the body of `<skill>/agents/stills-critic.md` plus the sheet path
and spec path; without sub-agents, run that checklist on the sheet yourself) and fix what it fails before the user sees anything.

Show the sheet and ask: **Approve (Recommended)** / **Change something**. **Never render before
approval.** Notes become taste rules first (`references/taste.md`), then spec changes, check, stills.

## 4. Render and verify

```bash
python3 <skill>/tools/motion.py render <slug>            # --draft: half size, for a quick look
```

Checks duration against the spec, that the sound is there (never -inf), and writes 4:5 crop frames
(`qa/crop45-*.png`: Meta crops feed placements to 4:5) to look at. Then hand over:

```bash
python3 <skill>/tools/deliver.py <slug> <workspace>/out/<slug>.mp4 "motion v1"
```

Short report: which beats where, which assets, what was left out on purpose. Ask for notes.

## 5. Other outputs

- `python3 <skill>/tools/motion.py srt <slug>`: one-line captions as SRT.
- `python3 <skill>/tools/motion.py export <slug>`: cut + transparent overlay (ProRes 4444) + SRT, to finish in an NLE.
- A 16:9 version: `prepare --aspect 169` on its own slug, `Overlay169` (panels become side panels).
- A split-screen reel (b-roll top 1080x960 muted, speaker bottom 1080x960 with the sound, captions at
  the seam, looks `bold` or `sentence`): composition `SplitReel`, props in `engine/src/SplitReel.tsx`
  (`broll`, `face`, `words`, `variant`, optional `fulls` for full-screen b-roll stretches). Cut the
  speaker half with `cut.py` format `split_bottom` (1080x960) and a `crop_x`; build the top half from
  HyperFrames beats (`references/broll.md`, 1080x960) joined to exact frames. Render:
  `npx remotion render SplitReel out/<slug>.mp4 --props=videos/<slug>.json --concurrency=2`.

## What this phase never does

Cut the video again (phase 1), pull images of people from the web, add music unasked, render without
check + stills approval, use anything `ai-tells.md` bans unless creator.yaml allows it.
