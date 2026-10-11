import { useEffect, useState } from 'react';
import { continueRender, delayRender } from 'remotion';
import type { Theme } from './spec';

/**
 * Theme defaults + Google Fonts loading.
 *
 * The theme ALWAYS comes in through the spec props (derived from creator.yaml);
 * DEFAULT_THEME is only the fallback for the Studio preview without props.
 *
 * Fonts: Google Fonts via @remotion/google-fonts. We load through a fixed
 * map of family name → dynamic import (Webpack needs literal paths;
 * a template string would bundle the entire font catalog). Families
 * that are not in the map fall back cleanly to the system stacks:
 * the video still renders, just without the requested font.
 */

export const DEFAULT_THEME: Theme = {
  bg: '#16121C',
  ink: '#F7F4EF',
  accent: '#D4AF37',
  accent2: '#C9A961',
  capActive: '#D4AF37',
  serif: 'Playfair Display',
  sans: 'Plus Jakarta Sans',
};

type GoogleFontModule = {
  loadFont: () => { fontFamily: string; waitUntilDone: () => Promise<void> };
};

/** Curated set of common brand fonts. Extendable: import path = family name
 *  without spaces. */
const FONT_LOADERS: Record<string, () => Promise<GoogleFontModule>> = {
  'Playfair Display': () => import('@remotion/google-fonts/PlayfairDisplay'),
  'Plus Jakarta Sans': () => import('@remotion/google-fonts/PlusJakartaSans'),
  Inter: () => import('@remotion/google-fonts/Inter'),
  Montserrat: () => import('@remotion/google-fonts/Montserrat'),
  Poppins: () => import('@remotion/google-fonts/Poppins'),
  Oswald: () => import('@remotion/google-fonts/Oswald'),
  Lora: () => import('@remotion/google-fonts/Lora'),
  Merriweather: () => import('@remotion/google-fonts/Merriweather'),
  'Cormorant Garamond': () => import('@remotion/google-fonts/CormorantGaramond'),
  'DM Sans': () => import('@remotion/google-fonts/DMSans'),
  'DM Serif Display': () => import('@remotion/google-fonts/DMSerifDisplay'),
  'Space Grotesk': () => import('@remotion/google-fonts/SpaceGrotesk'),
  'Bebas Neue': () => import('@remotion/google-fonts/BebasNeue'),
  Archivo: () => import('@remotion/google-fonts/Archivo'),
  'Libre Baskerville': () => import('@remotion/google-fonts/LibreBaskerville'),
  Raleway: () => import('@remotion/google-fonts/Raleway'),
  'Work Sans': () => import('@remotion/google-fonts/WorkSans'),
  'Crimson Pro': () => import('@remotion/google-fonts/CrimsonPro'),
  'Instrument Serif': () => import('@remotion/google-fonts/InstrumentSerif'),
  'Instrument Sans': () => import('@remotion/google-fonts/InstrumentSans'),
};

/** CSS font stacks with safe fallbacks. */
export const serifStack = (theme: Theme): string => `'${theme.serif}', Georgia, serif`;
export const sansStack = (theme: Theme): string =>
  `'${theme.sans}', 'Helvetica Neue', Arial, sans-serif`;

/** Loads both theme fonts and blocks the render until they are ready. */
export const useThemeFonts = (theme: Theme): void => {
  const [handle] = useState(() => delayRender('Loading Google Fonts'));

  useEffect(() => {
    const load = async () => {
      const families = [theme.serif, theme.sans];
      for (const family of families) {
        const loader = FONT_LOADERS[family];
        if (!loader) {
          // eslint-disable-next-line no-console
          console.warn(
            `Font "${family}" is not in the fallback map (theme.ts); using the system fallback.`
          );
          continue;
        }
        try {
          const mod = await loader();
          await mod.loadFont().waitUntilDone();
        } catch (err) {
          // eslint-disable-next-line no-console
          console.warn(`Font "${family}" could not be loaded:`, err);
        }
      }
      continueRender(handle);
    };
    void load();
  }, [handle, theme.serif, theme.sans]);
};
