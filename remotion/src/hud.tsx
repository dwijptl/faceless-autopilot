import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

/** Telemetry HUD — persistent, subtle sci-doc instrument layer for the
 * "telemetry" style pack. Latin/numeric only (mono type), so it never
 * competes with Devanagari captions. All elements sit near the frame
 * edges at low opacity: texture, not information overload. */

const MONO =
  '"SF Mono", "Cascadia Mono", "JetBrains Mono", "Roboto Mono", monospace';

// ── Story metric readout — the simulation's changing variable ──────────
// Interpolates between per-scene milestone values so the number the viewer
// watches (depth, speed, time, temperature) moves continuously with the
// narrative. Renders nothing when the script provides no milestones.

export type Milestone = {
  start: number;
  value?: number | null;
  label?: string;
  unit?: string;
};

const fmtMetric = (v: number) =>
  Math.abs(v) >= 100 || Number.isInteger(v)
    ? Math.round(v).toLocaleString('en-IN')
    : v.toFixed(1);

export const MetricReadout: React.FC<{
  milestones: Milestone[];
  label: string;
  unit: string;
  accent: string;
  bottom?: number; // offset in 1080p-scale px
}> = ({milestones, label, unit, accent, bottom}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  const t = frame / fps;
  const pts = milestones.filter(
    (m) => typeof m.value === 'number' && isFinite(m.value as number));
  if (pts.length === 0) return null;
  let i = 0;
  pts.forEach((p, idx) => {
    if (t >= p.start) i = idx;
  });
  const cur = pts[i];
  const nxt = pts[Math.min(i + 1, pts.length - 1)];
  const value =
    nxt.start > cur.start
      ? interpolate(t, [cur.start, nxt.start],
          [cur.value as number, nxt.value as number],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
      : (cur.value as number);
  const lbl = (cur.label || label || '').toUpperCase();
  const un = cur.unit || unit || '';
  return (
    <div style={{
      position: 'absolute', left: 40 * s, bottom: (bottom ?? 44) * s,
      fontFamily: MONO, letterSpacing: 2, pointerEvents: 'none',
      textShadow: '0 2px 12px rgba(0,0,0,0.85)',
    }}>
      {lbl ? (
        <div style={{fontSize: 19 * s, color: 'rgba(244,247,251,0.55)'}}>
          {lbl}
        </div>
      ) : null}
      <div style={{fontSize: 42 * s, fontWeight: 700, color: accent}}>
        {fmtMetric(value)}
        {un ? (
          <span style={{fontSize: 22 * s, color: 'rgba(244,247,251,0.75)',
            marginLeft: 8 * s}}>{un}</span>
        ) : null}
      </div>
    </div>
  );
};

const Corner: React.FC<{
  pos: 'tl' | 'tr' | 'bl' | 'br';
  s: number;
}> = ({pos, s}) => {
  const size = 30 * s;
  const b = `${Math.max(2 * s, 1.5)}px solid rgba(244,247,251,0.30)`;
  const off = 26 * s;
  const style: React.CSSProperties = {position: 'absolute', width: size, height: size};
  if (pos === 'tl') Object.assign(style, {top: off, left: off, borderTop: b, borderLeft: b});
  if (pos === 'tr') Object.assign(style, {top: off, right: off, borderTop: b, borderRight: b});
  if (pos === 'bl') Object.assign(style, {bottom: off, left: off, borderBottom: b, borderLeft: b});
  if (pos === 'br') Object.assign(style, {bottom: off, right: off, borderBottom: b, borderRight: b});
  return <div style={style} />;
};

export const TelemetryHUD: React.FC<{
  starts: number[];
  accent: string;
  accent2: string;
  milestones?: Milestone[];
  metricLabel?: string;
  metricUnit?: string;
}> = ({starts, accent, accent2, milestones, metricLabel, metricUnit}) => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  const t = frame / fps;

  let idx = 0;
  starts.forEach((st, i) => {
    if (t >= st) idx = i;
  });
  const pct = ((frame / Math.max(durationInFrames - 1, 1)) * 100).toFixed(1);

  // brief flash of the readout when a new scene begins
  const sceneStart = (starts[idx] ?? 0) * fps;
  const flash = interpolate(frame - sceneStart, [0, 10, 40], [0.9, 0.9, 0.5], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <Corner pos="tl" s={s} />
      <Corner pos="tr" s={s} />
      <Corner pos="bl" s={s} />
      <Corner pos="br" s={s} />

      {/* rotating dashed instrument ring, bottom-left */}
      <div
        style={{
          position: 'absolute',
          left: 40 * s,
          bottom: 96 * s,
          width: 58 * s,
          height: 58 * s,
          borderRadius: '50%',
          border: `${Math.max(1.6 * s, 1)}px dashed ${accent2}`,
          opacity: 0.32,
          transform: `rotate(${frame * 0.5}deg)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 58 * s,
          bottom: 114 * s,
          width: 22 * s,
          height: 22 * s,
          borderRadius: '50%',
          border: `${Math.max(1.4 * s, 1)}px solid ${accent}`,
          opacity: 0.4,
        }}
      />

      {/* monospace readout, bottom-left beside the ring */}
      <div
        style={{
          position: 'absolute',
          left: 116 * s,
          bottom: 108 * s,
          fontFamily: MONO,
          fontSize: 21 * s,
          letterSpacing: 2.5,
          color: 'rgba(244,247,251,0.62)',
          opacity: flash,
          textShadow: '0 2px 10px rgba(0,0,0,0.8)',
        }}
      >
        T·I // SCN {String(idx + 1).padStart(2, '0')}/{String(starts.length).padStart(2, '0')}
        {' '}· <span style={{color: accent}}>{pct}%</span>
      </div>

      {/* the simulation's changing variable, above the instrument ring */}
      <MetricReadout milestones={milestones ?? []} label={metricLabel ?? ''}
        unit={metricUnit ?? ''} accent={accent} bottom={172} />

      {/* faint horizon tick rail, right edge */}
      <div style={{position: 'absolute', right: 30 * s, top: '30%', bottom: '30%',
        width: 1.5 * s, background: 'rgba(244,247,251,0.14)'}} />
      {[0.3, 0.45, 0.6, 0.75].map((f, i) => (
        <div key={i} style={{position: 'absolute', right: 26 * s,
          top: `${f * 100}%`, width: 10 * s, height: 1.5 * s,
          background: i === 1 ? accent2 : 'rgba(244,247,251,0.22)',
          opacity: 0.5}} />
      ))}
    </AbsoluteFill>
  );
};
