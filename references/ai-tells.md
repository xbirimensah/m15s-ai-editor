# AI tells: what makes an edit look AI-made

Adapted from NextWork ai-editor (`vendor/ai-video-editor/.../style-edit/references/ai-tells.md`,
with sources) and fitted to the engine. `<skill>/tools/ai_tells.py <workspace>/videos/<slug>.json`
checks everything marked **code** before every render. The rest is checked on the stills.

- **BAN**: never. Only exception: `creator.yaml` → `ai_tells_allowed` names the ID (brand colours).
- **WARN**: allowed with a reason. State the reason in the report.

## Colour

- `neon-on-black` BAN, code: a near-black background with ONE loud accent (lime, cyan, magenta, purple).
  Instead: real content, or the brand colours from creator.yaml, used sparingly.
- `purple-blue` BAN, code: purple/indigo accents, purple-to-blue gradients, gradient text.
- `gradient` WARN, code: a two-colour gradient as a card background. Only if the brand has one.
- Cream/beige paper background, flat saturated solid background (vermilion, forest green) BAN (stills).

## Surfaces

- `glass-panel` BAN: frosted glass, backdrop blur, glowing borders. Instead: a plain card, a real
  soft shadow, or no card at all.
- `glow-halo` BAN: neon glow/bloom around shapes and text. Instead: clean edges, depth through shadow.

## Icons

- `slop-icon` BAN, code: sparkle, star (and magic wand, rocket, bot). WARN, code: bolt, brain.
  The sparkle for "AI" and the rocket for "launch" are the first things a model reaches for.
- `icon-only` BAN, code: a card whose only image is icons. Icons only alongside text,
  a logo or a real image.

## Text in the picture

- `emoji` BAN, code: emoji in captions, cards, labels.
- `slop-copy` BAN, code: Unlock, Supercharge, Game-changer, Next level, Level up, Seamless, Elevate,
  Revolutionize, Effortless, Empower, Leverage, Unleash, Skyrocket, Cutting-edge, plus the German
  bahnbrechend, revolutionär, mühelos, entfesseln, auf das nächste Level, im Handumdrehen.
  Instead: the speaker's own words from the transcript.
- `multiplier-claim` BAN, code: invented comparison multipliers ("200x faster than X").
  A number the speaker states, e.g. 10x in their own calculation, may appear as a `stat`.
- `invented-text` BAN: text in the picture the speaker did not say (no invented stats,
  quotes, dashboards with made-up numbers).
- `heading-subline-rule` BAN: big centred headline, grey subline, short accent bar.
- `text-heavy` WARN, code: more than one `takeover` per video, or more than half of the beats
  are pure text cards.

## Captions

- `preset-captions` WARN, code: ALL CAPS + yellow active word + outline, word by word
  (the Hormozi preset from every caption app).
- Keyword colour roulette WARN: more than one highlight colour. One colour: `capActive`.

## Motion & sound

- Zoom on every line WARN: more than ~15 punch-ins per minute.
- Always the same designed transition WARN. Mostly hard cuts, one effect for one or two moments.
- Stock whoosh, vine boom, AI images as b-roll BAN.
