import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Theme } from '../spec';
import { sansStack } from '../theme';
import { CanvasBeat, Eyebrow, clampOpt } from './shared';

/**
 * List builds up item by item (one cue per item, passed in beat-local).
 * onVideo=true (default): dark glass chips over the running video.
 * onVideo=false: canvas cutaway with push wipe (CanvasBeat).
 */
export const ListBuild: React.FC<{
  title?: string;
  items: string[];
  itemAt: number[];
  onVideo: boolean;
  dur: number;
  theme: Theme;
}> = ({ title, items, itemAt, onVideo, dur, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const rowH = is916 ? 116 : 96;
  const top = is916 ? (onVideo ? 560 : 430) : Math.round(height * 0.22);
  const sidePad = is916 ? 80 : Math.round(width * 0.26);

  const body = (
    <div
      style={{
        position: 'absolute',
        top,
        left: sidePad,
        right: sidePad,
        display: 'flex',
        flexDirection: 'column',
        gap: 18,
      }}
    >
      {title ? (
        <div style={{ marginBottom: 16 }}>
          <Eyebrow theme={theme} light={onVideo}>
            {title}
          </Eyebrow>
        </div>
      ) : null}
      {items.map((label, i) => {
        const at = itemAt[i] ?? i * 20;
        const on = spring({
          frame: frame - at,
          fps,
          config: { damping: 15, mass: 0.7 },
          durationInFrames: 18,
        });
        if (frame < at - 2) return <div key={i} style={{ height: rowH }} />;
        return (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 22,
              padding: '22px 30px',
              borderRadius: 22,
              background: onVideo ? 'rgba(10,10,14,0.72)' : '#FFFFFF',
              backdropFilter: onVideo ? 'blur(14px)' : undefined,
              WebkitBackdropFilter: onVideo ? 'blur(14px)' : undefined,
              border: `1.5px solid ${onVideo ? `${theme.accent}88` : `${theme.accent}44`}`,
              boxShadow: onVideo
                ? '0 14px 40px rgba(0,0,0,0.35)'
                : '0 18px 46px rgba(0,0,0,0.12)',
              opacity: on,
              transform: `translateX(${(1 - on) * -40}px)`,
            }}
          >
            <span
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                background: theme.accent,
                color: onVideo ? '#0A0A0E' : '#FFFFFF',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                font: `800 26px ${sansStack(theme)}`,
                flexShrink: 0,
              }}
            >
              ✓
            </span>
            <span
              style={{
                font: `700 ${is916 ? 40 : 34}px ${sansStack(theme)}`,
                color: onVideo ? '#FFFFFF' : theme.ink,
              }}
            >
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );

  if (onVideo) {
    const enter = interpolate(frame, [0, 8], [0, 1], clampOpt);
    const exit = interpolate(frame, [dur - 6, dur - 1], [1, 0], clampOpt);
    return <AbsoluteFill style={{ opacity: enter * exit, pointerEvents: 'none' }}>{body}</AbsoluteFill>;
  }

  return (
    <CanvasBeat dur={dur} theme={theme}>
      {body}
    </CanvasBeat>
  );
};
