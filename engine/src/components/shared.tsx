import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from 'remotion';
import type { Theme } from '../spec';
import { sansStack } from '../theme';

/**
 * Shared building blocks for all beat components.
 *
 * Aesthetic rules (binding):
 *  - Everything ENTERS (fade + ~20px translateY or scale 0.96→1, ease-out),
 *    nothing hard-cuts.
 *  - Canvas cutaways get a dark push wipe in and out.
 *  - No SFX, at most ONE hero effect per beat.
 *  - No stillness: nothing sits still for more than 2–3 s; canvas scenes
 *    breathe/drift subtly (Breathe).
 */

export const clampOpt = {
  extrapolateLeft: 'clamp' as const,
  extrapolateRight: 'clamp' as const,
};

export const easeOut = Easing.out(Easing.cubic);
export const easeIO = Easing.inOut(Easing.cubic);

/**
 * Instagram Reels UI in 9:16 space (1080x1920): menu and sound at the top; profile picture,
 * username, first caption line and audio at the bottom; like/comment/share on the right.
 * Safe-zone rule: text only inside the safe zone. Bottom 500 px = the most conservative figure in the guides.
 */
export const IG_SAFE_916 = { top: 250, bottom: 1420, side: 120 } as const;

/** Pull the top edge of a text block of height h into the safe zone. */
export const safeTop916 = (y: number, h: number): number =>
  Math.max(IG_SAFE_916.top, Math.min(y, IG_SAFE_916.bottom - h));

/** Hex → {r,g,b}; unknown formats fall back to a neutral dark. */
const hexToRgb = (hex: string): { r: number; g: number; b: number } => {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return { r: 20, g: 17, b: 24 };
  const n = parseInt(m[1], 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
};

/** Near-black derived from the theme background color (for push wipes and scrims). */
export const nearBlack = (bg: string): string => {
  const { r, g, b } = hexToRgb(bg);
  const f = 0.22;
  return `rgb(${Math.round(r * f)}, ${Math.round(g * f)}, ${Math.round(b * f)})`;
};

export const nearBlackAlpha = (bg: string, a: number): string => {
  const { r, g, b } = hexToRgb(bg);
  const f = 0.22;
  return `rgba(${Math.round(r * f)}, ${Math.round(g * f)}, ${Math.round(b * f)}, ${a})`;
};

/** Darken a color slightly (f < 1), for the subtle canvas gradient. */
export const shade = (hex: string, f: number): string => {
  const { r, g, b } = hexToRgb(hex);
  return `rgb(${Math.round(r * f)}, ${Math.round(g * f)}, ${Math.round(b * f)})`;
};

/** Hex color with alpha. */
export const withAlpha = (hex: string, a: number): string => {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
};

const luminance = (hex: string): number => {
  const { r, g, b } = hexToRgb(hex);
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
};

/** Light theme (editorial cream) or dark theme? */
export const isLightBg = (hex: string): boolean => luminance(hex) > 0.5;

/**
 * Paper surface for cards (VSL-style recipe: light card, dark ink,
 * regardless of whether the theme is light or dark). `ink` is the theme
 * ink for light themes, and for dark themes a near-black derived from bg
 * (theme.ink would be light there and unreadable on paper).
 */
export const paper = (theme: Theme): { bg: string; ink: string; mutedInk: string } => {
  const light = isLightBg(theme.bg);
  const { r, g, b } = hexToRgb(light ? theme.ink : theme.bg);
  const f = light ? 1 : 0.22;
  const R = Math.round(r * f);
  const G = Math.round(g * f);
  const B = Math.round(b * f);
  return {
    bg: 'rgba(255,255,255,0.95)',
    ink: `rgb(${R}, ${G}, ${B})`,
    mutedInk: `rgba(${R}, ${G}, ${B}, 0.6)`,
  };
};

/** Chapter label in micro-caps style. */
export const Eyebrow: React.FC<{ theme: Theme; children: React.ReactNode; light?: boolean }> = ({
  theme,
  children,
  light,
}) => (
  <div
    style={{
      font: `800 26px ${sansStack(theme)}`,
      letterSpacing: 6,
      textTransform: 'uppercase',
      color: light ? theme.accent : theme.accent2 ?? theme.accent,
      textAlign: 'center',
      textShadow: light ? '0 2px 12px rgba(0,0,0,0.6)' : 'none',
    }}
  >
    {children}
  </div>
);

/**
 * No-stillness stage: very slow push-in + micro drift with
 * incommensurable frequencies (nothing visibly loops). For canvas scenes.
 */
export const Breathe: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const f = useCurrentFrame();
  const breathe = 1.004 + Math.sin(f / 17) * 0.006 + Math.min(f * 0.00004, 0.016);
  const driftX = Math.sin(f / 29) * 5;
  const driftY = Math.cos(f / 37) * 4;
  return (
    <AbsoluteFill
      style={{ transform: `scale(${breathe}) translate(${driftX}px, ${driftY}px)` }}
    >
      {children}
    </AbsoluteFill>
  );
};

/**
 * Wrapper for full-screen canvas cutaways (stat / proof / endcard / takeover /
 * diagram / list canvas):
 *  - Entry: push wipe with a COLOR WAVE: the dark panel slides up and
 *    away, its trailing edge carries an accent stripe, so the
 *    beat boundary reads as a color wave. Content settles with fade+translateY.
 *  - Exit: the panel slides back in from below (accent edge first),
 *    then a short fade back to the video: never a hard cut.
 */
export const CanvasBeat: React.FC<{
  dur: number;
  theme: Theme;
  children: React.ReactNode;
}> = ({ dur, theme, children }) => {
  const frame = useCurrentFrame();
  const dark = nearBlack(theme.bg);

  const panelIn = interpolate(frame, [0, 10], [0, -112], { ...clampOpt, easing: easeIO });
  const settle = interpolate(frame, [4, 12], [0, 1], clampOpt);
  const panelOut = interpolate(frame, [dur - 12, dur - 4], [112, 0], {
    ...clampOpt,
    easing: easeIO,
  });
  const exitFade = interpolate(frame, [dur - 4, dur - 1], [1, 0], clampOpt);

  /** Accent stripe on the currently visible trailing edge of the wipe panel. */
  const wave = (edge: 'top' | 'bottom'): React.CSSProperties => ({
    position: 'absolute',
    left: 0,
    right: 0,
    [edge]: '-1.2%',
    height: '4.5%',
    background: theme.accent,
  });

  return (
    <AbsoluteFill style={{ opacity: exitFade }}>
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, ${theme.bg} 0%, ${shade(theme.bg, 0.86)} 100%)`,
        }}
      />
      <AbsoluteFill
        style={{ transform: `translateY(${(1 - settle) * 26}px)`, opacity: settle }}
      >
        <Breathe>{children}</Breathe>
      </AbsoluteFill>
      {/* Push wipe in: slides up, bottom edge = color wave */}
      {frame <= 12 ? (
        <AbsoluteFill style={{ background: dark, transform: `translateY(${panelIn}%)` }}>
          <div style={wave('bottom')} />
        </AbsoluteFill>
      ) : null}
      {/* Push wipe out: comes in from below, top edge = color wave */}
      {frame >= dur - 12 ? (
        <AbsoluteFill style={{ background: dark, transform: `translateY(${panelOut}%)` }}>
          <div style={wave('top')} />
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
