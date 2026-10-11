import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { IconName, Theme } from '../spec';
import { sansStack } from '../theme';
import { Icon } from './Icons';
import { clampOpt } from './shared';

/** How long a single pill stays visible (frames). */
const SHOW = 70;

/**
 * Cue-synced keyword pills over the running video. Each pill appears
 * on its (beat-local) frame, holds briefly and leaves again; the video keeps
 * running undisturbed.
 */
export const Chips: React.FC<{
  items: { text: string; at: number; icon?: IconName }[];
  dur: number;
  theme: Theme;
}> = ({ items, dur, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;
  const top = is916 ? 430 : Math.round(height * 0.18);

  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      {items.map((item, i) => {
        const local = frame - item.at;
        // Visibility window: until the next cue, at most SHOW, never past the beat end.
        const next = items[i + 1] ? items[i + 1].at - item.at - 4 : SHOW;
        const window = Math.min(SHOW, Math.max(20, next), dur - item.at - 2);
        if (local < 0 || local > window) return null;
        const on = spring({
          frame: local,
          fps,
          config: { damping: 13, mass: 0.6 },
          durationInFrames: 14,
        });
        const exit = interpolate(local, [window - 8, window], [1, 0], clampOpt);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              top,
              left: 0,
              right: 0,
              display: 'flex',
              justifyContent: 'center',
              opacity: on * exit,
              transform: `translateY(${(1 - on) * -22}px) scale(${interpolate(on, [0, 1], [0.85, 1])})`,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                background: 'rgba(10,10,14,0.78)',
                backdropFilter: 'blur(14px)',
                WebkitBackdropFilter: 'blur(14px)',
                border: `1.5px solid ${theme.accent}88`,
                borderRadius: 999,
                padding: '16px 30px',
                boxShadow: '0 16px 44px rgba(0,0,0,0.4)',
              }}
            >
              {item.icon ? (
                <Icon
                  name={item.icon}
                  size={is916 ? 42 : 36}
                  color={theme.accent}
                  strokeWidth={2.2}
                />
              ) : (
                <span
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    background: theme.accent,
                    boxShadow: `0 0 14px ${theme.accent}`,
                  }}
                />
              )}
              <span
                style={{
                  font: `800 ${is916 ? 40 : 34}px ${sansStack(theme)}`,
                  color: '#FFFFFF',
                  letterSpacing: 0.5,
                  whiteSpace: 'nowrap',
                }}
              >
                {item.text}
              </span>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
