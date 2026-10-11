import React from 'react';
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Theme } from '../spec';
import { sansStack } from '../theme';
import { clampOpt } from './shared';

/**
 * Photo card (person/proof) floats at the side over the video, with a gentle
 * drift (no stillness). Images live in public/, path relative to it.
 * Rule: person photo only when the person is named + the user supplied the asset.
 */
export const ImageCard: React.FC<{
  image: string;
  name: string;
  sub?: string;
  side: 'left' | 'right';
  dur: number;
  theme: Theme;
}> = ({ image, name, sub, side, dur, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const on = spring({ frame, fps, config: { damping: 14, mass: 0.8 }, durationInFrames: 20 });
  const exit = interpolate(frame, [dur - 8, dur - 1], [1, 0], clampOpt);
  const drift = Math.sin(frame / 34) * 6;
  const x0 = side === 'right' ? 120 : -120;
  const cardW = is916 ? 340 : 300;
  const top = is916 ? 400 : Math.round(height * 0.18);
  const inset = is916 ? 70 : 90;

  const posStyle: React.CSSProperties =
    side === 'right' ? { right: inset } : { left: inset };

  return (
    <AbsoluteFill style={{ pointerEvents: 'none', opacity: exit }}>
      <div
        style={{
          position: 'absolute',
          top: top + drift,
          ...posStyle,
          transform: `translateX(${(1 - on) * x0}px) rotate(${(1 - on) * (side === 'right' ? 5 : -5)}deg) scale(${interpolate(on, [0, 1], [0.85, 1])})`,
          opacity: on,
        }}
      >
        <div
          style={{
            width: cardW,
            borderRadius: 26,
            overflow: 'hidden',
            background: '#FFFFFF',
            boxShadow: '0 30px 80px rgba(0,0,0,0.5)',
            border: '1px solid rgba(255,255,255,0.6)',
          }}
        >
          <Img
            src={staticFile(image)}
            style={{ width: cardW, height: cardW, objectFit: 'cover', display: 'block' }}
          />
          <div style={{ padding: '14px 18px 16px', display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ font: `800 30px ${sansStack(theme)}`, color: '#111318', letterSpacing: -0.5 }}>
              {name}
            </div>
            {sub ? (
              <div
                style={{
                  font: `700 21px ${sansStack(theme)}`,
                  color: theme.accent2 ?? theme.accent,
                  letterSpacing: 0.5,
                }}
              >
                {sub}
              </div>
            ) : null}
          </div>
        </div>
        {/* Accent dot: ties the card to the brand identity */}
        <div
          style={{
            position: 'absolute',
            top: -10,
            ...(side === 'right' ? { left: -10 } : { right: -10 }),
            width: 26,
            height: 26,
            borderRadius: '50%',
            background: theme.accent,
            boxShadow: `0 0 20px ${theme.accent}`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
