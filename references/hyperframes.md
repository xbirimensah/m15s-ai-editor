# HyperFrames inside m15s-ai-editor

HyperFrames (HeyGen, Apache-2.0) renders video from HTML. Its complete skill set ships in this skill at
`<skill>/hyperframes/` as a **HyperFrames plugin root**: `plugin.json` (release pin), `skills/` (every
HyperFrames skill), `LICENSE`, `VENDORED.md`. Remotion stays the engine for talking-head overlays
(phase 2); HyperFrames makes b-roll beats and every video HyperFrames has a workflow for.

## Running it: plugin mode, always

`PLUGIN_ROOT` is `<skill>/hyperframes`. Start every HyperFrames task by reading
`<skill>/hyperframes/skills/hyperframes/SKILL.md` (the router), and follow its plugin rules
(`skills/hyperframes/references/plugin-installation.md`) in every workflow:

- A skill named `/name` (e.g. `/hyperframes-core`, `/media-use`, `/general-video`) is
  `<skill>/hyperframes/skills/<name>/SKILL.md`. Resolve every reference inside the bundle, even when a
  copy of the same skill is installed elsewhere.
- Never run `hyperframes skills update`, `skills check` or `npx skills add`: the bundle is
  release-managed. A missing skill is reported, never downloaded.
- Every `npx hyperframes <command>` in the HyperFrames skills runs as
  `node <skill>/hyperframes/skills/hyperframes/scripts/plugin-cli.mjs <command>`, in the project folder
  (never inside the skill). That is exactly the bundled release; the workspace's `node_modules` holds
  the same version, so it is instant and works offline.
- A project's `npx hyperframes@latest upgrade` advice does not apply: the release is the bundle's.
  New release: `bash <skill>/tools/sync_hyperframes.sh [version]`, then `bash <skill>/setup/install.sh`.

## Where projects live

One HyperFrames project per video: `<workspace>/work/<slug>/hf/` (a b-roll beat: `work/<slug>/broll/NN-name/`,
made by `tools/broll.py`). Finished renders are handed over like every other version:
`python3 <skill>/tools/deliver.py <slug> <file> "<what it is>"`.

## m15s rules on top of every HyperFrames workflow

- Brand: the design spec a workflow asks for (palette, type, design.md/frame.md) is filled from
  creator.yaml `brand` and `<config home>/broll-style.md`, never invented. Confirm it once, as the
  intake does.
- Taste rules (`tools/taste.py show --video <slug>`) and creator.yaml `text_bans` apply: no em dash,
  no dates, only the speaker's or the brief's words on screen, no AI looks (`references/ai-tells.md`).
- Vertical output keeps the Instagram safe zone (nothing in the bottom 500 px or top 250 px, 120 px
  clear on the right); captions one line; a hook bar (when the video has one) for the first 3 s.
- Raw talking-head footage is cut in phase 1 first (`references/cut.md`); HyperFrames works on
  `work/<slug>/cut.mp4`, never on the raw take.
- Render one HyperFrames project at a time (parallel renders can silently write no file); check the
  output exists and is new.

## Which HyperFrames workflow

| The user wants | Workflow (`<skill>/hyperframes/skills/<name>/SKILL.md`) |
|---|---|
| An animated b-roll moment inside an m15s edit | `references/broll.md` (uses `hyperframes-core`) |
| Designed captions on a talking-head video (cinematic, kinetic, a caption look) instead of the engine's word captions | `embedded-captions` on the approved cut |
| Designed overlay cards on a talking head or podcast (kinetic titles, lower-thirds, data callouts) instead of phase 2's beats | `talking-head-recut` on the approved cut |
| A video from text with no footage (article, notes, topic) | `faceless-explainer` |
| A short design-led motion graphic: kinetic type, stat count-up, chart hit, logo sting | `motion-graphics` |
| A product launch or promo video from a URL, script or brief | `product-launch-video` (a recorded walk through a real web app: NextWork's product-video, `references/extras.md`) |
| A beat-synced video from a music track (lyric video, slideshow to music) | `music-to-video` |
| A deck, pitch or interactive slideshow | `slideshow` |
| A code-change explainer from a GitHub pull request | `pr-to-video` |
| Figma frames, tokens or components brought to motion | `figma` |
| A Remotion composition ported to HyperFrames | `remotion-to-hyperframes` (only on an explicit ask) |
| Anything else made in HyperFrames | `general-video` |

The domain skills every workflow leans on are in the same bundle: `hyperframes-core` (the composition
contract), `hyperframes-cli`, `hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`,
`hyperframes-registry`, `hyperframes-audio`, `hyperframes-studio`, `media-use`.

Default for a talking-head reel stays m15s phase 1 + phase 2 (Remotion). Offer `embedded-captions` or
`talking-head-recut` when the user asks for that look; say which one you are using.
