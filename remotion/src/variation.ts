/** Seeded per-video jitter — two videos in the SAME pack never render
 * identically. Deterministic (Remotion's random(seed)), driven by the
 * manifest's motionSeed, so re-renders are reproducible while every new
 * title lands on slightly different framing: caption position/size,
 * grade & texture intensity, lower-third entry timing, word tilt.
 * Ranges are deliberately narrow — variation should read as a human
 * editor's hand, not as a glitch.
 */
import {random} from 'remotion';

export type Variation = {
  captionYOff: number;   // ± caption anchor offset (fraction of height)
  captionScale: number;  // caption size multiplier
  captionMaxW: number;   // caption max width (fraction)
  gradeOpacity: number;  // grade overlay intensity multiplier
  texOpacity: number;    // texture overlay intensity multiplier
  ltDelay: number;       // lower-third entry delay (frames)
  tiltSeed: string;      // seed for per-word tilt in 'outline' captions
};

export const variationFor = (seed: string): Variation => ({
  captionYOff: (random(`vy-${seed}`) - 0.5) * 0.05,
  captionScale: 0.94 + random(`vs-${seed}`) * 0.12,
  captionMaxW: 0.72 + random(`vw-${seed}`) * 0.1,
  gradeOpacity: 0.8 + random(`vg-${seed}`) * 0.35,
  texOpacity: 0.7 + random(`vt-${seed}`) * 0.55,
  ltDelay: Math.round(4 + random(`vl-${seed}`) * 8),
  tiltSeed: `tilt-${seed}`,
});

export const DEFAULT_VARIATION: Variation = {
  captionYOff: 0,
  captionScale: 1,
  captionMaxW: 0.78,
  gradeOpacity: 1,
  texOpacity: 1,
  ltDelay: 7,
  tiltSeed: 'tilt-default',
};
