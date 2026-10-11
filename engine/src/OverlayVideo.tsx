import React from 'react';
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type { Beat, VideoSpec } from './spec';
import { useThemeFonts } from './theme';
import { BRoll } from './components/BRoll';
import { Captions } from './components/Captions';
import { Chips } from './components/Chips';
import { Diagram } from './components/Diagram';
import { Endcard } from './components/Endcard';
import { ImageCard } from './components/ImageCard';
import { Kicker } from './components/Kicker';
import { HookBar } from './components/HookBar';
import { KineticHook } from './components/KineticHook';
import { ListBuild } from './components/ListBuild';
import { NameTag } from './components/NameTag';
import { Panel } from './components/Panel';
import { ProofCycle } from './components/ProofCycle';
import { StatScene } from './components/StatScene';
import { Takeover } from './components/Takeover';

/**
 * THE composition (VSL-style architecture):
 *
 *  - The finished cut runs as ONE continuous OffthreadVideo layer with
 *    its own audio across the whole composition and is NEVER re-cut.
 *  - Every beat is a purely visual Sequence that sits on top of it.
 *  - Punch-ins (4–7 % scale, decaying fast) at beat starts or on the
 *    return from canvas cutaways: the only intervention in the video image.
 *    Kicker starts (= chapter changes) punch a little harder.
 *  - Karaoke word captions globally, except during canvas/hook beats.
 *  - No SFX. Music only when spec.music is set.
 */

/** Does the beat cover the whole frame (canvas cutaway / full screen)? */
const isFullCover = (b: Beat): boolean =>
  b.type === 'stat' ||
  b.type === 'proof' ||
  b.type === 'endcard' ||
  b.type === 'broll' ||
  b.type === 'takeover' ||
  b.type === 'diagram' ||
  (b.type === 'list' && b.onVideo === false);

/** Beats during which captions pause (the scene carries the text). */
const masksCaptions = (b: Beat): boolean =>
  b.type === 'hook' ||
  b.type === 'stat' ||
  b.type === 'proof' ||
  b.type === 'endcard' ||
  b.type === 'takeover' ||
  b.type === 'diagram' ||
  (b.type === 'list' && b.onVideo === false);

/** Does the beat trigger a punch-in at its start? (Kicker handled separately.) */
const punchesOnStart = (b: Beat): boolean =>
  !isFullCover(b) && b.type !== 'nametag' && b.type !== 'kicker';

/** Continuous video layer with punch-ins. */
const VideoLayer: React.FC<{ src: string; beats: Beat[] }> = ({ src, beats }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  // Punch events: beat start for on-video beats, beat END for cutaways
  // (= return punch onto the face). Kicker = chapter change,
  // so it punches harder (4–7 %).
  const punches: { at: number; amount: number }[] = [];
  for (const b of beats) {
    if (isFullCover(b)) {
      punches.push({ at: b.from + b.dur, amount: 0.05 });
    } else if (b.type === 'kicker') {
      punches.push({ at: b.from, amount: 0.06 });
    } else if (punchesOnStart(b)) {
      punches.push({ at: b.from, amount: 0.045 });
    }
  }

  let punch = 0;
  for (const p of punches) {
    if (frame >= p.at) {
      punch = p.amount * Math.max(0, 1 - (frame - p.at) / 16);
    }
  }

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `scale(${1 + punch})`,
        transformOrigin: '50% 20%',
      }}
    >
      <OffthreadVideo
        src={staticFile(src)}
        style={{ width, height, objectFit: 'cover' }}
      />
    </div>
  );
};

export const OverlayVideo: React.FC<VideoSpec> = (spec) => {
  const theme = spec.theme;
  useThemeFonts(theme);

  const audioOffset = spec.audioOffsetFrames ?? 0;
  const captionsOn = spec.captions?.enabled ?? true;
  const mask: [number, number][] = spec.beats
    .filter(masksCaptions)
    .map((b) => [b.from, b.from + b.dur]);
  /** Windows in which a cutaway covers the frame (absolute); the kicker
   *  fades out there instead of floating over unrelated canvas scenes. */
  const coverWindows: [number, number][] = spec.beats
    .filter(isFullCover)
    .map((b) => [b.from, b.from + b.dur]);

  return (
    <AbsoluteFill style={{ backgroundColor: spec.overlayOnly ? 'transparent' : '#000' }}>
      {spec.overlayOnly ? null : <VideoLayer src={spec.video} beats={spec.beats} />}

      {spec.music && !spec.overlayOnly ? (
        <Audio src={staticFile(spec.music.file)} volume={spec.music.volume} loop />
      ) : null}

      {spec.beats.map((b, i) => (
        <Sequence key={i} from={b.from} durationInFrames={b.dur} layout="none">
          {b.type === 'hook' && <KineticHook lines={b.lines} dur={b.dur} theme={theme} />}
          {b.type === 'hookbar' && <HookBar text={b.text} dur={b.dur} theme={theme} y={b.y} />}
          {b.type === 'stat' && (
            <StatScene value={b.value} label={b.label} sub={b.sub} dur={b.dur} theme={theme} locale={spec.locale} />
          )}
          {b.type === 'list' && (
            <ListBuild
              title={b.title}
              items={b.items}
              itemAt={b.itemAt.map((a) => a - b.from)}
              onVideo={b.onVideo !== false}
              dur={b.dur}
              theme={theme}
            />
          )}
          {b.type === 'chips' && (
            <Chips
              items={b.items.map((it) => ({ ...it, at: it.at - b.from }))}
              dur={b.dur}
              theme={theme}
            />
          )}
          {b.type === 'imagecard' && (
            <ImageCard
              image={b.image}
              name={b.name}
              sub={b.sub}
              side={b.side ?? 'right'}
              dur={b.dur}
              theme={theme}
            />
          )}
          {b.type === 'proof' && (
            <ProofCycle images={b.images} title={b.title} dur={b.dur} theme={theme} />
          )}
          {b.type === 'broll' && <BRoll video={b.video} dur={b.dur} />}
          {b.type === 'endcard' && (
            <Endcard
              title={b.title}
              sub={b.sub}
              cta={b.cta}
              icon={b.icon}
              dur={b.dur}
              theme={theme}
            />
          )}
          {b.type === 'panel' && (
            <Panel
              position={b.position ?? 'top'}
              side={b.side ?? 'right'}
              icon={b.icon}
              eyebrow={b.eyebrow}
              title={b.title}
              rows={(b.rows ?? []).map((r) => ({ ...r, at: r.at - b.from }))}
              dur={b.dur}
              theme={theme}
            />
          )}
          {b.type === 'takeover' && (
            <Takeover
              eyebrow={b.eyebrow}
              lines={b.lines}
              sub={b.sub}
              icons={b.icons}
              dur={b.dur}
              theme={theme}
            />
          )}
          {b.type === 'diagram' && (
            <Diagram
              kind={b.kind}
              title={b.title}
              left={b.left}
              right={b.right}
              verdict={b.verdict}
              verdictAt={b.verdictAt !== undefined ? b.verdictAt - b.from : undefined}
              steps={(b.steps ?? []).map((s) =>
                s.at !== undefined ? { ...s, at: s.at - b.from } : s
              )}
              dur={b.dur}
              theme={theme}
            />
          )}
          {b.type === 'kicker' && (
            <Kicker
              text={b.text}
              align={b.align ?? 'center'}
              dur={b.dur}
              theme={theme}
              mask={coverWindows.map(([a, c]) => [a - b.from, c - b.from])}
            />
          )}
          {b.type === 'nametag' && (
            <NameTag
              name={b.name}
              sub={b.sub}
              side={b.side ?? 'left'}
              dur={b.dur}
              theme={theme}
            />
          )}
        </Sequence>
      ))}

      {captionsOn ? (
        <Captions
          words={spec.words}
          theme={theme}
          y={spec.captions?.y}
          font={spec.captions?.font}
          plain={spec.captions?.style === 'plain'}
          activeColor={spec.captions?.activeColor}
          audioOffsetFrames={audioOffset}
          mask={mask}
        />
      ) : null}
    </AbsoluteFill>
  );
};
