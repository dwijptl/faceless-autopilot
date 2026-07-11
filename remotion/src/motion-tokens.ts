import type {CSSProperties} from 'react';
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

/** Shared motion and surface vocabulary for every new library component. */
export const SPRING = {
  snap: {damping: 15, stiffness: 220, mass: 0.62},
  settle: {damping: 18, stiffness: 145, mass: 0.78},
  drift: {damping: 24, stiffness: 75, mass: 1.05},
  wobble: {damping: 10, stiffness: 165, mass: 0.72},
} as const;

export const TIMING = {
  enter: 10,
  hold: 44,
  exitLead: 9,
  stagger: 3,
} as const;

export const SPACE = {xs: 8, sm: 12, md: 20, lg: 32, xl: 48, xxl: 72} as const;
export const RADIUS = {sm: 14, md: 22, lg: 34, pill: 999} as const;
export const SHADOW = {
  sm: '0 10px 28px rgba(0,0,0,.28)',
  md: '0 24px 64px rgba(0,0,0,.42)',
  lg: '0 40px 110px rgba(0,0,0,.58)',
} as const;

export const GLASS = {
  opacity: 0.25,
  blur: 25,
  border: 'rgba(255,255,255,.24)',
  borderTop: 'rgba(255,255,255,.70)',
  radiusLg: 36,
  radiusSm: 22,
  tint: 'rgba(6,15,30,.58)',
  frost: 'rgba(255,255,255,.10)',
  shadow: '0 34px 110px rgba(0,0,0,.60), inset 0 1px 0 rgba(255,255,255,.36)',
} as const;

export const GLOW = (accent: string, strength = 1) =>
  `0 0 ${Math.round(26 * strength)}px ${accent}55, 0 0 ${Math.round(72 * strength)}px ${accent}22`;

export const useScale = () => {
  const {width, height} = useVideoConfig();
  return width < height ? width / 1280 : Math.min(width / 1920, height / 1080);
};

export const useEnter = (
  delay = 0,
  preset: keyof typeof SPRING = 'settle'
) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = spring({frame: frame - delay, fps, config: SPRING[preset]});
  return {
    progress,
    opacity: interpolate(progress, [0, 1], [0, 1]),
    transform: `translateY(${interpolate(progress, [0, 1], [48, 0])}px) scale(${interpolate(progress, [0, 1], [.94, 1])})`,
  };
};

/** Devanagari-safe text defaults: never introduce synthetic tracking. */
export const text = (fontSize: number, fontWeight = 700, scale = 1): CSSProperties => ({
  fontSize: fontSize * scale,
  fontWeight,
  letterSpacing: 0,
  lineHeight: 1.32,
});

export const panel = (scale = 1): CSSProperties => ({
  borderRadius: GLASS.radiusLg * scale,
  border: `${Math.max(1, 1.4 * scale)}px solid ${GLASS.border}`,
  boxShadow: GLASS.shadow,
  overflow: 'hidden',
});
