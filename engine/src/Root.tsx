import React from 'react';
import { CalculateMetadataFunction, Composition } from 'remotion';
import { OverlayVideo } from './OverlayVideo';
import { SplitReel, type SplitReelProps } from './SplitReel';
import type { VideoSpec } from './spec';
import { DEFAULT_THEME } from './theme';

/**
 * Three compositions:
 *   Overlay916 — 1080×1920, 30 fps (short-form, Meta 4:5 crop-safe)
 *   Overlay169 — 1920×1080, 30 fps (long-form/VSL)
 *   SplitReel  — 1080×1920, 30 fps (split-screen reel: b-roll top, speaker bottom)
 *
 * The real props arrive at render time:
 *   npx remotion render Overlay916 out/<slug>.mp4 --props=videos/<slug>.json
 *
 * calculateMetadata reads durationInFrames and fps from the props; the values
 * below are only Studio placeholders.
 */

const splitMetadata: CalculateMetadataFunction<SplitReelProps> = ({ props }) => ({
  durationInFrames: props.durationInFrames,
  fps: props.fps,
  props,
});

const splitPlaceholder: SplitReelProps = {
  broll: 'split/example-broll.mp4',
  face: 'split/example-bottom.mp4',
  fps: 30,
  durationInFrames: 300,
  variant: 'sentence',
  words: [],
};

const calculateMetadata: CalculateMetadataFunction<VideoSpec> = ({ props }) => ({
  durationInFrames: props.durationInFrames,
  fps: props.fps,
  props,
});

/** Minimal placeholder so the Studio opens without props. */
const placeholder: VideoSpec = {
  video: 'cut/example.mp4',
  durationInFrames: 300,
  fps: 30,
  theme: DEFAULT_THEME,
  words: [],
  captions: { enabled: true },
  music: null,
  beats: [
    { type: 'hook', from: 0, dur: 75, lines: ['THIS', '*CHANGES EVERYTHING*'] },
    {
      type: 'endcard',
      from: 210,
      dur: 90,
      title: 'Creator Engine',
      sub: 'Ready',
      cta: 'Link in bio',
    },
  ],
};

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="Overlay916"
        component={OverlayVideo}
        width={1080}
        height={1920}
        fps={30}
        durationInFrames={300}
        defaultProps={placeholder}
        calculateMetadata={calculateMetadata}
      />
      <Composition
        id="Overlay169"
        component={OverlayVideo}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={300}
        defaultProps={placeholder}
        calculateMetadata={calculateMetadata}
      />
      <Composition
        id="SplitReel"
        component={SplitReel}
        width={1080}
        height={1920}
        fps={30}
        durationInFrames={300}
        defaultProps={splitPlaceholder}
        calculateMetadata={splitMetadata}
      />
    </>
  );
};
