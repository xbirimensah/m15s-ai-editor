import React from 'react';
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Theme } from '../spec';
import { CanvasBeat, Eyebrow, clampOpt } from './shared';

/**
 * Canvas cutaway that cycles through proof images (screenshots, results, quotes),
 * each image with its own gentle Ken Burns push.
 */
export const ProofCycle: React.FC<{
  images: string[];
  title?: string;
  dur: number;
  theme: Theme;
}> = ({ images, title, dur, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const inn = spring({
    frame: frame - 8,
    fps,
    config: { damping: 15, mass: 0.9 },
    durationInFrames: 26,
  });

  const imgs = images.length ? images : [];
  const seg = imgs.length ? dur / imgs.length : dur;

  const frameBox: React.CSSProperties = is916
    ? { top: 430, left: 90, right: 90, bottom: 440 }
    : { top: 150, left: Math.round(width * 0.24), right: Math.round(width * 0.24), bottom: 170 };

  return (
    <CanvasBeat dur={dur} theme={theme}>
      {title ? (
        <div style={{ position: 'absolute', top: is916 ? 320 : 70, left: 0, right: 0 }}>
          <Eyebrow theme={theme}>{title}</Eyebrow>
        </div>
      ) : null}
      <div
        style={{
          position: 'absolute',
          ...frameBox,
          borderRadius: 32,
          overflow: 'hidden',
          border: '10px solid #FFFFFF',
          background: '#FFFFFF',
          boxShadow: '0 40px 90px rgba(0,0,0,0.28)',
          transform: `scale(${interpolate(inn, [0, 1], [0.9, 1])}) rotate(${(1 - inn) * -2}deg)`,
          opacity: inn,
        }}
      >
        {imgs.map((img, k) => {
          const start = k * seg;
          const op =
            k === 0
              ? interpolate(frame, [0, 6], [0, 1], clampOpt)
              : interpolate(frame, [start - 6, start + 6], [0, 1], clampOpt);
          const kb = interpolate(frame, [start, start + seg], [1.04, 1.1], clampOpt);
          return (
            <Img
              key={k}
              src={staticFile(img)}
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                transform: `scale(${kb})`,
                opacity: op,
              }}
            />
          );
        })}
      </div>
      {is916 ? (
        <div
          style={{
            position: 'absolute',
            bottom: 300,
            left: 0,
            right: 0,
            textAlign: 'center',
            opacity: interpolate(frame, [18, 28], [0, 1], clampOpt),
          }}
        >
          <div style={{ width: 90, height: 4, background: theme.accent, borderRadius: 2, margin: '0 auto' }} />
        </div>
      ) : null}
    </CanvasBeat>
  );
};
