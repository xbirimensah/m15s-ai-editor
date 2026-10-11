# Taste: every correction becomes a rule

The user should never have to say the same thing twice. Rules live in the config home
(`taste.json`, mirrored to `TASTE.md`), never in the repo, and beat engine defaults and creator.yaml.

## Before every video

`python3 <skill>/tools/taste.py show --video <slug>` and follow every rule (it counts each as applied). If a rule contradicts
this skill, say so once and follow the rule: the user chose it.

## After every correction

1. Find the behaviour behind it, not the single case: "too slow at 0:14" -> "pauses before a number
   max 0.2 s"; "the card at 0:14 is too small" -> "cards fill the space they have".
2. Ask its scope: **Always (Recommended)** / **This video only**. Skip when the user
   already said ("always", "just here").
3. Save: `python3 <skill>/tools/taste.py add <area> "<rule>" [--video <slug>] [--id N]`. Areas: cut, captions, graphics, sound,
   delivery, general. With a number or value wherever possible ("captions 6 % of frame height", not
   "bigger"). Changing an existing rule: `--id N`.
4. Say in one line what was saved, so a wrong rule is caught at once.
5. `add` prints REGRESSION: the rule already applied and did not hold. Say so and make it more
   concrete (a number), never re-save the same words.
6. Apply it: map the timestamps to spans or beats, re-render, keep the old version (`v1`), update
   the report.

"What have you learned?": `python3 <skill>/tools/taste.py report`.

## Settings that live in creator.yaml instead

Some corrections are a setting, not a rule: caption font/position/style (`captions`), hook bar
length (`hookbar.seconds`), on-screen text bans (`text_bans`), brand colours (`brand`), delivery
folder. Change the setting AND save a one-line rule, so the reason is kept.
