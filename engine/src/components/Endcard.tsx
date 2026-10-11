import React from 'react';
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { IconName, Theme } from '../spec';
import { sansStack } from '../theme';
import { IconBadge } from './Icons';
import { CanvasBeat, Eyebrow } from './shared';

/**
 * Closing card on brand canvas: optional icon badge, sub line (eyebrow),
 * title, CTA bar in the accent color. Push wipe in, stays until the end.
 */
export const Endcard: React.FC<{
  title: string;
  sub?: string;
  cta: string;
  icon?: IconName;
  dur: number;
  theme: Theme;
}> = ({ title, sub, cta, icon, dur, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const t = spring({ frame: frame - 8, fps, config: { damping: 200 }, durationInFrames: 18 });
  const bar = spring({
    frame: frame - 24,
    fps,
    config: { damping: 14, mass: 0.7 },
    durationInFrames: 20,
  });

  const titleTop = is916 ? 640 : Math.round(height * 0.32);
  const barTop = is916 ? 980 : Math.round(height * 0.58);
  const barInset = is916 ? 120 : Math.round(width * 0.28);
  const titlePx = Math.min(is916 ? 104 : 96, Math.floor((width - 160) / (Math.max(title.length, 1) * 0.55)));

  return (
    <CanvasBeat dur={dur} theme={theme}>
      <div
        style={{
          position: 'absolute',
          top: titleTop,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: t,
          transform: `translateY(${(1 - t) * 20}px)`,
        }}
      >
        {icon ? (
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 26 }}>
            <IconBadge name={icon} theme={theme} size={is916 ? 104 : 88} />
          </div>
        ) : null}
        {sub ? <Eyebrow theme={theme}>{sub}</Eyebrow> : null}
        <div
          style={{
            font: `900 ${titlePx}px ${sansStack(theme)}`,
            color: theme.ink,
            letterSpacing: -2,
            marginTop: 16,
            padding: '0 60px',
          }}
        >
          {title}
        </div>
      </div>
      <div
        style={{
          position: 'absolute',
          left: barInset,
          right: barInset,
          top: barTop,
          height: 132,
          borderRadius: 999,
          background: theme.accent,
          boxShadow: `0 22px 60px ${theme.accent}55`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: bar,
          transform: `translateY(${(1 - bar) * 24}px)`,
        }}
      >
        <span style={{ font: `800 ${is916 ? 50 : 44}px ${sansStack(theme)}`, color: '#111318', padding: '0 40px', whiteSpace: 'nowrap' }}>
          {cta}
        </span>
      </div>
    </CanvasBeat>
  );
};
