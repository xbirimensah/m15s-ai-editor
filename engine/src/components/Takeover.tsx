import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { IconName, Theme } from '../spec';
import { sansStack, serifStack } from '../theme';
import { Icon } from './Icons';
import { CanvasBeat, Eyebrow, clampOpt, withAlpha } from './shared';

/**
 * Full-screen statement on brand canvas (VSL-style takeover):
 * big serif lines build up line by line (`*like this*` = accent color),
 * below that an optional sub line and an icon row. Push wipe with color wave
 * via CanvasBeat. Richer than `stat`: for the ONE big statement.
 */
export const Takeover: React.FC<{
  eyebrow?: string;
  lines: string[];
  sub?: string;
  icons?: IconName[];
  dur: number;
  theme: Theme;
}> = ({ eyebrow, lines, sub, icons, dur, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const parsed = lines.map((l) => {
    const m = /^\*(.+)\*$/.exec(l.trim());
    return { text: m ? m[1] : l, accent: Boolean(m) };
  });

  // Serif runs wider than the hook sans: ~0.52 em average character width.
  const usable = width - (is916 ? 150 : 460);
  const maxLen = Math.max(...parsed.map((p) => p.text.length), 1);
  const cap = is916 ? 110 : 96;
  const fontPx = Math.max(56, Math.min(cap, Math.floor(usable / (maxLen * 0.52))));

  const barIn = interpolate(frame, [10, 22], [0, 1], clampOpt);
  const subIn = interpolate(frame, [26, 36], [0, 1], clampOpt);

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
          gap: is916 ? 34 : 26,
          padding: is916 ? '0 75px' : '0 200px',
          textAlign: 'center',
        }}
      >
        {eyebrow ? (
          <div style={{ opacity: interpolate(frame, [4, 14], [0, 1], clampOpt) }}>
            <Eyebrow theme={theme}>{eyebrow}</Eyebrow>
          </div>
        ) : null}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {parsed.map((line, i) => {
            const at = 8 + i * 9;
            const on = spring({
              frame: frame - at,
              fps,
              config: { damping: 16, mass: 0.7 },
              durationInFrames: 15,
            });
            if (frame < at) return null;
            return (
              <div
                key={i}
                style={{
                  font: `600 ${fontPx}px ${serifStack(theme)}`,
                  fontStyle: line.accent ? 'italic' : 'normal',
                  color: line.accent ? theme.accent : theme.ink,
                  lineHeight: 1.12,
                  letterSpacing: -1,
                  opacity: on,
                  transform: `translateY(${(1 - on) * 26}px)`,
                }}
              >
                {line.text}
              </div>
            );
          })}
        </div>
        <div
          style={{
            width: 90 * barIn,
            height: 4,
            background: theme.accent,
            borderRadius: 2,
          }}
        />
        {sub ? (
          <div
            style={{
              font: `500 ${is916 ? 42 : 34}px ${sansStack(theme)}`,
              color: withAlpha(theme.ink, 0.72),
              maxWidth: is916 ? 860 : 1100,
              lineHeight: 1.3,
              opacity: subIn,
              transform: `translateY(${(1 - subIn) * 14}px)`,
            }}
          >
            {sub}
          </div>
        ) : null}
        {icons && icons.length ? (
          <div style={{ display: 'flex', gap: is916 ? 34 : 28, marginTop: is916 ? 14 : 8 }}>
            {icons.map((name, i) => {
              const at = 34 + i * 7;
              const on = spring({
                frame: frame - at,
                fps,
                config: { damping: 13, mass: 0.6 },
                durationInFrames: 14,
              });
              if (frame < at) return null;
              const size = is916 ? 96 : 80;
              return (
                <div
                  key={i}
                  style={{
                    width: size,
                    height: size,
                    borderRadius: '50%',
                    border: `2px solid ${withAlpha(theme.ink, 0.22)}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: on,
                    transform: `scale(${0.7 + 0.3 * on})`,
                  }}
                >
                  <Icon name={name} size={Math.round(size * 0.5)} color={theme.accent} strokeWidth={2} />
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </CanvasBeat>
  );
};
