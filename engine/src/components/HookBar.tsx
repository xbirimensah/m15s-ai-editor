import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Theme } from '../spec';
import { sansStack } from '../theme';
import { clampOpt, easeOut, IG_SAFE_916, safeTop916 } from './shared';

/**
 * Hook bar: the text hook in the first frame (reel rule "text hook in the first frame").
 * White bar, black text, over the running video. Stands from frame 0 (no
 * fade-in, the first frame carries the hook), fades out at the end in ~0.25 s.
 * Text in the speaker's own words. Max. 2 lines; the font size adapts.
 */
export const HookBar: React.FC<{ text: string; dur: number; theme: Theme; y?: number }> = ({
  text,
  dur,
  theme,
  y,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const outFrames = Math.round(0.25 * fps);
  const exit = interpolate(frame, [dur - outFrames, dur - 1], [1, 0], { ...clampOpt, easing: easeOut });

  const maxWidth = is916 ? width - 2 * IG_SAFE_916.side : 1400;
  const maxFont = is916 ? 76 : 64;
  // Sans 800 ≈ 0.55 em average character width. If the text doesn't fit on one line, split it
  // into two balanced lines (otherwise the browser breaks long words onto a third line).
  const words = text.split(' ');
  let lines = [text];
  if (text.length * 0.55 * maxFont > maxWidth - 72) {
    for (let i = 1; i < words.length; i++) {
      const pair = [words.slice(0, i).join(' '), words.slice(i).join(' ')];
      if (lines.length === 1 || Math.max(...pair.map((l) => l.length)) < Math.max(...lines.map((l) => l.length))) {
        lines = pair;
      }
    }
  }
  const perLine = Math.max(...lines.map((l) => l.length));
  const fontPx = Math.max(52, Math.min(maxFont, Math.floor((maxWidth - 72) / (perLine * 0.55))));
  const barH = Math.ceil(2 * fontPx * 1.16 + 2 * fontPx * 0.32);
  const top = is916 ? safeTop916(y ?? 880, barH) : y ?? Math.round(height * 0.12);

  return (
    <AbsoluteFill style={{ pointerEvents: 'none', zIndex: 45 }}>
      <div
        style={{
          position: 'absolute',
          top,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          opacity: exit,
        }}
      >
        <div
          style={{
            maxWidth,
            background: '#FFFFFF',
            color: '#0B0B0C',
            font: `800 ${fontPx}px ${sansStack(theme)}`,
            lineHeight: 1.16,
            letterSpacing: '-0.01em',
            textAlign: 'center',
            padding: `${Math.round(fontPx * 0.32)}px ${Math.round(fontPx * 0.5)}px`,
            borderRadius: Math.round(fontPx * 0.28),
            boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
          }}
        >
          {lines.map((l, i) => (
            <div key={i} style={{ whiteSpace: 'nowrap' }}>
              {l}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
