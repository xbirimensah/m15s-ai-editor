import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Theme } from '../spec';
import { sansStack } from '../theme';
import { clampOpt } from './shared';

/**
 * Persistent chapter label (VSL-style eyebrow as a pill): micro-caps in a
 * glass pill, stays up for a whole chapter. The matching punch-in on the
 * video happens in OverlayVideo (VideoLayer). During full-screen cutaways
 * the pill fades out (`mask` = beat-local windows of the cover beats)
 * so it doesn't float over unrelated canvas scenes.
 */
export const Kicker: React.FC<{
  text: string;
  align: 'left' | 'center';
  dur: number;
  theme: Theme;
  mask: [number, number][];
}> = ({ text, align, dur, theme, mask }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const on = spring({ frame, fps, config: { damping: 15, mass: 0.6 }, durationInFrames: 14 });
  const exit = interpolate(frame, [dur - 8, dur - 1], [1, 0], clampOpt);

  // Fade out softly while a cover beat runs (±6 frame ramp).
  let cover = 1;
  for (const [a, b] of mask) {
    const inRamp = interpolate(frame, [a - 6, a], [1, 0], clampOpt);
    const outRamp = interpolate(frame, [b, b + 6], [0, 1], clampOpt);
    if (frame >= a - 6 && frame <= b + 6) cover = Math.min(cover, Math.min(1, inRamp + outRamp));
  }

  const top = is916 ? 300 : 54;
  const alignStyle: React.CSSProperties =
    align === 'left'
      ? { left: is916 ? 70 : 72, justifyContent: 'flex-start' }
      : { left: 0, right: 0, justifyContent: 'center' };

  return (
    <AbsoluteFill style={{ pointerEvents: 'none', opacity: on * exit * cover }}>
      <div style={{ position: 'absolute', top, display: 'flex', ...alignStyle }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            background: 'rgba(10,10,14,0.62)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            border: `1.5px solid ${theme.accent}66`,
            borderRadius: 999,
            padding: is916 ? '13px 28px' : '11px 24px',
            boxShadow: '0 12px 34px rgba(0,0,0,0.35)',
            transform: `translateY(${(1 - on) * -18}px)`,
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: theme.accent,
              boxShadow: `0 0 12px ${theme.accent}`,
            }}
          />
          <span
            style={{
              font: `800 ${is916 ? 27 : 23}px ${sansStack(theme)}`,
              letterSpacing: 4.5,
              textTransform: 'uppercase',
              color: '#FFFFFF',
              whiteSpace: 'nowrap',
            }}
          >
            {text}
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
