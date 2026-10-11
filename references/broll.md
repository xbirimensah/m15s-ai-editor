# HyperFrames b-roll beats

Custom animated b-roll (HTML + GSAP rendered by HyperFrames) for moments where a sentence names an app,
tool or workflow and no real asset exists, or where an idea needs motion a card cannot give. The MP4
drops into the Remotion overlay as a `broll` beat. Remotion stays the editor; HyperFrames makes clips.

Tool: `python3 <skill>/tools/broll.py`. HyperFrames is bundled (`<skill>/hyperframes/`, plugin mode,
`references/hyperframes.md`); the tool runs its pinned CLI. Local renders need no account.

## When

- The speaker names a tool, app or workflow and there is no screenshot or asset: a replica that looks
  like the real thing (real window chrome, real labels, real numbers only).
- A mechanism that reads better moving than as a `diagram`.
- Never as decoration, never for text alone (that is a caption), never two b-roll beats in a row.
- Max 1 per 15 s; 3 s each (90 frames; a broll beat must stay under 100).

## Flow

1. Map exactly: the sentence (quote) -> the metaphor -> `NN-slug`. When the user names parts, part N
   = beat N, no more, no less. Write the table before building.
2. `python3 <skill>/tools/broll.py new <slug> NN-name [--seconds 3]` scaffolds `work/<slug>/broll/NN-name/index.html` (1080x1920,
   the brand colours, local GSAP and fonts). Read `<config home>/broll-style.md` for the look.
3. Build the metaphor in `index.html` (the template's comments hold the recipes). The authoring
   contract is `<skill>/hyperframes/skills/hyperframes-core/SKILL.md`; motion recipes are in
   `hyperframes-animation`, named blocks in `hyperframes-registry` (search before building by hand).
   Real facts only: look up real names, labels, install commands; never invent a number (no number
   found -> the visual without one). Fix Whisper mishearings in any on-screen word.
4. `python3 <skill>/tools/broll.py check <slug> NN-name`: lint + check --strict, 0 errors and 0 warnings. One folder at a time.
5. `python3 <skill>/tools/broll.py render <slug> NN-name --at-word "<word>"` renders into `public/broll/`, verifies size, fps and
   length, writes `qa/middle.png` + `qa/last.png`, and prints the beat. LOOK at both frames: payoff
   visible? still moving at the end? content inside y 480-1350?
6. Paste the printed beat into `videos/<slug>.json`, then `motion.py check` and `stills` as usual.
   Re-renders get a new name (`NN-name-v2`), never overwrite.

## Timing inside 3 s

Stage in by 0.5 s, payoff around 1.8-2.2 s, something alive until the last frame. The engine fades
the clip in over 8 frames, out over 6, adds a slow 6 % zoom and darkens the top 28 % and bottom 34 %:
keep content in the middle band. Captions keep running over b-roll.

## Traps (each cost a render once)

- Gauge needles are HTML divs, never SVG `<line>`.
- A scaleX fill needs `display:block; width:100%` or it is invisible.
- No CSS transform on an element GSAP also scales; wrap it.
- Keep every `@font-face`; fonts load locally (a Google Fonts import fails in the sandbox).
- No `Math.random`, `Date.now`, `repeat:-1`, `toLocaleString` (renders must be deterministic).
- No relative values (`x:'+='`) in keyframe chains with repeat; no second tween on a property while
  the first still runs.
- The timeline is `paused: true` and registered on `window.__timelines["root"]`.
- Render one beat at a time: parallel HyperFrames renders (two agents at once) can silently write no
  MP4. After each render check that the file exists and its time is new.
