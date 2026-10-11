import React, { useEffect, useMemo, useState } from 'react';
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  interpolate,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

/**
 * Split reel: b-roll on top (1080x960, muted), the speaker below (1080x960, carries the audio), captions at the seam.
 *   bold     = UPPERCASE, Archivo Black, white with a black outline, active word in a black box.
 *   sentence = sentence case, Inter 700, dark on the light b-roll background, upcoming words gray,
 *              active word bold italic.
 */
export type SplitWord = { w: string; s: number; e: number };

/** Full-screen b-roll (1080x1920) from `from` to `to` (seconds): covers the speaker and the top half. */
export type FullBroll = { src: string; from: number; to: number };

export type SplitReelProps = {
  broll: string;
  face: string;
  fps: number;
  durationInFrames: number;
  variant: 'bold' | 'sentence';
  words: SplitWord[];
  fulls?: FullBroll[];
  /** Caption center (y) during a full-screen b-roll; if omitted, the split position applies. */
  fullCaptionY?: number;
};

const HALF = 960;

type Look = {
  font: () => Promise<{ loadFont: () => { fontFamily: string; waitUntilDone: () => Promise<void> } }>;
  maxWords: number;
  maxChars: number;
  centerY: number;
};

const LOOKS: Record<SplitReelProps['variant'], Look> = {
  bold: { font: () => import('@remotion/google-fonts/ArchivoBlack'), maxWords: 3, maxChars: 18, centerY: HALF + 70 },
  sentence: { font: () => import('@remotion/google-fonts/Inter'), maxWords: 4, maxChars: 26, centerY: HALF - 80 },
};

type Chunk = { words: SplitWord[]; from: number; to: number };

const chunkWords = (words: SplitWord[], maxWords: number, maxChars: number): Chunk[] => {
  const out: Chunk[] = [];
  let cur: SplitWord[] = [];
  const len = (ws: SplitWord[]) => ws.reduce((n, w) => n + w.w.length + 1, -1);
  const push = () => {
    if (cur.length) out.push({ words: cur, from: cur[0].s, to: cur[cur.length - 1].e });
    cur = [];
  };
  for (const w of words) {
    if (cur.length && (cur.length >= maxWords || len(cur) + 1 + w.w.length > maxChars)) push();
    cur.push(w);
    if (/[.!?]$/.test(w.w) || (/,$/.test(w.w) && cur.length >= 2)) push();
  }
  push();
  // Each chunk stays up until the next one: no gap without a caption.
  return out.map((c, i) => ({ ...c, to: i + 1 < out.length ? out[i + 1].from : c.to + 0.4 }));
};

const useFont = (variant: SplitReelProps['variant']) => {
  const [family, setFamily] = useState<string>('sans-serif');
  const [handle] = useState(() => delayRender(`font ${variant}`));
  useEffect(() => {
    LOOKS[variant]
      .font()
      .then((m) => {
        const f = m.loadFont();
        setFamily(f.fontFamily);
        return f.waitUntilDone();
      })
      .catch((err) => console.error('font load failed, falling back to sans-serif', err))
      .finally(() => continueRender(handle));
  }, [variant, handle]);
  return family;
};

const BoldWord: React.FC<{ text: string; active: boolean; family: string }> = ({ text, active, family }) => (
  <span
    style={{
      fontFamily: family,
      fontSize: 62,
      lineHeight: 1.1,
      color: '#FFFFFF',
      textTransform: 'uppercase',
      letterSpacing: '0.01em',
      padding: active ? '2px 12px 6px' : '2px 4px',
      background: active ? '#111111' : 'transparent',
      borderRadius: active ? 8 : 0,
      WebkitTextStroke: active ? '0px' : '10px #000000',
      paintOrder: 'stroke fill',
      whiteSpace: 'nowrap',
    }}
  >
    {text}
  </span>
);

const SentenceWord: React.FC<{ text: string; state: 'said' | 'now' | 'next'; family: string }> = ({ text, state, family }) => (
  <span
    style={{
      fontFamily: family,
      fontSize: 50,
      lineHeight: 1.15,
      fontWeight: state === 'now' ? 800 : 700,
      fontStyle: state === 'now' ? 'italic' : 'normal',
      color: state === 'next' ? '#BDB7AC' : '#161616',
      padding: '0 6px',
      whiteSpace: 'nowrap',
    }}
  >
    {text}
  </span>
);

const Captions: React.FC<{
  words: SplitWord[];
  variant: SplitReelProps['variant'];
  fulls: FullBroll[];
  fullCaptionY?: number;
}> = ({ words, variant, fulls, fullCaptionY }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const family = useFont(variant);
  const look = LOOKS[variant];
  const chunks = useMemo(() => chunkWords(words, look.maxWords, look.maxChars), [words, look]);
  const t = frame / fps;
  const inFull = fulls.some((f) => t >= f.from && t < f.to);
  const centerY = inFull && fullCaptionY ? fullCaptionY : look.centerY;
  const chunk = chunks.find((c) => t >= c.from && t < c.to);
  if (!chunk) return null;

  const since = (t - chunk.from) * fps;
  const enter =
    variant === 'bold'
      ? { transform: `scale(${interpolate(since, [0, 3], [0.82, 1], { extrapolateRight: 'clamp' })})`, opacity: 1 }
      : {
          transform: `translateY(${interpolate(since, [0, 6], [14, 0], { extrapolateRight: 'clamp' })}px)`,
          opacity: interpolate(since, [0, 6], [0, 1], { extrapolateRight: 'clamp' }),
        };

  return (
    <div
      style={{
        position: 'absolute',
        left: 60,
        right: 60,
        top: centerY - 45,
        height: 90,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: variant === 'bold' ? 10 : 0,
        zIndex: 10,
        ...enter,
      }}
    >
      {chunk.words.map((w, i) => {
        const now = t >= w.s && t < (chunk.words[i + 1]?.s ?? chunk.to);
        if (variant === 'bold') return <BoldWord key={i} text={w.w} active={now} family={family} />;
        const state = now ? 'now' : t >= w.s ? 'said' : 'next';
        return <SentenceWord key={i} text={w.w} state={state} family={family} />;
      })}
    </div>
  );
};

export const SplitReel: React.FC<SplitReelProps> = ({ broll, face, variant, words, fulls = [], fullCaptionY }) => {
  const { fps } = useVideoConfig();
  return (
  <AbsoluteFill style={{ backgroundColor: '#000' }}>
    <div style={{ position: 'absolute', top: 0, left: 0, width: 1080, height: HALF, overflow: 'hidden' }}>
      <OffthreadVideo src={staticFile(broll)} muted style={{ width: 1080, height: HALF }} />
    </div>
    <div style={{ position: 'absolute', top: HALF, left: 0, width: 1080, height: HALF, overflow: 'hidden' }}>
      <OffthreadVideo src={staticFile(face)} style={{ width: 1080, height: HALF }} />
    </div>
    {fulls.map((f, i) => (
      <Sequence key={i} from={Math.round(f.from * fps)} durationInFrames={Math.max(1, Math.round((f.to - f.from) * fps))}>
        <AbsoluteFill style={{ zIndex: 5 }}>
          <OffthreadVideo src={staticFile(f.src)} muted style={{ width: 1080, height: 1920 }} />
        </AbsoluteFill>
      </Sequence>
    ))}
    <Captions words={words} variant={variant} fulls={fulls} fullCaptionY={fullCaptionY} />
  </AbsoluteFill>
  );
};
