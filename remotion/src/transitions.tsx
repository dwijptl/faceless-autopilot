import React from 'react';
import {AbsoluteFill} from 'remotion';
import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from '@remotion/transitions';

/** Custom transition presentations — the "hand-edited" camera language.
 *
 * zoomPunch: the outgoing shot swells and defocuses while the incoming shot
 * punches through it — reads as a physical camera push, not a dissolve.
 *
 * blurWhip: a whip-pan. Both shots fly in the same direction with heavy
 * motion blur peaking mid-transition. Use fast timings (6-10 frames).
 */

const smooth = (p: number) => p * p * (3 - 2 * p); // smoothstep easing

// ── zoom punch ──────────────────────────────────────────────────────────
const ZoomPunch: React.FC<
  TransitionPresentationComponentProps<Record<string, never>>
> = ({children, presentationDirection, presentationProgress}) => {
  const p = smooth(presentationProgress);
  const entering = presentationDirection === 'entering';
  const scale = entering ? 0.86 + 0.14 * p : 1 + 0.16 * p;
  const blur = entering ? 10 * (1 - p) : 12 * p;
  const opacity = entering ? Math.min(p * 1.8, 1) : 1 - p;
  return (
    <AbsoluteFill
      style={{
        transform: `scale(${scale})`,
        filter: `blur(${blur.toFixed(2)}px)`,
        opacity,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

export const zoomPunch = (): TransitionPresentation<Record<string, never>> => ({
  component: ZoomPunch,
  props: {},
});

// ── blur whip ───────────────────────────────────────────────────────────
export type WhipDirection = 'from-left' | 'from-right' | 'from-top' | 'from-bottom';
type WhipProps = {direction: WhipDirection};

const WHIP_VECTORS: Record<WhipDirection, [number, number]> = {
  'from-right': [1, 0],
  'from-left': [-1, 0],
  'from-bottom': [0, 1],
  'from-top': [0, -1],
};

const BlurWhip: React.FC<TransitionPresentationComponentProps<WhipProps>> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const p = smooth(presentationProgress);
  const [dx, dy] = WHIP_VECTORS[passedProps.direction ?? 'from-right'];
  const entering = presentationDirection === 'entering';
  // camera whips toward the incoming shot: outgoing exits opposite the
  // incoming shot's origin, both blurred hardest mid-move
  const travel = 34; // percent of frame
  const tx = entering ? dx * travel * (1 - p) : -dx * travel * p;
  const ty = entering ? dy * travel * (1 - p) : -dy * travel * p;
  const blur = 18 * Math.sin(Math.PI * p);
  const opacity = entering ? Math.min(p * 2.2, 1) : 1 - p * p;
  return (
    <AbsoluteFill
      style={{
        transform: `translate(${tx.toFixed(3)}%, ${ty.toFixed(3)}%) scale(1.04)`,
        filter: `blur(${blur.toFixed(2)}px)`,
        opacity,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

export const blurWhip = (
  direction: WhipDirection = 'from-right'
): TransitionPresentation<WhipProps> => ({
  component: BlurWhip,
  props: {direction},
});
