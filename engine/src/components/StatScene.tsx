import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Theme } from '../spec';
import { sansStack, serifStack } from '../theme';
import { CanvasBeat, Eyebrow, clampOpt } from './shared';

/**
 * Full-screen cutaway: big number on brand canvas. Numeric values count up
 * (a suffix like "%" or "+" stays put), otherwise a scale entrance.
 */
export const StatScene: React.FC<{
  value: string;
  label: string;
  sub?: string;
  dur: number;
  theme: Theme;
  locale?: string;
}> = ({ value, label, sub, dur, theme, locale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const inn = spring({
    frame: frame - 8,
    fps,
    config: { damping: 16, mass: 0.8 },
    durationInFrames: 22,
  });

  // Count-up when the value starts with a number ("82%", "2000+", "12").
  const m = /^(\d[\d.]*)(.*)$/.exec(value.trim());
  let shown = value;
  if (m) {
    const target = parseInt(m[1].replace(/\./g, ''), 10);
    if (!Number.isNaN(target)) {
      const n = Math.round(Math.min(1, inn) * target);
      shown = n.toLocaleString(locale ?? 'en-US') + m[2];
    }
  }

  const fontPx = shown.length <= 4 ? 300 : shown.length <= 6 ? 210 : 150;

  return (
    <CanvasBeat dur={dur} theme={theme}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 26,
          padding: '0 80px',
        }}
      >
        <Eyebrow theme={theme}>{label}</Eyebrow>
        <div
          style={{
            font: `900 ${fontPx}px ${sansStack(theme)}`,
            color: theme.ink,
            letterSpacing: -4,
            lineHeight: 0.9,
            textAlign: 'center',
            transform: `scale(${interpolate(inn, [0, 1], [0.8, 1])})`,
            opacity: inn,
          }}
        >
          {shown}
        </div>
        <div
          style={{
            width: 90,
            height: 4,
            background: theme.accent,
            borderRadius: 2,
            transform: `scaleX(${inn})`,
          }}
        />
        {sub ? (
          <div
            style={{
              font: `italic 800 48px ${serifStack(theme)}`,
              color: theme.ink,
              textAlign: 'center',
              maxWidth: 860,
              opacity: interpolate(frame, [16, 26], [0, 1], clampOpt),
            }}
          >
            {sub}
          </div>
        ) : null}
      </div>
    </CanvasBeat>
  );
};
