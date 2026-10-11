import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { IconName, PanelRow, Theme } from '../spec';
import { sansStack, serifStack } from '../theme';
import { Icon, IconBadge } from './Icons';
import { clampOpt, paper, withAlpha } from './shared';

/**
 * THE workhorse (VSL-style side panel, vertical-first): light paper card
 * over the running video. Optional icon badge + eyebrow + serif title,
 * below that rows that build up word cue by word cue (each row with
 * its own icon: check, x, arrow-right …).
 *
 * 9:16: card in the upper or lower third (Meta 4:5 safe, does not collide
 * with captions at y 1010). 16:9: side panel left/right.
 * Entry: slides in from the side (spring, ~0.4 s), exit: fade + slide.
 */
export const Panel: React.FC<{
  position: 'top' | 'bottom';
  side: 'left' | 'right';
  icon?: IconName;
  eyebrow?: string;
  title?: string;
  rows: PanelRow[];
  dur: number;
  theme: Theme;
}> = ({ position, side, icon, eyebrow, title, rows, dur, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;
  const pap = paper(theme);

  const on = spring({ frame, fps, config: { damping: 15, mass: 0.75 }, durationInFrames: 14 });
  const exit = interpolate(frame, [dur - 8, dur - 1], [1, 0], clampOpt);
  const slideX = (1 - on) * (side === 'right' ? 90 : -90);
  const drift = Math.sin(frame / 41) * 3;

  const rowIconColor = (name?: IconName): string => {
    if (name === 'x' || name === 'warning') return theme.accent2 ?? theme.accent;
    return theme.accent;
  };

  const box: React.CSSProperties = is916
    ? position === 'bottom'
      ? { left: 70, right: 70, bottom: 1920 - 1615 }
      : { left: 70, right: 70, top: 430 }
    : { [side]: 72, top: '50%', width: 560, transform: 'translateY(-50%)' };

  const rowFont = is916 ? 37 : 30;
  const titleFont = is916 ? 56 : 44;

  return (
    <AbsoluteFill style={{ pointerEvents: 'none', opacity: exit }}>
      <div
        style={{
          position: 'absolute',
          ...box,
          transform: `${(box.transform as string | undefined) ?? ''} translateX(${slideX}px) translateY(${drift}px)`,
          opacity: on,
        }}
      >
        <div
          style={{
            background: pap.bg,
            borderRadius: 32,
            boxShadow: '0 30px 70px rgba(0,0,0,0.28)',
            padding: is916 ? '36px 42px 34px' : '30px 34px 28px',
            display: 'flex',
            flexDirection: 'column',
            gap: is916 ? 20 : 16,
            borderTop: `6px solid ${theme.accent}`,
          }}
        >
          {(icon || eyebrow || title) && (
            <div style={{ display: 'flex', alignItems: 'center', gap: is916 ? 24 : 18 }}>
              {icon ? <IconBadge name={icon} theme={theme} size={is916 ? 76 : 60} /> : null}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
                {eyebrow ? (
                  <div
                    style={{
                      font: `800 ${is916 ? 23 : 19}px ${sansStack(theme)}`,
                      letterSpacing: 4,
                      textTransform: 'uppercase',
                      color: theme.accent2 ?? theme.accent,
                    }}
                  >
                    {eyebrow}
                  </div>
                ) : null}
                {title ? (
                  <div
                    style={{
                      font: `600 ${titleFont}px ${serifStack(theme)}`,
                      color: pap.ink,
                      lineHeight: 1.08,
                      letterSpacing: -0.5,
                    }}
                  >
                    {title}
                  </div>
                ) : null}
              </div>
            </div>
          )}
          {rows.length > 0 && (icon || eyebrow || title) ? (
            <div style={{ height: 1.5, background: withAlpha(theme.accent, 0.25) }} />
          ) : null}
          {rows.map((row, i) => {
            const at = row.at;
            const rs = spring({
              frame: frame - at,
              fps,
              config: { damping: 15, mass: 0.65 },
              durationInFrames: 13,
            });
            if (frame < at) return null;
            return (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: is916 ? 20 : 16,
                  opacity: rs,
                  transform: `translateY(${(1 - rs) * 16}px)`,
                }}
              >
                {row.icon ? (
                  <Icon
                    name={row.icon}
                    size={is916 ? 40 : 32}
                    color={rowIconColor(row.icon)}
                    strokeWidth={2.2}
                  />
                ) : (
                  <span
                    style={{
                      width: 11,
                      height: 11,
                      borderRadius: '50%',
                      background: theme.accent,
                      flexShrink: 0,
                      marginLeft: is916 ? 14 : 10,
                      marginRight: is916 ? 15 : 11,
                    }}
                  />
                )}
                <span
                  style={{
                    font: `600 ${rowFont}px ${sansStack(theme)}`,
                    color: pap.ink,
                    lineHeight: 1.22,
                  }}
                >
                  {row.text}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
