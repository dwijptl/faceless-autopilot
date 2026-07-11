import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {fontFamily} from './elements';
import {StylePack} from './styles';

export type MapRender = {
  world?: string;
  region?: string;
  markerWorld?: number[];
  markerRegion?: number[];
  label?: string;
};

const Marker: React.FC<{fx: number; fy: number; accent: string; s: number}> = ({
  fx,
  fy,
  accent,
  s,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ring = (frame / fps) % 1.6; // pulse every 1.6s
  const rr = interpolate(ring, [0, 1.6], [10, 64]) * s;
  const ro = interpolate(ring, [0, 1.6], [0.8, 0]);
  return (
    <>
      <div style={{
        position: 'absolute', left: `${fx * 100}%`, top: `${fy * 100}%`,
        width: rr, height: rr, borderRadius: '50%',
        border: `${3 * s}px solid ${accent}`, opacity: ro,
        transform: 'translate(-50%, -50%)',
      }} />
      <div style={{
        position: 'absolute', left: `${fx * 100}%`, top: `${fy * 100}%`,
        width: 16 * s, height: 16 * s, borderRadius: '50%',
        background: accent, boxShadow: `0 0 ${18 * s}px ${accent}`,
        transform: 'translate(-50%, -50%)',
      }} />
    </>
  );
};

/** Two-phase map zoom: world overview pushes toward the marker, then
 * crossfades into a re-rendered close-up region with a labelled marker. */
export const MapZoom: React.FC<{
  map: MapRender;
  sceneFrames: number;
  style: StylePack;
}> = ({map, sceneFrames, style}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  if (!map?.world || !map?.region) return null;
  const [wx, wy] = map.markerWorld ?? [0.5, 0.5];
  const [rx, ry] = map.markerRegion ?? [0.5, 0.5];

  const switchF = Math.min(Math.round(sceneFrames * 0.42), Math.round(3.2 * fps));
  const zoomT = interpolate(frame, [0, switchF], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const worldScale = interpolate(zoomT, [0, 1], [1.04, 3.4]);
  // push the marker toward the frame center as we zoom
  const tx = interpolate(zoomT, [0, 1], [0, (0.5 - wx) * 100]);
  const ty = interpolate(zoomT, [0, 1], [0, (0.5 - wy) * 100]);
  const xfade = interpolate(frame, [switchF - Math.round(0.4 * fps), switchF],
    [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const regionScale = interpolate(frame, [switchF, sceneFrames], [1.04, 1.16],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const labelIn = spring({frame: frame - switchF - 6, fps,
    config: {damping: 200, stiffness: 120}});

  return (
    <AbsoluteFill style={{backgroundColor: style.bg, overflow: 'hidden'}}>
      {/* world phase */}
      <AbsoluteFill style={{
        opacity: 1 - xfade,
        transform: `scale(${worldScale}) translate(${tx}%, ${ty}%)`,
      }}>
        <Img src={staticFile(map.world)}
          style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        <Marker fx={wx} fy={wy} accent={style.accent} s={s} />
      </AbsoluteFill>
      {/* region phase */}
      <AbsoluteFill style={{opacity: xfade, transform: `scale(${regionScale})`}}>
        <Img src={staticFile(map.region)}
          style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        <Marker fx={rx} fy={ry} accent={style.accent} s={s} />
        {map.label ? (
          <div style={{
            position: 'absolute',
            left: `${Math.min(rx * 100 + 3, 72)}%`,
            top: `${Math.max(ry * 100 - 8, 6)}%`,
            fontFamily, fontSize: 40 * s, fontWeight: 800,
            color: '#F4F7FB', background: 'rgba(10,20,40,0.85)',
            border: `${2 * s}px solid ${style.accent}`,
            padding: `${8 * s}px ${20 * s}px`, borderRadius: 10 * s,
            opacity: labelIn, lineHeight: 1.4,
            transform: `translateY(${interpolate(labelIn, [0, 1], [16, 0])}px)`,
          }}>{map.label}</div>
        ) : null}
      </AbsoluteFill>
      {/* vignette to match footage grade */}
      <AbsoluteFill style={{
        background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.4) 100%)',
        pointerEvents: 'none',
      }} />
    </AbsoluteFill>
  );
};
