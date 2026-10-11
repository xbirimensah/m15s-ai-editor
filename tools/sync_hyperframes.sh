#!/bin/bash
# Bundle the HyperFrames skills (Apache-2.0, heygen-com/hyperframes) at one release, as a HyperFrames
# plugin root: hyperframes/plugin.json + hyperframes/skills/<all> + LICENSE. In that layout the
# HyperFrames skills run in their plugin mode: every skill reference resolves inside this bundle, no
# skill is downloaded or updated at run time, and the CLI is the manifest's exact version.
#
#   bash tools/sync_hyperframes.sh            the npm "latest" release
#   bash tools/sync_hyperframes.sh 0.8.147    a given release
#
# Also pins the engine's hyperframes dependency to the same version. Then: bash setup/install.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
VERSION="${1:-$(npm view hyperframes version)}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "✗ not a release version: $VERSION"; exit 1; }
TAG="v$VERSION"
DEST="$ROOT/hyperframes"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/hf-sync.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

echo "→ heygen-com/hyperframes $TAG"
git clone -q --depth 1 --branch "$TAG" --filter=blob:none --sparse \
  https://github.com/heygen-com/hyperframes.git "$WORK/hf"
git -C "$WORK/hf" sparse-checkout set --no-cone '/skills/**' '/LICENSE' '/packages/cli/package.json'
COMMIT="$(git -C "$WORK/hf" rev-parse HEAD)"
CLI="$(node -p "require('$WORK/hf/packages/cli/package.json').version")"
[ "$CLI" = "$VERSION" ] || { echo "✗ tag $TAG holds CLI $CLI, not $VERSION"; exit 1; }

mkdir -p "$DEST"
rsync -a --delete --exclude '*.test.mjs' "$WORK/hf/skills/" "$DEST/skills/"
cp "$WORK/hf/LICENSE" "$DEST/LICENSE"
cat > "$DEST/plugin.json" <<JSON
{
  "name": "hyperframes",
  "version": "$VERSION",
  "description": "HyperFrames skills bundled in m15s-ai-editor (plugin mode: no run-time skill installs, CLI pinned)",
  "source": "https://github.com/heygen-com/hyperframes/tree/$TAG",
  "commit": "$COMMIT",
  "license": "Apache-2.0"
}
JSON
cat > "$DEST/VENDORED.md" <<MD
# HyperFrames, bundled

\`skills/\` is the \`skills/\` folder (test files left out, nothing else changed) of [heygen-com/hyperframes]($(printf 'https://github.com/heygen-com/hyperframes/tree/%s' "$TAG"))
at release $TAG (commit \`$COMMIT\`), licensed Apache-2.0 (\`LICENSE\`). Copyright HeyGen.

\`plugin.json\` makes this folder a HyperFrames plugin root, so the skills follow their own plugin rules
(\`skills/hyperframes/references/plugin-installation.md\`): every skill reference resolves inside this
bundle, nothing is downloaded or updated at run time, and the CLI runs at exactly $VERSION through
\`skills/hyperframes/scripts/plugin-cli.mjs\` (the workspace's own \`node_modules/.bin/hyperframes\` is the same
version). \`template/\` is m15s-ai-editor's own b-roll starting point, not part of HyperFrames.

Update to a newer release: \`bash tools/sync_hyperframes.sh [version]\`, then \`bash setup/install.sh\`.
MD

# The engine pins the same CLI version (exact, no range).
node -e "
const fs = require('fs'); const f = '$ROOT/engine/package.json';
const p = JSON.parse(fs.readFileSync(f, 'utf8'));
p.devDependencies = Object.assign({}, p.devDependencies, { hyperframes: '$VERSION' });
fs.writeFileSync(f, JSON.stringify(p, null, 2) + '\n');"

# Upstream skills carry their own .gitignore files that hide some tracked fixtures; stage those too, so the
# bundle in git is the complete release.
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$ROOT" ls-files -z --others --ignored --exclude-standard -- hyperframes/skills \
    | xargs -0 -r git -C "$ROOT" add -f --
fi

echo "✓ hyperframes/ = HyperFrames $VERSION ($(ls "$DEST/skills" | wc -l | tr -d ' ') skills, commit ${COMMIT:0:7}); engine pinned to $VERSION"
