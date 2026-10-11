import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Theme } from '../spec';
import { sansStack } from '../theme';
import { clampOpt, paper } from './shared';

/**
 * Lower-third name tag: light pill with name · accent
 * dot · credential line, slides in from the side and back out.
 * For intro moments ("who is talking"). No punch, no caption mask.
 * 9:16: below the captions, still inside the Meta 4:5 window (y ≤ 1635).
 */
export const NameTag: React.FC<{
  name: string;
  sub?: string;
  side: 'left' | 'right';
  dur: number;
  theme: Theme;
}> = ({ name, sub, side, dur, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;
  const pap = paper(theme);

  const on = spring({ frame, fps, config: { damping: 15, mass: 0.7 }, durationInFrames: 15 });
  const exit = interpolate(frame, [dur - 9, dur - 1], [1, 0], clampOpt);
  const slide = (1 - on) * (side === 'left' ? -60 : 60);

  const pos: React.CSSProperties = is916
    ? { top: 1330, [side]: 70 }
    : { bottom: 200, [side]: 72 };

  return (
    <AbsoluteFill style={{ pointerEvents: 'none', opacity: exit }}>
      <div
        style={{
          position: 'absolute',
          ...pos,
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          background: pap.bg,
          borderRadius: 999,
          padding: is916 ? '16px 30px' : '14px 26px',
          boxShadow: '0 18px 44px rgba(0,0,0,0.3)',
          borderLeft: `6px solid ${theme.accent}`,
          opacity: on,
          transform: `translateX(${slide}px) scale(${0.94 + 0.06 * on})`,
        }}
      >
        <span style={{ font: `700 ${is916 ? 34 : 28}px ${sansStack(theme)}`, color: pap.ink }}>
          {name}
        </span>
        {sub ? (
          <>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: theme.accent,
                flexShrink: 0,
              }}
            />
            <span
              style={{
                font: `500 ${is916 ? 28 : 24}px ${sansStack(theme)}`,
                color: pap.mutedInk,
                whiteSpace: 'nowrap',
              }}
            >
              {sub}
            </span>
          </>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
