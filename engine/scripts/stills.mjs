// Stills for the approval sheet: bundle once, then render one PNG per requested frame.
// `npx remotion still` re-bundles for every frame; this does it once for the whole sheet.
//
//   node scripts/stills.mjs <compositionId> <spec.json> <outDir> <frame>:<label> [<frame>:<label> ...]
//
// Run from the engine root (the workspace). Writes <outDir>/<label>.png and prints one line each.
import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const [, , compId, specPath, outDir, ...frames] = process.argv;
if (!compId || !specPath || !outDir || frames.length === 0) {
  console.error('usage: node scripts/stills.mjs <compositionId> <spec.json> <outDir> <frame>:<label> ...');
  process.exit(2);
}

const inputProps = JSON.parse(fs.readFileSync(specPath, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });

const serveUrl = await bundle({
  entryPoint: path.resolve('src/index.ts'),
  publicDir: path.resolve('public'),
});
const composition = await selectComposition({ serveUrl, id: compId, inputProps });

for (const item of frames) {
  const [frameText, label] = item.split(':');
  const frame = Math.max(0, Math.min(Number(frameText), composition.durationInFrames - 1));
  const output = path.join(outDir, `${label}.png`);
  await renderStill({ composition, serveUrl, output, frame, inputProps, imageFormat: 'png' });
  console.log(`${frame}\t${output}`);
}
