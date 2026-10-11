import React from 'react';
import type { IconName, Theme } from '../spec';

/**
 * Built-in icon library: ~27 line icons as inline SVG (simple
 * paths, stroke = currentColor or the `color` prop). Style:
 * round caps, calm geometry, no fills.
 *
 * Beats reference icons by name (`icon: 'leaf'`). Add new icons here
 * AND add the name to spec.ts (IconName).
 */

const P: Record<IconName, React.ReactNode> = {
  check: <path d="M5 12.5 L10 17.5 L19 7" />,
  x: <path d="M6.5 6.5 L17.5 17.5 M17.5 6.5 L6.5 17.5" />,
  'arrow-up': <path d="M12 19 V5 M6 11 L12 5 L18 11" />,
  'arrow-down': <path d="M12 5 V19 M6 13 L12 19 L18 13" />,
  'arrow-right': <path d="M5 12 H19 M13 6 L19 12 L13 18" />,
  leaf: (
    <>
      <path d="M19 5 C10 5 5 10 5 16.5 C5 18 6 19 7.5 19 C15 19 19 13 19 5 Z" />
      <path d="M7 17 C9 12.5 12.5 8.5 16.5 6.5" />
    </>
  ),
  heart: (
    <path d="M12 20 C5 14.5 4 10 6.5 7.5 C8.5 5.5 11 6 12 8 C13 6 15.5 5.5 17.5 7.5 C20 10 19 14.5 12 20 Z" />
  ),
  drop: (
    <path d="M12 3 C15 8 18 11 18 14.5 A6 6 0 0 1 6 14.5 C6 11 9 8 12 3 Z" />
  ),
  flame: (
    <path d="M12 3 C13 7 17 8.5 17 13.2 A5 5.2 0 0 1 7 13.2 C7 10.5 9 9.5 9.5 7 C10.8 8 11.6 9.2 11.6 10.8 C12.6 9.2 12.5 6 12 3 Z" />
  ),
  bolt: <path d="M13 2.5 L5.5 13 H11 L9.5 21.5 L18.5 9.5 H12.5 Z" />,
  shield: (
    <path d="M12 3 L19 5.8 V11 C19 15.8 16.2 19.4 12 21 C7.8 19.4 5 15.8 5 11 V5.8 Z" />
  ),
  warning: (
    <>
      <path d="M12 4 L21 19.5 H3 Z" />
      <path d="M12 10 V14.2" />
      <path d="M12 16.8 V17" />
    </>
  ),
  sparkle: (
    <path d="M12 3 L13.8 10.2 L21 12 L13.8 13.8 L12 21 L10.2 13.8 L3 12 L10.2 10.2 Z" />
  ),
  star: (
    <path d="M12 3.5 L14.6 8.8 L20.5 9.6 L16.2 13.7 L17.3 19.5 L12 16.7 L6.7 19.5 L7.8 13.7 L3.5 9.6 L9.4 8.8 Z" />
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7 V12 L15.5 14" />
    </>
  ),
  calendar: (
    <>
      <rect x="4" y="5.5" width="16" height="14.5" rx="2" />
      <path d="M4 10 H20 M8 3.5 V7 M16 3.5 V7" />
    </>
  ),
  scale: (
    <>
      <path d="M12 4.5 V19.5 M8 20 H16 M4.5 7 H19.5" />
      <path d="M4.5 7 L2.5 12 M4.5 7 L6.5 12 M2.5 12 A2.6 2.6 0 0 0 6.5 12" />
      <path d="M19.5 7 L17.5 12 M19.5 7 L21.5 12 M17.5 12 A2.6 2.6 0 0 0 21.5 12" />
    </>
  ),
  brain: (
    <>
      <path d="M12 4.5 C8.8 4.5 6.8 6.4 6.8 8.8 C5.2 9.7 4.6 12 6 13.6 C5.5 16.2 7.4 18.3 10 17.8 C10.5 19.3 13.5 19.3 14 17.8 C16.6 18.3 18.5 16.2 18 13.6 C19.4 12 18.8 9.7 17.2 8.8 C17.2 6.4 15.2 4.5 12 4.5 Z" />
      <path d="M12 4.8 V19" />
    </>
  ),
  gut: (
    <path d="M5 6 H14.5 A4 4 0 0 1 14.5 14 H9.5 A3.2 3.2 0 0 0 9.5 20.4 H19" />
  ),
  muscle: (
    <>
      <path d="M7 4.5 H11 L13.5 8.5 C16.5 7.5 19.5 9.6 19.5 12.8 C19.5 16.4 16 18.8 12.2 18 C8.8 17.3 6.2 14.6 6.4 10.8 Z" />
      <path d="M11 11.5 C12.2 10.6 13.8 10.8 14.8 11.8" />
    </>
  ),
  pill: (
    <g transform="rotate(45 12 12)">
      <rect x="8.2" y="2.8" width="7.6" height="18.4" rx="3.8" />
      <path d="M8.2 12 H15.8" />
    </g>
  ),
  bowl: (
    <>
      <path d="M4 12 H20 A8 8 0 0 1 4 12 Z" />
      <path d="M10 8.5 C9.5 7 10.5 6 10 4.5 M14 8.5 C13.5 7 14.5 6 14 4.5" />
    </>
  ),
  money: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 6.8 V17.2 M14.6 8.8 C14 7.7 10 7.4 9.6 9.6 C9.2 12 14.8 11.6 14.4 14 C14 16.2 9.8 15.8 9.2 14.4" />
    </>
  ),
  'chart-up': (
    <>
      <path d="M4 4.5 V19.5 H20" />
      <path d="M6.5 15.5 L10.5 10.5 L13.5 13 L19 6.5" />
      <path d="M15.5 6.5 H19 V10" />
    </>
  ),
  chat: (
    <path d="M20 13.5 C20 14.6 19.1 15.5 18 15.5 H10.5 L6 19.5 V15.5 C4.9 15.5 4 14.6 4 13.5 V6.5 C4 5.4 4.9 4.5 6 4.5 H18 C19.1 4.5 20 5.4 20 6.5 Z" />
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M15.8 15.8 L20 20" />
    </>
  ),
  lock: (
    <>
      <rect x="5.5" y="10.5" width="13" height="9.5" rx="2" />
      <path d="M8.5 10.5 V8 A3.5 3.5 0 0 1 15.5 8 V10.5 M12 14 V16.5" />
    </>
  ),
};

/** A line icon. `color` defaults to currentColor, `strokeWidth` scales with it. */
export const Icon: React.FC<{
  name: IconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
  style?: React.CSSProperties;
}> = ({ name, size = 32, color = 'currentColor', strokeWidth = 1.9, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    style={{ display: 'block', flexShrink: 0, ...style }}
  >
    {P[name] ?? P.sparkle}
  </svg>
);

/** Icon in a round accent badge (filled circle, icon in a contrast color). */
export const IconBadge: React.FC<{
  name: IconName;
  theme: Theme;
  size?: number;
  bg?: string;
  fg?: string;
}> = ({ name, theme, size = 64, bg, fg }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: '50%',
      background: bg ?? theme.accent,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    }}
  >
    <Icon name={name} size={Math.round(size * 0.52)} color={fg ?? '#FFFFFF'} strokeWidth={2.1} />
  </div>
);
