import React, { useMemo } from 'react';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Theme, Word } from '../spec';
import { sansStack, serifStack } from '../theme';
import { clampOpt, IG_SAFE_916, nearBlackAlpha, safeTop916 } from './shared';

/**
 * Karaoke word captions:
 *  - Chunking at punctuation (.!?: always; comma from 4 words on), with a hard
 *    character cap per font, so every chunk is ALWAYS ONE line
 *    (plus nowrap as a safeguard).
 *  - Each word lights up exactly at the moment it is spoken; the word currently
 *    being spoken is shown in theme.capActive.
 *  - Never two chunks at once: a chunk disappears strictly before the
 *    next one fades in.
 *
 * Position: 9:16 → y 1010 (Meta 4:5 crop-safe, core zone y285–1635), always pulled into the
 * Instagram safe zone (IG_SAFE_916: not into the username/caption at the bottom, not
 * under the buttons on the right); 16:9 → lower third (bottom-anchored).
 */
/** Max. characters per chunk = one line at 56 px in 840 px width (1080 - 2 x safe margin). */
const MAX_CHARS = { serif: 34, sans: 26 } as const;
/** Height of one caption line including its shadow, for the safe-zone clamp. */
const LINE_PX = 80;

type Chunk = { words: Word[]; from: number; to: number };

export const Captions: React.FC<{
  words: Word[];
  theme: Theme;
  y?: number;
  font?: 'serif' | 'sans';
  /** No background: text with a shadow only. */
  plain?: boolean;
  activeColor?: string;
  audioOffsetFrames: number;
  mask: [number, number][];
}> = ({ words, theme, y, font = 'serif', plain = false, activeColor, audioOffsetFrames, mask }) => {
  const maxChars = MAX_CHARS[font];
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const chunks = useMemo<Chunk[]>(() => {
    const out: Chunk[] = [];
    let cur: Word[] = [];
    const push = () => {
      if (!cur.length) return;
      out.push({ words: cur, from: cur[0].s, to: cur[cur.length - 1].e });
      cur = [];
    };
    const lengthOf = (ws: Word[]) => ws.reduce((n, w) => n + w.w.length + 1, -1);
    for (const w of words) {
      if (cur.length && lengthOf(cur) + 1 + w.w.length > maxChars) push();
      cur.push(w);
      if (/[.!?:]$/.test(w.w) || (/[,]$/.test(w.w) && cur.length >= 4)) push();
    }
    push();
    return out;
  }, [words, maxChars]);

  // No captions during canvas/hook beats (the scene carries the text).
  if (mask.some(([a, b]) => frame >= a && frame <= b)) return null;

  const t = (frame - audioOffsetFrames) / fps;

  const boxStyle: React.CSSProperties = is916
    ? {
        top: safeTop916(y ?? 1010, LINE_PX),
        left: IG_SAFE_916.side,
        right: IG_SAFE_916.side,
        height: 190,
        alignItems: 'flex-start',
      }
    : { bottom: 44, left: 200, right: 200, height: 140, alignItems: 'flex-end' };

  const fontPx = is916 ? 56 : 44;

  return (
    <div
      style={{
        position: 'absolute',
        display: 'flex',
        justifyContent: 'center',
        pointerEvents: 'none',
        zIndex: 40,
        ...boxStyle,
      }}
    >
      {chunks.map((c, i) => {
        const isLast = i === chunks.length - 1;
        const inT = c.from - 0.16;
        // Last chunk: don't leave it up forever (the VO can end before the video).
        const outT = isLast ? c.to + 1.2 : Math.min(c.to + 0.22, chunks[i + 1].from - 0.2);
        if (t < inT || t > outT) return null;
        const chunkIn = interpolate(t, [inT, inT + 0.2], [0, 1], clampOpt);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              ...(is916 ? {} : { bottom: 0 }),
              maxWidth: is916 ? 920 : 1340,
              textAlign: 'center',
              font:
                font === 'sans'
                  ? `600 ${fontPx}px ${sansStack(theme)}`
                  : `italic 500 ${fontPx}px ${serifStack(theme)}`,
              whiteSpace: 'nowrap',
              color: '#FDFBF9',
              lineHeight: 1.24,
              opacity: chunkIn,
              transform: `translateY(${(1 - chunkIn) * 10}px)`,
              textShadow: plain
                ? '0 2px 4px rgba(0,0,0,0.9), 0 4px 18px rgba(0,0,0,0.75)'
                : '0 2px 10px rgba(0,0,0,0.85), 0 8px 34px rgba(0,0,0,0.6)',
              ...(plain
                ? { padding: '8px 0' }
                : {
                    background: nearBlackAlpha(theme.bg, 0.68),
                    backdropFilter: 'blur(10px)',
                    WebkitBackdropFilter: 'blur(10px)',
                    borderRadius: 20,
                    padding: '8px 24px',
                  }),
            }}
          >
            {c.words.map((w, j) => {
              const lit = plain ? 1 : interpolate(t, [w.s - 0.06, w.s + 0.14], [0.5, 1], clampOpt);
              const active = t >= w.s - 0.02 && t <= w.e + 0.06;
              return (
                <span
                  key={j}
                  style={{ opacity: lit, color: active ? (activeColor ?? theme.capActive) : undefined }}
                >
                  {w.w}
                  {j < c.words.length - 1 ? ' ' : ''}
                </span>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};
