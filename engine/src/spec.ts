/**
 * Video spec of the Creator Engine.
 *
 * One video = ONE continuous cut (never re-cut) + purely visual
 * beats that sit on top of it as Sequences (VSL-style overlay pattern).
 *
 * TIME UNITS (do not mix them up):
 *  - `Word.s` / `Word.e`:  SECONDS, absolute on the cut (from transcribe.py).
 *  - `Beat.from` / `Beat.dur` and all cues (`itemAt`, `items[].at`,
 *    `rows[].at`, `steps[].at`, `verdictAt`):
 *    FRAMES, absolute on the composition (frame = second × fps).
 *    Cue frames are converted to beat-local internally; always give them
 *    as absolute in the spec: `Math.round(word.s * fps)`.
 */

/** A transcribed word. Seconds, absolute on the cut. */
export type Word = { w: string; s: number; e: number };

/**
 * Built-in icon library (src/components/Icons.tsx). Beats reference
 * icons by name; the planner picks what fits the context (leaf for plant-based,
 * shield for safety, warning for myths, etc.).
 */
export type IconName =
  | 'check'
  | 'x'
  | 'arrow-up'
  | 'arrow-down'
  | 'arrow-right'
  | 'leaf'
  | 'heart'
  | 'drop'
  | 'flame'
  | 'bolt'
  | 'shield'
  | 'warning'
  | 'sparkle'
  | 'star'
  | 'clock'
  | 'calendar'
  | 'scale'
  | 'brain'
  | 'gut'
  | 'muscle'
  | 'pill'
  | 'bowl'
  | 'money'
  | 'chart-up'
  | 'chat'
  | 'search'
  | 'lock';

/** Kinetic word slam over the video. Instant motion, never static.
 *  Lines written as `*like this*` are set in the accent color. */
export type HookBeat = { type: 'hook'; from: number; dur: number; lines: string[] };
/** White text bar with the hook, from frame 0 for the first 3 seconds (dur = 3 × fps)
 *  (reel rule: text hook in the first frame). */
export type HookBarBeat = { type: 'hookbar'; from: number; dur: number; text: string; y?: number };

/** Full-screen cutaway on canvas: big number + label (+ source/sub line). */
export type StatBeat = {
  type: 'stat';
  from: number;
  dur: number;
  value: string;
  label: string;
  sub?: string;
};

/** List builds up point by point (itemAt = absolute frames per item).
 *  onVideo=true (default): glass chips over the running video.
 *  onVideo=false: canvas cutaway with push wipe. */
export type ListBeat = {
  type: 'list';
  from: number;
  dur: number;
  title?: string;
  items: string[];
  itemAt: number[];
  onVideo?: boolean;
};

/** Cue-synced keyword pills over the video (each pill visible briefly).
 *  An optional icon replaces the pill's accent dot. */
export type ChipsBeat = {
  type: 'chips';
  from: number;
  dur: number;
  items: { text: string; at: number; icon?: IconName }[];
};

/** Photo card (person/proof) floats at the side over the video.
 *  Rule: person photo only when the person is named + an asset exists. */
export type ImageCardBeat = {
  type: 'imagecard';
  from: number;
  dur: number;
  image: string;
  name: string;
  sub?: string;
  side?: 'left' | 'right';
};

/** Canvas cutaway that cycles through proof images (Ken Burns per image). */
export type ProofBeat = {
  type: 'proof';
  from: number;
  dur: number;
  images: string[];
  title?: string;
};

/** Full-screen b-roll (muted), gentle Ken Burns. Keep dur under 100 frames. */
export type BrollBeat = { type: 'broll'; from: number; dur: number; video: string };

/** Closing card on canvas: title, sub line, CTA bar, optional icon. */
export type EndcardBeat = {
  type: 'endcard';
  from: number;
  dur: number;
  title: string;
  sub?: string;
  cta: string;
  icon?: IconName;
};

/** Row in the panel. `at` = absolute frame (word cue), icon optional
 *  (check, x, arrow-right … whatever fits the content). */
export type PanelRow = { text: string; at: number; icon?: IconName };

/**
 * THE workhorse (VSL-style side panel, vertical-first): rounded
 * paper card that slides in from the side. Optional icon badge, eyebrow,
 * serif title; rows build up word cue by word cue.
 * 9:16: upper or lower third (`position`). 16:9: side panel
 * left/right, vertically centered (`side`).
 */
export type PanelBeat = {
  type: 'panel';
  from: number;
  dur: number;
  position?: 'top' | 'bottom';
  side?: 'left' | 'right';
  icon?: IconName;
  eyebrow?: string;
  title?: string;
  rows?: PanelRow[];
};

/**
 * Full-screen statement on brand canvas (VSL-style takeover): big serif lines
 * (`*like this*` = accent), optional sub line + icon row. Push wipe in/out.
 * For the ONE big statement; use more sparingly than panel.
 */
export type TakeoverBeat = {
  type: 'takeover';
  from: number;
  dur: number;
  eyebrow?: string;
  lines: string[];
  sub?: string;
  icons?: IconName[];
};

export type DiagramSide = { label: string; icon?: IconName };
export type DiagramStep = { label: string; icon?: IconName; at?: number };

/**
 * Built-in diagrams (canvas cutaway, pure SVG/CSS, theme-colored):
 *  - 'versus': two boxes (left/right) + verdict check mark on the
 *    winning side (`verdict`, cue `verdictAt`), the loser dims.
 *  - 'flow':   2–4 steps with arrows, builds step by step
 *    (`steps[].at` = absolute frames; without at, staggered automatically).
 *  - 'scale':  balance scale, tips toward the `verdict` side (cue `verdictAt`).
 */
export type DiagramBeat = {
  type: 'diagram';
  from: number;
  dur: number;
  kind: 'versus' | 'flow' | 'scale';
  title?: string;
  left?: DiagramSide;
  right?: DiagramSide;
  verdict?: 'left' | 'right';
  verdictAt?: number;
  steps?: DiagramStep[];
};

/**
 * Persistent chapter label (VSL-style eyebrow): small micro-caps pill that
 * stays up for a whole chapter. Automatically triggers a punch-in on the
 * video at beat start (chapter-change grammar).
 * Fades out automatically during full-screen cutaways.
 */
export type KickerBeat = {
  type: 'kicker';
  from: number;
  dur: number;
  text: string;
  align?: 'left' | 'center';
};

/** Lower-third name tag: name + credential line,
 *  slides in from the side. For intro moments. Does NOT trigger a punch. */
export type NametagBeat = {
  type: 'nametag';
  from: number;
  dur: number;
  name: string;
  sub?: string;
  side?: 'left' | 'right';
};

export type Beat =
  | HookBeat
  | HookBarBeat
  | StatBeat
  | ListBeat
  | ChipsBeat
  | ImageCardBeat
  | ProofBeat
  | BrollBeat
  | EndcardBeat
  | PanelBeat
  | TakeoverBeat
  | DiagramBeat
  | KickerBeat
  | NametagBeat;

/** The creator's brand identity. Colors as hex, fonts as Google Fonts family names
 *  (e.g. "Playfair Display", "Plus Jakarta Sans"). */
export type Theme = {
  bg: string;
  ink: string;
  accent: string;
  accent2?: string;
  capActive: string;
  serif: string;
  sans: string;
};

export type VideoSpec = {
  /** Path relative to public/, e.g. "cut/my-video.mp4". */
  video: string;
  durationInFrames: number;
  fps: number;
  /** Shifts ONLY the caption/word timings (frames), not the audio. */
  audioOffsetFrames?: number;
  /** Number format for stat count-ups (e.g. "de-DE" shows 2.000, "en-US" 2,000). Default "en-US". */
  locale?: string;
  /** Render the overlays only, on a transparent ground (no video, no audio): for NLE export. */
  overlayOnly?: boolean;
  theme: Theme;
  words: Word[];
  /** font: 'serif' (default, theme serif in italic) or 'sans' (theme sans, bold).
   *  Captions are ALWAYS one line. */
  captions?: {
    enabled: boolean;
    y?: number;
    font?: 'serif' | 'sans';
    /** 'box' (default): dark glass box. 'plain': text with a shadow only, no background. */
    style?: 'box' | 'plain';
    /** Color of the word currently being spoken. Default theme.capActive. */
    activeColor?: string;
  };
  /** Default: no music. Only set it when the user explicitly asks for it. */
  music?: { file: string; volume: number } | null;
  beats: Beat[];
};
