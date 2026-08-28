import React from 'react';
import {AbsoluteFill, Img, interpolate, random, useCurrentFrame} from 'remotion';
import type {StylePack} from './styles';

/** Visual-director renderer layer.
 *
 * FamilyCamera — deterministic directed camera moves for still shots. The
 * beat's narrative-intent family (python: pipeline/families.py) decides the
 * move: descend beats crane down, evidence beats push in, timeline beats
 * track laterally. Replaces the random Ken Burns drift for directed beats.
 *
 * FamilyGraphic — zero-cost programmatic full-canvas graphics (timeline /
 * scale / branch / chart / cutaway) drawn from the beat planner's bounded
 * data payload. These are first-class shots, not overlays: they carry the
 * beat on their own, in the channel's dark investigative identity.
 */

const FONT =
  '"Inter", "Noto Sans Devanagari", -apple-system, "DejaVu Sans", sans-serif';

export type GraphicItem = {label?: string; value?: number};
export type GraphicData = {
  kind?: string;
  variant?: string;
  title?: string;
  unit?: string;
  items?: GraphicItem[];
};

const ease = (p: number) => p * p * (3 - 2 * p);

// intensity 1..3 scales how far the camera travels
const intensityFactor = (intensity?: number) =>
  intensity === 3 ? 1.35 : intensity === 2 ? 1.0 : 0.72;

// ── FamilyCamera ────────────────────────────────────────────────────────
export const FamilyCamera: React.FC<{
  camera: string;
  durationInFrames: number;
  seed: string;
  intensity?: number;
  src: string;
  depth?: boolean; // two-layer parallax depth for AI stills
}> = ({camera, durationInFrames, seed, intensity, src, depth}) => {
  const frame = useCurrentFrame();
  const t = ease(
    Math.min(frame / Math.max(durationInFrames, 1), 1));
  const k = intensityFactor(intensity);
  const dir = random(`camdir-${seed}`) < 0.5 ? 1 : -1;

  let scale = 1.1;
  let tx = 0; // percent
  let ty = 0;
  let rot = 0;
  switch (camera) {
    case 'push':
      scale = 1.06 + 0.12 * k * t;
      break;
    case 'pull':
      scale = 1.06 + 0.12 * k * (1 - t);
      break;
    case 'crane_down':
      scale = 1.16;
      ty = interpolate(t, [0, 1], [4.5 * k, -4.5 * k]);
      break;
    case 'crane_up':
      scale = 1.16;
      ty = interpolate(t, [0, 1], [-4.5 * k, 4.5 * k]);
      break;
    case 'lateral':
      scale = 1.14;
      tx = dir * interpolate(t, [0, 1], [-3.8 * k, 3.8 * k]);
      break;
    case 'tilt_up':
      scale = 1.18;
      ty = interpolate(t, [0, 1], [5.5 * k, -5.5 * k]);
      break;
    case 'tilt_down':
      scale = 1.18;
      ty = interpolate(t, [0, 1], [-5.5 * k, 5.5 * k]);
      break;
    case 'drift': {
      const w = (frame / Math.max(durationInFrames, 1)) * Math.PI;
      scale = 1.1 + 0.02 * Math.sin(w);
      tx = dir * 1.4 * k * Math.sin(w);
      ty = 1.0 * k * Math.sin(w * 0.7);
      break;
    }
    case 'orbit':
      scale = 1.12 + 0.04 * k * t;
      tx = dir * interpolate(t, [0, 1], [-2.6 * k, 2.6 * k]);
      rot = dir * 0.5 * k * t;
      break;
    case 'hold':
    default:
      scale = 1.04;
      tx = dir * 0.4 * t;
      break;
  }
  const transform =
    `scale(${scale.toFixed(4)}) translate(${tx.toFixed(3)}%, ` +
    `${ty.toFixed(3)}%) rotate(${rot.toFixed(3)}deg)`;
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      {depth ? (
        <Img
          src={src}
          style={{
            position: 'absolute', width: '100%', height: '100%',
            objectFit: 'cover', filter: 'blur(10px) brightness(0.7)',
            transform:
              `scale(${(scale + 0.16).toFixed(4)}) ` +
              `translate(${(-tx * 0.4).toFixed(3)}%, ${(-ty * 0.4).toFixed(3)}%)`,
          }}
        />
      ) : null}
      <Img
        src={src}
        style={{
          position: 'absolute', width: '100%', height: '100%',
          objectFit: 'cover', transform,
          ...(depth
            ? {
                maskImage:
                  'radial-gradient(ellipse 80% 80% at 50% 50%, black 58%, transparent 100%)',
                WebkitMaskImage:
                  'radial-gradient(ellipse 80% 80% at 50% 50%, black 58%, transparent 100%)',
              }
            : {}),
        }}
      />
    </AbsoluteFill>
  );
};

// ── shared canvas for programmatic graphics ────────────────────────────
const Canvas: React.FC<{
  style: StylePack;
  title?: string;
  children: React.ReactNode;
}> = ({style, title, children}) => (
  <AbsoluteFill
    style={{
      background:
        'radial-gradient(ellipse 120% 90% at 50% 10%, rgb(14,20,34) 0%, rgb(6,9,16) 70%)',
      fontFamily: FONT,
      color: '#E8ECF4',
    }}
  >
    {/* faint technical grid */}
    <AbsoluteFill
      style={{
        backgroundImage:
          'linear-gradient(rgba(130,150,190,0.06) 1px, transparent 1px), ' +
          'linear-gradient(90deg, rgba(130,150,190,0.06) 1px, transparent 1px)',
        backgroundSize: '96px 96px',
      }}
    />
    {title ? (
      <div
        style={{
          position: 'absolute', top: '6.5%', left: '7%',
          fontSize: 34, fontWeight: 800, letterSpacing: 4,
          textTransform: 'uppercase', color: style.accent,
          borderLeft: `5px solid ${style.accent}`, paddingLeft: 18,
        }}
      >
        {title}
      </div>
    ) : null}
    {children}
  </AbsoluteFill>
);

const fmt = (v?: number, unit?: string) => {
  if (typeof v !== 'number' || !isFinite(v)) return '';
  const s = Math.abs(v) >= 1000 ? Math.round(v).toLocaleString('en-IN')
    : (Math.round(v * 10) / 10).toString();
  return unit ? `${s} ${unit}` : s;
};

// draw-on progress for element i of n, staggered across the shot
const stagger = (t: number, i: number, n: number) =>
  ease(Math.min(Math.max((t * (n + 1.6) - i) / 1.6, 0), 1));

// Network-independent last resort. This is intentionally visually dense: a
// failed stock/AI lookup must never read as a blank solid-colour frame.
const FallbackGraphic: React.FC<{
  data: GraphicData; style: StylePack; t: number;
}> = ({data, style, t}) => {
  const labels = (data.items ?? [])
    .map((item) => String(item.label ?? '').trim())
    .filter(Boolean)
    .slice(0, 3);
  const items = labels.length > 0 ? labels : ['EVIDENCE', 'CONTEXT', 'UNKNOWN'];
  const positions = [
    {left: 13, top: 43},
    {left: 42, top: 66},
    {left: 71, top: 43},
  ];
  const sweep = interpolate(t, [0, 1], [-12, 112]);
  const variant = String(data.variant ?? 'evidence-orbit');

  if (variant === 'signal-trace') {
    const wave = Array.from({length: 13}, (_, i) => {
      const x = 5 + i * 7.5;
      const y = 52 + Math.sin(i * 1.7 + t * 7) * (8 + (i % 3) * 5);
      return `${x},${y}`;
    }).join(' ');
    return (
      <Canvas style={style} title={data.title}>
        <div style={{position: 'absolute', left: '8%', top: '24%', bottom: '13%',
          width: 3, background: style.accent, boxShadow: `0 0 28px ${style.accent}`}} />
        <svg viewBox="0 0 100 100" preserveAspectRatio="none"
          style={{position: 'absolute', left: '10%', top: '23%', width: '82%', height: '58%'}}>
          {[20, 40, 60, 80].map((y) => <line key={y} x1="0" x2="100" y1={y}
            y2={y} stroke="rgba(180,198,230,0.13)" strokeWidth="0.3" />)}
          <polyline points={wave} fill="none" stroke={style.accent} strokeWidth="1.2"
            strokeDasharray="160" strokeDashoffset={(1 - t) * 160} />
        </svg>
        {items.map((label, i) => <div key={`${label}-${i}`} style={{position: 'absolute',
          left: `${18 + i * 25}%`, bottom: `${12 + (i % 2) * 8}%`, fontSize: 24,
          fontWeight: 750, color: i === 0 ? style.accent : '#D5DDEA',
          opacity: stagger(t, i, items.length), letterSpacing: 1.2}}>{label}</div>)}
        <div style={{position: 'absolute', right: `${100 - sweep}%`, top: '23%',
          height: '58%', width: 2, background: style.accent, opacity: 0.45}} />
        <div style={{position: 'absolute', left: '8%', bottom: '6%', fontSize: 18,
          letterSpacing: 5, color: 'rgba(205,216,236,0.62)'}}>SIGNAL TRACE · FIELD AUDIO</div>
      </Canvas>
    );
  }

  if (variant === 'archive-strip') {
    return (
      <Canvas style={style} title={data.title}>
        <div style={{position: 'absolute', left: '8%', right: '8%', top: '24%',
          bottom: '13%', display: 'flex', gap: '2.5%', alignItems: 'stretch'}}>
          {items.map((label, i) => {
            const p = stagger(t, i, items.length);
            return <div key={`${label}-${i}`} style={{flex: i === 1 ? 1.18 : 0.9,
              position: 'relative', overflow: 'hidden', opacity: p,
              transform: `translateY(${(1 - p) * (i % 2 ? -38 : 38)}px) rotate(${i - 1}deg)`,
              background: 'linear-gradient(145deg, rgba(42,47,55,.98), rgba(12,16,24,.98))',
              border: '1px solid rgba(220,225,235,.28)', boxShadow: '0 24px 70px rgba(0,0,0,.42)'}}>
              <div style={{height: '63%', margin: '7%',
                background: `linear-gradient(${120 + i * 25}deg, rgba(255,255,255,.10), rgba(0,0,0,.38)), repeating-linear-gradient(0deg, rgba(255,255,255,.04) 0 2px, transparent 2px 12px)`,
                border: '1px solid rgba(255,255,255,.11)'}} />
              <div style={{padding: '0 8%', fontSize: 27, fontWeight: 800,
                color: i === 1 ? style.accent : '#E1E6EF'}}>{label}</div>
              <div style={{position: 'absolute', right: '7%', bottom: '5%',
                fontSize: 18, letterSpacing: 3, opacity: .45}}>0{i + 1}</div>
            </div>;
          })}
        </div>
        <div style={{position: 'absolute', left: '8%', bottom: '6%', fontSize: 18,
          letterSpacing: 5, color: 'rgba(205,216,236,0.62)'}}>ARCHIVE PLATE · SOURCE STUDY</div>
      </Canvas>
    );
  }

  if (variant === 'terrain-scan') {
    return (
      <Canvas style={style} title={data.title}>
        <svg viewBox="0 0 1000 560" style={{position: 'absolute', inset: '18% 6% 8%',
          width: '88%', height: '72%'}}>
          {[0, 1, 2, 3, 4, 5].map((i) => <ellipse key={i} cx="500" cy="275"
            rx={110 + i * 65 + t * 12} ry={55 + i * 29 + t * 6} fill="none"
            stroke={i === 1 ? style.accent : 'rgba(184,202,232,.24)'}
            strokeWidth={i === 1 ? 4 : 2} strokeDasharray={`${18 + i * 3} ${8 + i}`} />)}
          <path d="M80 420 C230 310 330 390 470 260 S720 160 920 245" fill="none"
            stroke={style.accent} strokeWidth="4" strokeDasharray="520"
            strokeDashoffset={(1 - t) * 520} />
        </svg>
        {items.map((label, i) => <div key={`${label}-${i}`} style={{position: 'absolute',
          left: `${17 + i * 29}%`, top: `${68 - (i % 2) * 28}%`, padding: '12px 18px',
          fontSize: 24, fontWeight: 760, opacity: stagger(t, i, items.length),
          background: 'rgba(7,11,19,.82)', borderBottom: `3px solid ${style.accent}`}}>{label}</div>)}
        <div style={{position: 'absolute', right: '6%', top: '25%', bottom: '13%',
          width: 2, background: 'rgba(205,216,236,.22)'}} />
        <div style={{position: 'absolute', left: '8%', bottom: '6%', fontSize: 18,
          letterSpacing: 5, color: 'rgba(205,216,236,0.62)'}}>TERRAIN SCAN · DEPTH STUDY</div>
      </Canvas>
    );
  }

  return (
    <Canvas style={style} title={data.title}>
      <svg viewBox="0 0 1000 560" style={{position: 'absolute', inset: '17% 8% 8%',
        width: '84%', height: '72%', overflow: 'visible'}}>
        <path d="M180 245 L500 370 L820 245" fill="none"
          stroke="rgba(180,198,230,0.34)" strokeWidth="3"
          strokeDasharray="10 12" strokeDashoffset={(1 - t) * 120} />
        <circle cx="500" cy="225" r={88 + 18 * t} fill="none"
          stroke={style.accent} strokeWidth="4" opacity={0.32 + t * 0.5} />
        <circle cx="500" cy="225" r={45 + 10 * t} fill="rgba(0,0,0,0.28)"
          stroke="rgba(232,236,244,0.7)" strokeWidth="2" />
        <path d="M500 115 V335 M390 225 H610" stroke="rgba(232,236,244,0.22)"
          strokeWidth="2" />
      </svg>
      <div style={{position: 'absolute', left: '50%', top: '45%',
        transform: `translate(-50%, -50%) scale(${0.82 + 0.18 * ease(t)})`,
        width: 132, height: 132, borderRadius: 999, display: 'grid',
        placeItems: 'center', color: style.accent, fontSize: 72, fontWeight: 900,
        border: `3px solid ${style.accent}`,
        background: 'rgba(5,9,16,0.76)',
        boxShadow: `0 0 55px ${style.accent}55`}}>?</div>
      {items.map((label, index) => {
        const position = positions[index];
        const p = stagger(t, index, items.length);
        return (
          <div key={`${label}-${index}`} style={{position: 'absolute',
            left: `${position.left}%`, top: `${position.top}%`, width: '16%',
            minHeight: 92, padding: '22px 24px', display: 'grid',
            placeItems: 'center', textAlign: 'center', fontSize: 25,
            fontWeight: 750, letterSpacing: 0.6, lineHeight: 1.25,
            opacity: p, transform: `translateY(${(1 - p) * 30}px)`,
            border: '1px solid rgba(180,198,230,0.35)', borderRadius: 10,
            background: 'linear-gradient(145deg, rgba(24,33,52,0.94), rgba(8,13,23,0.92))',
            boxShadow: '0 18px 45px rgba(0,0,0,0.38)'}}>{label}</div>
        );
      })}
      <div style={{position: 'absolute', left: 0, right: 0, top: `${sweep}%`,
        height: 3, background: `linear-gradient(90deg, transparent, ${style.accent}, transparent)`,
        opacity: 0.58, boxShadow: `0 0 24px ${style.accent}`}} />
      <div style={{position: 'absolute', left: '7%', bottom: '7%',
        color: 'rgba(205,216,236,0.62)', fontSize: 18, fontWeight: 700,
        letterSpacing: 5}}>SURAAGNAMA · EVIDENCE MAP</div>
    </Canvas>
  );
};

// ── timeline: chronology with nodes lighting in order ──────────────────
const TimelineGraphic: React.FC<{
  data: GraphicData; style: StylePack; t: number;
}> = ({data, style, t}) => {
  const items = (data.items ?? []).slice(0, 6);
  const n = Math.max(items.length, 1);
  return (
    <Canvas style={style} title={data.title}>
      <div
        style={{
          position: 'absolute', left: '8%', right: '8%', top: '52%',
          height: 4, background: 'rgba(150,170,210,0.25)',
        }}
      >
        <div
          style={{
            height: '100%', width: `${ease(t) * 100}%`,
            background: style.accent,
            boxShadow: `0 0 24px ${style.accent}`,
          }}
        />
      </div>
      {items.map((item, i) => {
        const p = stagger(t, i, n);
        const x = 8 + (84 * (n === 1 ? 0.5 : i / (n - 1)));
        return (
          <div key={i} style={{position: 'absolute', left: `${x}%`, top: '52%',
            transform: 'translate(-50%, -50%)', opacity: p}}>
            <div
              style={{
                width: 26, height: 26, borderRadius: 999, margin: '0 auto',
                background: p > 0.6 ? style.accent : 'rgb(30,40,60)',
                border: `3px solid ${style.accent}`,
                transform: `scale(${0.6 + 0.4 * p})`,
                boxShadow: p > 0.6 ? `0 0 22px ${style.accent}` : 'none',
              }}
            />
            <div style={{marginTop: 22, textAlign: 'center', width: 260,
              marginLeft: -117, fontSize: 30, fontWeight: 700, lineHeight: 1.3}}>
              {item.label}
            </div>
            <div style={{textAlign: 'center', fontSize: 26, marginTop: 6,
              color: style.accent, fontVariantNumeric: 'tabular-nums',
              fontWeight: 800}}>
              {fmt(typeof item.value === 'number' ? item.value * p : undefined,
                data.unit)}
            </div>
          </div>
        );
      })}
    </Canvas>
  );
};

// ── scale: horizontal comparison bars with a measuring axis ────────────
const ScaleGraphic: React.FC<{
  data: GraphicData; style: StylePack; t: number;
}> = ({data, style, t}) => {
  const items = (data.items ?? []).slice(0, 5);
  const max = Math.max(...items.map((i) => Math.abs(i.value ?? 0)), 1);
  const n = Math.max(items.length, 1);
  return (
    <Canvas style={style} title={data.title}>
      {items.map((item, i) => {
        const p = stagger(t, i, n);
        const w = (Math.abs(item.value ?? 0) / max) * 62 * p;
        const y = 24 + (58 / n) * i + 58 / n / 2;
        return (
          <div key={i} style={{position: 'absolute', left: '7%', right: '7%',
            top: `${y}%`, transform: 'translateY(-50%)', opacity: Math.min(p * 2, 1)}}>
            <div style={{fontSize: 30, fontWeight: 700, marginBottom: 10}}>
              {item.label}
            </div>
            <div style={{position: 'relative', height: 34,
              background: 'rgba(150,170,210,0.10)', borderRadius: 6}}>
              <div
                style={{
                  position: 'absolute', left: 0, top: 0, bottom: 0,
                  width: `${w}%`, borderRadius: 6,
                  background: i === 0 ? style.accent : 'rgba(170,190,230,0.65)',
                  boxShadow: i === 0 ? `0 0 26px ${style.accent}` : 'none',
                }}
              />
              <div style={{position: 'absolute', left: `${w + 1.2}%`, top: '50%',
                transform: 'translateY(-50%)', fontSize: 28, fontWeight: 800,
                color: i === 0 ? style.accent : '#C9D4E8',
                fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap'}}>
                {fmt(typeof item.value === 'number' ? item.value * p : undefined,
                  data.unit)}
              </div>
            </div>
          </div>
        );
      })}
    </Canvas>
  );
};

// ── branch: one node splitting into competing explanations ─────────────
const BranchGraphic: React.FC<{
  data: GraphicData; style: StylePack; t: number;
}> = ({data, style, t}) => {
  const items = (data.items ?? []).slice(0, 5);
  const n = Math.max(items.length, 1);
  const rootX = 18;
  const rootY = 50;
  return (
    <Canvas style={style} title={data.title}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none"
        style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
        {items.map((_, i) => {
          const p = stagger(t, i, n);
          const y = 18 + (64 * (n === 1 ? 0.5 : i / (n - 1)));
          const d = `M ${rootX} ${rootY} C 40 ${rootY}, 48 ${y}, 68 ${y}`;
          return (
            <path key={i} d={d} fill="none" stroke={style.accent}
              strokeWidth={0.45} strokeDasharray={100}
              strokeDashoffset={100 - 100 * p} opacity={0.9} />
          );
        })}
      </svg>
      <div style={{position: 'absolute', left: `${rootX}%`, top: `${rootY}%`,
        transform: 'translate(-50%, -50%)', width: 300, textAlign: 'center',
        background: 'rgba(18,26,44,0.92)', border: `3px solid ${style.accent}`,
        borderRadius: 14, padding: '22px 18px', fontSize: 30, fontWeight: 800,
        opacity: Math.min(t * 4, 1)}}>
        {data.unit || '?'}
      </div>
      {items.map((item, i) => {
        const p = stagger(t, i, n);
        const y = 18 + (64 * (n === 1 ? 0.5 : i / (n - 1)));
        return (
          <div key={i} style={{position: 'absolute', left: '68%', top: `${y}%`,
            transform: `translate(0, -50%) translateX(${(1 - p) * 30}px)`,
            width: '25%', opacity: p,
            background: 'rgba(14,20,34,0.92)',
            border: '2px solid rgba(150,170,210,0.4)',
            borderLeft: `6px solid ${style.accent}`,
            borderRadius: 10, padding: '18px 20px',
            fontSize: 29, fontWeight: 700, lineHeight: 1.3}}>
            {item.label}
          </div>
        );
      })}
    </Canvas>
  );
};

// ── chart: one dominant bar chart with counting values ─────────────────
const ChartGraphic: React.FC<{
  data: GraphicData; style: StylePack; t: number;
}> = ({data, style, t}) => {
  const items = (data.items ?? []).slice(0, 6);
  const max = Math.max(...items.map((i) => Math.abs(i.value ?? 0)), 1);
  const n = Math.max(items.length, 1);
  return (
    <Canvas style={style} title={data.title}>
      <div style={{position: 'absolute', left: '10%', right: '10%',
        top: '22%', bottom: '18%', display: 'flex', alignItems: 'flex-end',
        gap: '4%', borderBottom: '3px solid rgba(150,170,210,0.35)'}}>
        {items.map((item, i) => {
          const p = stagger(t, i, n);
          const h = (Math.abs(item.value ?? 0) / max) * 100 * p;
          return (
            <div key={i} style={{flex: 1, display: 'flex',
              flexDirection: 'column', justifyContent: 'flex-end',
              alignItems: 'center', height: '100%'}}>
              <div style={{fontSize: 30, fontWeight: 800, color: style.accent,
                fontVariantNumeric: 'tabular-nums', marginBottom: 10,
                opacity: p}}>
                {fmt(typeof item.value === 'number' ? item.value * p : undefined,
                  data.unit)}
              </div>
              <div style={{width: '70%', height: `${h}%`, borderRadius: '8px 8px 0 0',
                background: `linear-gradient(180deg, ${style.accent}, rgba(170,190,230,0.35))`,
                boxShadow: `0 0 30px rgba(255,176,32,0.25)`}} />
              <div style={{position: 'absolute', bottom: '-14%', fontSize: 27,
                fontWeight: 700, width: `${92 / n}%`, textAlign: 'center',
                transform: `translateX(0)`, opacity: p, lineHeight: 1.25}}>
                {item.label}
              </div>
            </div>
          );
        })}
      </div>
    </Canvas>
  );
};

// ── cutaway: descending strata with a depth line drawing downward ──────
const CutawayGraphic: React.FC<{
  data: GraphicData; style: StylePack; t: number;
}> = ({data, style, t}) => {
  const items = (data.items ?? []).slice(0, 6);
  const n = Math.max(items.length, 1);
  const shades = ['#2A3550', '#26304A', '#222B44', '#1D253C', '#181F34', '#141A2C'];
  return (
    <Canvas style={style} title={data.title}>
      <div style={{position: 'absolute', left: '12%', right: '12%',
        top: '20%', bottom: '10%'}}>
        {items.map((item, i) => {
          const p = stagger(t, i, n);
          return (
            <div key={i} style={{position: 'relative',
              height: `${100 / n}%`, overflow: 'hidden',
              background: shades[i % shades.length],
              borderBottom: '2px solid rgba(150,170,210,0.25)',
              opacity: 0.35 + 0.65 * p}}>
              <div style={{position: 'absolute', left: 28, top: '50%',
                transform: 'translateY(-50%)', fontSize: 30, fontWeight: 700,
                opacity: p}}>
                {item.label}
              </div>
              <div style={{position: 'absolute', right: 28, top: '50%',
                transform: 'translateY(-50%)', fontSize: 29, fontWeight: 800,
                color: style.accent, fontVariantNumeric: 'tabular-nums',
                opacity: p}}>
                {fmt(typeof item.value === 'number' ? item.value * p : undefined,
                  data.unit)}
              </div>
            </div>
          );
        })}
        {/* descent line — the journey travelling down the strata */}
        <div style={{position: 'absolute', left: '50%', top: 0,
          width: 4, height: `${ease(t) * 100}%`,
          background: style.accent, boxShadow: `0 0 22px ${style.accent}`}} />
        <div style={{position: 'absolute', left: '50%', top: `${ease(t) * 100}%`,
          transform: 'translate(-50%, -50%)', width: 20, height: 20,
          borderRadius: 999, background: style.accent,
          boxShadow: `0 0 30px ${style.accent}`}} />
      </div>
    </Canvas>
  );
};

// ── dispatcher ─────────────────────────────────────────────────────────
export const FamilyGraphic: React.FC<{
  graphic: GraphicData;
  style: StylePack;
  durationInFrames: number;
}> = ({graphic, style, durationInFrames}) => {
  const frame = useCurrentFrame();
  // reserve the last 15% as a hold so the finished graphic can be read
  const t = Math.min(frame / Math.max(durationInFrames * 0.85, 1), 1);
  switch (graphic.kind) {
    case 'fallback':
      return <FallbackGraphic data={graphic} style={style} t={t} />;
    case 'timeline':
      return <TimelineGraphic data={graphic} style={style} t={t} />;
    case 'scale':
      return <ScaleGraphic data={graphic} style={style} t={t} />;
    case 'branch':
      return <BranchGraphic data={graphic} style={style} t={t} />;
    case 'chart':
      return <ChartGraphic data={graphic} style={style} t={t} />;
    case 'cutaway':
      return <CutawayGraphic data={graphic} style={style} t={t} />;
    default:
      return <Canvas style={style} title={graphic.title} children={null} />;
  }
};
