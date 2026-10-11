import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { DiagramSide, DiagramStep, Theme } from '../spec';
import { sansStack } from '../theme';
import { Icon, IconBadge } from './Icons';
import { CanvasBeat, Eyebrow, clampOpt, paper, withAlpha } from './shared';

/**
 * Built-in diagrams as a canvas cutaway (pure SVG/CSS, theme-colored):
 *  - versus: two paper boxes with icons, verdict check mark on the
 *    winning side, the loser dims (claim vs. myth).
 *  - flow:   2–4 steps with arrows, builds step by step
 *    (explaining a mechanism).
 *  - scale:  balance scale, tips toward the verdict side (weighing options).
 * All cues (`verdictAt`, `steps[].at`) arrive beat-LOCAL (OverlayVideo
 * converts them).
 */

const FALLBACK: DiagramSide = { label: '' };

/* ------------------------------------------------------------------ */

const VersusCard: React.FC<{
  side: DiagramSide;
  theme: Theme;
  on: number;
  dimmed: number;
  winner: boolean;
  verdictOn: number;
  w: number;
  is916: boolean;
}> = ({ side, theme, on, dimmed, winner, verdictOn, w, is916 }) => {
  const pap = paper(theme);
  return (
    <div
      style={{
        position: 'relative',
        width: w,
        borderRadius: 30,
        background: pap.bg,
        boxShadow: '0 26px 60px rgba(0,0,0,0.22)',
        padding: is916 ? '46px 30px 42px' : '38px 26px 34px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: is916 ? 24 : 18,
        opacity: on * (1 - dimmed * 0.3),
        transform: `translateY(${(1 - on) * 30}px) scale(${0.92 + 0.08 * on})`,
        filter: `grayscale(${dimmed})`,
        borderTop: `6px solid ${winner ? theme.accent : theme.accent2 ?? theme.accent}`,
      }}
    >
      {side.icon ? (
        <IconBadge
          name={side.icon}
          theme={theme}
          size={is916 ? 92 : 74}
          bg={winner ? theme.accent : theme.accent2 ?? theme.accent}
        />
      ) : null}
      <div
        style={{
          font: `700 ${is916 ? 38 : 31}px ${sansStack(theme)}`,
          color: pap.ink,
          textAlign: 'center',
          lineHeight: 1.22,
        }}
      >
        {side.label}
      </div>
      {winner && verdictOn > 0 ? (
        <div
          style={{
            position: 'absolute',
            top: -26,
            right: -22,
            width: is916 ? 72 : 60,
            height: is916 ? 72 : 60,
            borderRadius: '50%',
            background: theme.accent,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 14px 34px ${withAlpha(theme.accent, 0.45)}`,
            transform: `scale(${0.6 + 0.4 * verdictOn}) rotate(${(1 - verdictOn) * -14}deg)`,
            opacity: verdictOn,
          }}
        >
          <Icon name="check" size={is916 ? 38 : 32} color="#FFFFFF" strokeWidth={2.6} />
        </div>
      ) : null}
    </div>
  );
};

const Versus: React.FC<{
  left: DiagramSide;
  right: DiagramSide;
  verdict?: 'left' | 'right';
  verdictAt: number;
  theme: Theme;
}> = ({ left, right, verdict, verdictAt, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const lOn = spring({ frame: frame - 10, fps, config: { damping: 15, mass: 0.7 }, durationInFrames: 15 });
  const rOn = spring({ frame: frame - 20, fps, config: { damping: 15, mass: 0.7 }, durationInFrames: 15 });
  const vOn = spring({ frame: frame - verdictAt, fps, config: { damping: 12, mass: 0.6 }, durationInFrames: 16 });
  const verdictOn = frame >= verdictAt ? vOn : 0;
  const dim = verdict ? interpolate(frame, [verdictAt, verdictAt + 12], [0, 1], clampOpt) : 0;

  const cardW = is916 ? 430 : 430;
  const gap = is916 ? 46 : 60;
  const vsSize = is916 ? 86 : 74;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div style={{ position: 'relative', display: 'flex', gap, alignItems: 'stretch' }}>
        <VersusCard side={left} theme={theme} on={lOn} dimmed={verdict === 'right' ? dim : 0} winner={verdict === 'left'} verdictOn={verdictOn} w={cardW} is916={is916} />
        <VersusCard side={right} theme={theme} on={rOn} dimmed={verdict === 'left' ? dim : 0} winner={verdict === 'right'} verdictOn={verdictOn} w={cardW} is916={is916} />
        {/* VS medallion centered over the seam */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            width: vsSize,
            height: vsSize,
            borderRadius: '50%',
            background: theme.ink,
            color: theme.bg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            font: `800 ${Math.round(vsSize * 0.36)}px ${sansStack(theme)}`,
            letterSpacing: 1,
            boxShadow: '0 16px 40px rgba(0,0,0,0.3)',
            transform: `translate(-50%, -50%) scale(${Math.min(1, rOn * 1.2)})`,
            opacity: Math.min(1, rOn * 1.4),
          }}
        >
          VS
        </div>
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */

const Flow: React.FC<{ steps: DiagramStep[]; theme: Theme }> = ({ steps, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;
  const pap = paper(theme);

  const shown = steps.slice(0, 4);
  const cue = (i: number): number => shown[i].at ?? 12 + i * 22;

  const card = (st: DiagramStep, i: number) => {
    const on = spring({ frame: frame - cue(i), fps, config: { damping: 15, mass: 0.7 }, durationInFrames: 15 });
    if (frame < cue(i)) return null;
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: is916 ? 24 : 18,
          width: is916 ? 720 : 380,
          borderRadius: 26,
          background: pap.bg,
          boxShadow: '0 22px 50px rgba(0,0,0,0.2)',
          padding: is916 ? '26px 32px' : '22px 26px',
          opacity: on,
          transform: `translateY(${(1 - on) * 24}px)`,
        }}
      >
        <div
          style={{
            width: is916 ? 58 : 48,
            height: is916 ? 58 : 48,
            borderRadius: '50%',
            background: withAlpha(theme.accent, 0.14),
            border: `2px solid ${theme.accent}`,
            color: theme.accent,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            font: `800 ${is916 ? 28 : 23}px ${sansStack(theme)}`,
            flexShrink: 0,
          }}
        >
          {i + 1}
        </div>
        {st.icon ? (
          <Icon name={st.icon} size={is916 ? 46 : 38} color={theme.accent} strokeWidth={2} />
        ) : null}
        <div
          style={{
            font: `700 ${is916 ? 37 : 29}px ${sansStack(theme)}`,
            color: pap.ink,
            lineHeight: 1.2,
          }}
        >
          {st.label}
        </div>
      </div>
    );
  };

  const arrow = (i: number) => {
    const at = cue(i + 1) - 6;
    const on = interpolate(frame, [at, at + 8], [0, 1], clampOpt);
    if (frame < at) return null;
    return (
      <div style={{ opacity: on, display: 'flex', justifyContent: 'center' }}>
        <Icon
          name={is916 ? 'arrow-down' : 'arrow-right'}
          size={is916 ? 46 : 40}
          color={theme.accent}
          strokeWidth={2.4}
        />
      </div>
    );
  };

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: is916 ? 'column' : 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: is916 ? 16 : 20,
      }}
    >
      {shown.map((st, i) => (
        <React.Fragment key={i}>
          {i > 0 ? arrow(i - 1) : null}
          {card(st, i)}
        </React.Fragment>
      ))}
    </div>
  );
};

/* ------------------------------------------------------------------ */

const ScalePan: React.FC<{
  side: DiagramSide;
  theme: Theme;
  on: number;
  heavy: boolean;
  tilt: number;
  is916: boolean;
}> = ({ side, theme, on, heavy, tilt, is916 }) => {
  const pap = paper(theme);
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 14,
        // Cards stay level while the beam tips:
        // the pivot is the contact point with the beam (bottom center),
        // otherwise the card floats away from the beam.
        transform: `rotate(${-tilt}deg) translateY(${(1 - on) * 24}px)`,
        transformOrigin: '50% 100%',
        opacity: on,
      }}
    >
      <div
        style={{
          borderRadius: 24,
          background: pap.bg,
          boxShadow: '0 22px 50px rgba(0,0,0,0.22)',
          padding: is916 ? '24px 28px' : '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 12,
          maxWidth: is916 ? 350 : 320,
          borderTop: `5px solid ${heavy ? theme.accent : theme.accent2 ?? theme.accent}`,
        }}
      >
        {side.icon ? (
          <IconBadge
            name={side.icon}
            theme={theme}
            size={is916 ? 72 : 60}
            bg={heavy ? theme.accent : theme.accent2 ?? theme.accent}
          />
        ) : null}
        <div
          style={{
            font: `700 ${is916 ? 31 : 26}px ${sansStack(theme)}`,
            color: pap.ink,
            textAlign: 'center',
            lineHeight: 1.22,
          }}
        >
          {side.label}
        </div>
      </div>
    </div>
  );
};

const Seesaw: React.FC<{
  left: DiagramSide;
  right: DiagramSide;
  verdict?: 'left' | 'right';
  verdictAt: number;
  theme: Theme;
}> = ({ left, right, verdict, verdictAt, theme }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const is916 = height > width;

  const lOn = spring({ frame: frame - 10, fps, config: { damping: 15, mass: 0.7 }, durationInFrames: 15 });
  const rOn = spring({ frame: frame - 20, fps, config: { damping: 15, mass: 0.7 }, durationInFrames: 15 });
  const beamOn = interpolate(frame, [2, 12], [0, 1], clampOpt);

  const tiltS = spring({ frame: frame - verdictAt, fps, config: { damping: 11, mass: 0.9 }, durationInFrames: 26 });
  const wobble = Math.sin(frame / 33) * 0.7;
  const dir = verdict === 'left' ? -1 : verdict === 'right' ? 1 : 0;
  const tilt = (frame >= verdictAt ? tiltS : 0) * dir * 7 + wobble;

  const beamW = is916 ? 820 : 900;
  const beamH = 12;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div style={{ position: 'relative', width: beamW, height: is916 ? 560 : 460 }}>
        {/* Base (triangle) */}
        <svg
          width={110}
          height={96}
          viewBox="0 0 110 96"
          style={{
            position: 'absolute',
            left: '50%',
            bottom: 0,
            transform: 'translateX(-50%)',
            opacity: beamOn,
          }}
        >
          <path d="M55 6 L104 90 L6 90 Z" fill="none" stroke={theme.ink} strokeWidth={7} strokeLinejoin="round" />
        </svg>
        {/* Tipping beam with its pans */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            bottom: 86,
            width: beamW,
            marginLeft: -beamW / 2,
            transform: `rotate(${tilt}deg)`,
            transformOrigin: '50% 100%',
          }}
        >
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: beamH,
              borderRadius: beamH,
              background: theme.ink,
              opacity: beamOn,
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: beamH + 2,
              left: -10,
              width: is916 ? 350 : 320,
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            <ScalePan side={left} theme={theme} on={lOn} heavy={verdict === 'left'} tilt={tilt} is916={is916} />
          </div>
          <div
            style={{
              position: 'absolute',
              bottom: beamH + 2,
              right: -10,
              width: is916 ? 350 : 320,
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            <ScalePan side={right} theme={theme} on={rOn} heavy={verdict === 'right'} tilt={tilt} is916={is916} />
          </div>
        </div>
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */

export const Diagram: React.FC<{
  kind: 'versus' | 'flow' | 'scale';
  title?: string;
  left?: DiagramSide;
  right?: DiagramSide;
  verdict?: 'left' | 'right';
  verdictAt?: number;
  steps?: DiagramStep[];
  dur: number;
  theme: Theme;
}> = ({ kind, title, left, right, verdict, verdictAt, steps, dur, theme }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const is916 = height > width;
  const vAt = verdictAt ?? Math.round(dur * 0.55);

  return (
    <CanvasBeat dur={dur} theme={theme}>
      {title ? (
        <div
          style={{
            position: 'absolute',
            top: is916 ? 520 : 90,
            left: 0,
            right: 0,
            opacity: interpolate(frame, [4, 14], [0, 1], clampOpt),
          }}
        >
          <Eyebrow theme={theme}>{title}</Eyebrow>
        </div>
      ) : null}
      {kind === 'versus' ? (
        <Versus left={left ?? FALLBACK} right={right ?? FALLBACK} verdict={verdict} verdictAt={vAt} theme={theme} />
      ) : null}
      {kind === 'flow' ? <Flow steps={steps ?? []} theme={theme} /> : null}
      {kind === 'scale' ? (
        <Seesaw left={left ?? FALLBACK} right={right ?? FALLBACK} verdict={verdict} verdictAt={vAt} theme={theme} />
      ) : null}
    </CanvasBeat>
  );
};
