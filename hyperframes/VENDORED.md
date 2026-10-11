# HyperFrames, bundled

`skills/` is the `skills/` folder (test files left out, nothing else changed) of [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes/tree/v0.8.147)
at release v0.8.147 (commit `d4dd6c097d22ca890c0eea401eaebf550ce10fae`), licensed Apache-2.0 (`LICENSE`). Copyright HeyGen.

`plugin.json` makes this folder a HyperFrames plugin root, so the skills follow their own plugin rules
(`skills/hyperframes/references/plugin-installation.md`): every skill reference resolves inside this
bundle, nothing is downloaded or updated at run time, and the CLI runs at exactly 0.8.147 through
`skills/hyperframes/scripts/plugin-cli.mjs` (the workspace's own `node_modules/.bin/hyperframes` is the same
version). `template/` is m15s-ai-editor's own b-roll starting point, not part of HyperFrames.

Update to a newer release: `bash tools/sync_hyperframes.sh [version]`, then `bash setup/install.sh`.
