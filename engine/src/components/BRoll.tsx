import React from 'react';
import { AbsoluteFill, OffthreadVideo, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { clampOpt } from './shared';

/**
 * Full-screen b-roll: muted clip, plays FROM ITS START at the beat start
 * (the Sequence begins there; NEVER also wrap it in a Sequence with a
 * negative `from`, that causes the known frozen-frame bug).
 * Gentle Ken Burns on top, soft edges in/out. dur < 100 frames.
 */
export const BRoll: React.FC<{ video: string; dur: number }> = ({ video, dur }) => {
  const frame = useCurrentFrame();
  const settle = interpolate(frame, [0, 8], [0, 1], clampOpt);
  const exit = interpolate(frame, [dur - 6, dur - 1], [1, 0], clampOpt);
  const kb = interpolate(frame, [0, dur], [1.0, 1.06]);

  return (
    <AbsoluteFill style={{ opacity: settle * exit }}>
      <AbsoluteFill style={{ background: '#000', transform: `scale(${kb})` }}>
        <OffthreadVideo
          src={staticFile(video)}
          muted
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(0,0,0,0.4) 0%, transparent 28%, transparent 66%, rgba(0,0,0,0.45) 100%)',
        }}
      />
    </AbsoluteFill>
  );
};
