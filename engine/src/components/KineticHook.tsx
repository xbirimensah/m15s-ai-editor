import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Theme } from '../spec';
import { sansStack } from '../theme';
import { clampOpt, easeOut } from './shared';

/**
 * Kinetic hook: lines slam in on fixed early beats over the running
 * video (INSTANT motion: the hook must never "just sit there").
 * Lines written as `*like this*` are set in the accent color.
 * Adaptive font size: the LONGEST line sets the font size so nothing
 * runs out of the frame (sans 900 uppercase ≈ 0.6 em average character width).
 */
export const KineticHook: React.FC<{ lines: string[]; dur: number; theme: Theme }> = ({
  lines,
  dur,
  theme,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const exit = interpolate(frame, [dur - 6, dur - 1], [1, 0], clampOpt);
  const bar = interpolate(frame, [4, 16], [0, 1], { ...clampOpt, easing: easeOut });

  const parsed = lines.map((l) => {
    const m = /^\*(.+)\*$/.exec(l.trim());
    return { text: m ? m[1] : l, accent: Boolean(m) };
  });

  const usable = width - (is916 ? 100 : 400);
  const maxLen = Math.max(...parsed.map((p) => p.text.length), 1);
  const cap = is916 ? 148 : 120;
  const fontPx = Math.max(64, Math.min(cap, Math.floor(usable / (maxLen * 0.6))));

  const top = is916 ? 430 : Math.round(height * 0.3);

  return (
    <AbsoluteFill style={{ opacity: exit, pointerEvents: 'none' }}>
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.38) 30%, transparent 48%, transparent 62%, rgba(0,0,0,0.5) 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top,
          left: 50,
          right: 50,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
          textAlign: 'center',
        }}
      >
        {parsed.map((line, i) => {
          const at = 6 + i * 15;
          const on = spring({
            frame: frame - at,
            fps,
            config: { damping: 12, mass: 0.55 },
            durationInFrames: 13,
          });
          if (frame < at) return null;
          return (
            <span
              key={i}
              style={{
                font: `900 ${fontPx}px ${sansStack(theme)}`,
                letterSpacing: -3,
                lineHeight: 0.98,
                textTransform: 'uppercase',
                whiteSpace: 'nowrap',
                color: line.accent ? theme.accent : '#FFFFFF',
                textShadow: '0 8px 34px rgba(0,0,0,0.8)',
                transform: `scale(${interpolate(on, [0, 1], [0.5, 1])}) translateY(${(1 - on) * 30}px)`,
                opacity: on,
                display: 'inline-block',
              }}
            >
              {line.text}
            </span>
          );
        })}
      </div>
      {/* Accent bar under the block: the one hero effect of this beat */}
      <div
        style={{
          position: 'absolute',
          top: top + fontPx * parsed.length + 44,
          left: '50%',
          width: 320 * bar,
          height: 8,
          marginLeft: -160 * bar,
          background: theme.accent,
          borderRadius: 4,
          boxShadow: `0 0 24px ${theme.accent}`,
        }}
      />
    </AbsoluteFill>
  );
};
