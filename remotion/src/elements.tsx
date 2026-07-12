import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  Loop,
  OffthreadVideo,
  Sequence,
  interpolate,
  random,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {BRAND, StylePack} from './styles';

// ── Fonts: Inter (Latin) + Noto Sans Devanagari (Hindi) ────────────────
// Loaded from Google Fonts at render time; the workflow also installs
// fonts-noto-core so headless Chrome has a system-level Devanagari fallback.
let FONT =
  '"Inter", "Noto Sans Devanagari", -apple-system, "DejaVu Sans", sans-serif';
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const {loadFont} = require('@remotion/google-fonts/Inter');
  const inter = loadFont();
  let stack = `"${inter.fontFamily}"`;
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const {loadFont: loadDeva} = require('@remotion/google-fonts/NotoSansDevanagari');
    const deva = loadDeva();
    stack += `, "${deva.fontFamily}"`;
  } catch {
    stack += ', "Noto Sans Devanagari"';
  }
  FONT = `${stack}, sans-serif`;
} catch {
  // keep system fallback
}
export const fontFamily = FONT;

type Asset = {path: string; kind: string; duration?: number};

// ── Ken Burns still ────────────────────────────────────────────────────
export const KenBurnsImage: React.FC<{
  src: string;
  durationInFrames: number;
  seed: string;
}> = ({src, durationInFrames, seed}) => {
  const frame = useCurrentFrame();
  const zoomIn = random(`kb-${seed}`) < 0.5;
  const driftX = (random(`dx-${seed}`) - 0.5) * 60;
  const driftY = (random(`dy-${seed}`) - 0.5) * 40;
  const t = frame / Math.max(durationInFrames, 1);
  const scale = zoomIn
    ? interpolate(t, [0, 1], [1.06, 1.18])
    : interpolate(t, [0, 1], [1.18, 1.06]);
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Img
        src={src}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale}) translate(${driftX * t}px, ${driftY * t}px)`,
        }}
      />
    </AbsoluteFill>
  );
};

// ── Video shot ─────────────────────────────────────────────────────────
const VideoShot: React.FC<{
  asset: Asset;
  shotFrames: number;
  fps: number;
  seed: string;
}> = ({asset, shotFrames, fps, seed}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, Math.max(shotFrames, 1)], [1.0, 1.06]);
  const assetFrames = Math.max(Math.round((asset.duration ?? 6) * fps) - 2, 1);
  const offsetChoices = Math.max(assetFrames - shotFrames, 0);
  const trimBefore = Math.floor(random(`tb-${seed}`) * offsetChoices);
  const video = (
    <OffthreadVideo
      muted
      src={staticFile(asset.path)}
      trimBefore={trimBefore}
      style={{width: '100%', height: '100%', objectFit: 'cover'}}
    />
  );
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `scale(${scale})`}}>
        {assetFrames < shotFrames ? (
          <Loop durationInFrames={assetFrames}>{video}</Loop>
        ) : (
          video
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── Scene visual with style grade ──────────────────────────────────────
export const SceneVisual: React.FC<{
  assets: Asset[];
  sceneFrames: number;
  fps: number;
  maxShotSeconds: number;
  sceneN: number;
  style: StylePack;
  dim?: boolean; // for kinetic/stat overlay scenes
}> = ({assets, sceneFrames, fps, maxShotSeconds, sceneN, style, dim}) => {
  const maxShot = Math.round(maxShotSeconds * fps);
  const shots: {from: number; frames: number; asset: Asset; idx: number}[] = [];
  const shotCount = assets.length > 0
    ? Math.max(1, Math.ceil(sceneFrames / Math.max(maxShot, 1))) : 0;
  const baseFrames = shotCount > 0 ? Math.floor(sceneFrames / shotCount) : 0;
  let cursor = 0;
  for (let i = 0; i < shotCount; i++) {
    const frames = baseFrames + (i < sceneFrames % shotCount ? 1 : 0);
    shots.push({from: cursor, frames, asset: assets[i % assets.length], idx: i});
    cursor += frames;
  }
  return (
    <AbsoluteFill style={{backgroundColor: style.bg}}>
      <AbsoluteFill style={{filter: style.visualFilter}}>
        {shots.map((s) => (
          <Sequence key={s.idx} from={s.from} durationInFrames={s.frames}>
            {s.asset.kind === 'video' ? (
              <VideoShot asset={s.asset} shotFrames={s.frames} fps={fps}
                seed={`${sceneN}-${s.idx}`} />
            ) : (
              <KenBurnsImage src={staticFile(s.asset.path)}
                durationInFrames={s.frames} seed={`${sceneN}-${s.idx}`} />
            )}
          </Sequence>
        ))}
      </AbsoluteFill>
      <AbsoluteFill style={{background: style.gradeOverlay, pointerEvents: 'none'}} />
      {dim ? (
        <AbsoluteFill style={{background: 'rgba(6,10,20,0.55)'}} />
      ) : null}
    </AbsoluteFill>
  );
};

// ── Lower third (3 variants) ───────────────────────────────────────────
export const LowerThird: React.FC<{title: string; style: StylePack}> = ({
  title,
  style,
}) => {
  const frame = useCurrentFrame();
  const {fps, height, width} = useVideoConfig();
  const appear = spring({frame: frame - 8, fps, config: {damping: 200, stiffness: 120}});
  const hold = 2.6 * fps;
  const exit = interpolate(frame, [hold, hold + 12], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const x = interpolate(appear, [0, 1], [-420, 0]) - exit * 480;
  const s = Math.max(width, height) / 1920;
  const v = style.lowerThirdVariant;

  const inner =
    v === 'chip' ? (
      <div style={{
        background: style.accent, color: '#0A1428',
        fontSize: 32 * s, fontWeight: 800, letterSpacing: 0.5,
        padding: `${10 * s}px ${22 * s}px`,
        borderRadius: 999, lineHeight: 1.45,
      }}>{title}</div>
    ) : v === 'underline' ? (
      <div style={{display: 'flex', flexDirection: 'column', gap: 6 * s}}>
        <div style={{
          color: BRAND.text, fontSize: 34 * s, fontWeight: 600,
          letterSpacing: 1, lineHeight: 1.45,
          textShadow: '0 2px 14px rgba(0,0,0,0.8)',
        }}>{title}</div>
        <div style={{height: 3 * s, width: 120 * s, background: style.accent}} />
      </div>
    ) : (
      <div style={{display: 'flex', alignItems: 'center', gap: 16 * s}}>
        <div style={{width: 10 * s, height: 54 * s, background: style.accent,
          borderRadius: 3 * s}} />
        <div style={{
          color: 'white', fontSize: 34 * s, fontWeight: 700, letterSpacing: 0.5,
          lineHeight: 1.45, textShadow: '0 2px 12px rgba(0,0,0,0.75)',
          background: 'rgba(8,10,18,0.45)', padding: `${8 * s}px ${18 * s}px`,
          borderRadius: 8 * s,
        }}>{title}</div>
      </div>
    );

  return (
    <div style={{
      position: 'absolute', left: 56 * s, top: height * 0.08,
      transform: `translateX(${x * s}px)`, opacity: Math.min(appear, 1 - exit),
      fontFamily,
    }}>{inner}</div>
  );
};

// ── Captions (4 variants) ──────────────────────────────────────────────
export const CaptionsLayer: React.FC<{
  captions: {start: number; end: number; text: string}[];
  style: StylePack;
  yFrac?: number;
  compactYFrac?: number;
  compactRanges?: {start: number; end: number}[];
}> = ({captions, style, yFrac, compactYFrac, compactRanges = []}) => {
  const {fps, height, width} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  return (
    <AbsoluteFill>
      {captions.map((c, i) => {
        const from = Math.round(c.start * fps);
        const dur = Math.max(Math.round((c.end - c.start) * fps), 2);
        const midpoint = (c.start + c.end) / 2;
        const compact = compactRanges.some((r) => midpoint >= r.start && midpoint <= r.end);
        return (
          <Sequence key={i} from={from} durationInFrames={dur}>
            <CaptionChunk text={c.text} style={style}
              y={height * (compact ? (compactYFrac ?? 0.84) : (yFrac ?? 0.78))}
              s={s} durFrames={dur} compact={compact} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const CaptionChunk: React.FC<{
  text: string;
  style: StylePack;
  y: number;
  s: number;
  durFrames: number;
  compact: boolean;
}> = ({text, style, y, s, durFrames, compact}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 14, stiffness: 240, mass: 0.6}});
  const scale = interpolate(pop, [0, 1], [0.84, 1]);
  const captionScale = compact ? 0.72 : 1;
  const v = style.captionVariant;
  const stroke =
    '0 3px 0 rgba(0,0,0,0.85), 0 -2px 0 rgba(0,0,0,0.85), 3px 0 0 rgba(0,0,0,0.85), -3px 0 0 rgba(0,0,0,0.85), 0 6px 24px rgba(0,0,0,0.6)';

  // ── karaoke timing: words appear as spoken, active word in accent ──
  const words = text.split(/\s+/).filter(Boolean);
  const lens = words.map((w) => w.length + 1);
  const totalLen = lens.reduce((a, b) => a + b, 0) || 1;
  let acc = 0;
  const starts = lens.map((l) => {
    const st = (acc / totalLen) * Math.max(durFrames - 3, 1);
    acc += l;
    return st;
  });
  let active = 0;
  for (let i = 0; i < starts.length; i++) {
    if (frame >= starts[i]) active = i;
  }
  const kineticWords = (fontSize: number, doneColor: string, shadow?: string) => (
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center',
      columnGap: 13 * s, rowGap: 4 * s, lineHeight: 1.35, textAlign: 'center'}}>
      {words.map((w, i) => {
        const wpop = spring({frame: frame - starts[i], fps,
          config: {damping: 15, stiffness: 260, mass: 0.5}});
        const isActive = i === active;
        return (
          <span key={i} style={{
            display: 'inline-block',
            fontSize: fontSize * s, fontWeight: 800,
            color: isActive ? style.accent : doneColor,
            transform: `translateY(${interpolate(wpop, [0, 1], [16, 0])}px) scale(${isActive ? 1.06 : 1})`,
            opacity: wpop,
            textShadow: shadow,
          }}>{w}</span>
        );
      })}
    </div>
  );

  const body =
    v === 'boxed' ? (
      <div style={{
        background: 'rgba(8,13,26,0.88)', textAlign: 'center',
        padding: `${12 * s}px ${28 * s}px`, borderRadius: 12 * s,
        borderLeft: `${8 * s}px solid ${style.accent}`,
      }}>{kineticWords(60 * captionScale, 'white')}</div>
    ) : v === 'minimal' ? (
      <div style={{
        color: BRAND.text, fontSize: 50 * captionScale * s, fontWeight: 600, letterSpacing: 0.4,
        textAlign: 'center', lineHeight: 1.4, textShadow: '0 3px 18px rgba(0,0,0,0.9)',
        borderBottom: `${3 * s}px solid ${style.accent}`, paddingBottom: 8 * s,
      }}>{text}</div>
    ) : v === 'chip' ? (
      <div style={{
        background: style.accent, color: '#0A1428', fontSize: 54 * captionScale * s,
        fontWeight: 900, textAlign: 'center', lineHeight: 1.35,
        padding: `${8 * s}px ${24 * s}px`, borderRadius: 8 * s,
        boxShadow: '0 8px 30px rgba(0,0,0,0.55)',
      }}>{text}</div>
    ) : (
      <div style={{textAlign: 'center'}}>
        {kineticWords(58 * captionScale, 'white', stroke)}
        <div style={{
          height: 6 * s, width: `${interpolate(pop, [0, 1], [0, 34])}%`,
          background: style.accent, borderRadius: 3, margin: '8px auto 0',
        }} />
      </div>
    );

  return (
    <div style={{position: 'absolute', top: y, width: '100%', display: 'flex',
      justifyContent: 'center', fontFamily}}>
      <div style={{transform: `scale(${scale})`, opacity: pop, maxWidth: '78%'}}>
        {body}
      </div>
    </div>
  );
};

// ── Kinetic typography scene overlay ───────────────────────────────────
// letterSpacing 0 + roomier lineHeight: negative tracking and tight leading
// break Devanagari matras/conjuncts.
export const KineticText: React.FC<{text: string; style: StylePack}> = ({
  text,
  style,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  const words = text.split(/\s+/).filter(Boolean).slice(0, 8);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center',
      fontFamily, padding: `0 ${120 * s}px`}}>
      <div style={{display: 'flex', flexWrap: 'wrap', gap: 22 * s,
        justifyContent: 'center'}}>
        {words.map((w, i) => {
          const pop = spring({frame: frame - 6 - i * 5, fps,
            config: {damping: 13, stiffness: 200, mass: 0.7}});
          const highlight = i === words.length - 1 || /\d/.test(w);
          return (
            <span key={i} style={{
              display: 'inline-block',
              transform: `translateY(${interpolate(pop, [0, 1], [70, 0])}px) scale(${interpolate(pop, [0, 1], [0.8, 1])})`,
              opacity: pop,
              color: highlight ? style.accent : 'white',
              fontSize: 118 * s, fontWeight: 900, letterSpacing: 0,
              lineHeight: 1.25,
              textShadow: '0 10px 44px rgba(0,0,0,0.75)',
            }}>{w}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ── Animated stat / infographic card ───────────────────────────────────
export const StatCard: React.FC<{
  stat: {value?: number; suffix?: string; label?: string};
  style: StylePack;
}> = ({stat, style}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  const value = Number(stat.value ?? 0);
  const shown = interpolate(frame, [8, 8 + 1.6 * fps], [0, value],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const display = Math.abs(value) >= 100 || Number.isInteger(value)
    ? Math.round(shown).toLocaleString('en-IN')
    : shown.toFixed(1);
  const rise = spring({frame: frame - 4, fps, config: {damping: 200, stiffness: 90}});
  const barW = interpolate(frame, [10, 10 + 1.6 * fps], [0, 380],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily}}>
      <div style={{
        transform: `translateY(${interpolate(rise, [0, 1], [60, 0])}px)`,
        opacity: rise, background: 'rgba(10,20,40,0.82)',
        border: `${2 * s}px solid rgba(255,176,32,0.35)`,
        borderRadius: 24 * s, padding: `${44 * s}px ${80 * s}px`,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 14 * s, boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
      }}>
        <div style={{fontSize: 170 * s, fontWeight: 900, color: style.accent,
          letterSpacing: -3, lineHeight: 1}}>
          {display}{stat.suffix ?? ''}
        </div>
        <div style={{height: 6 * s, width: barW * s, background: style.accent2,
          borderRadius: 3}} />
        <div style={{fontSize: 40 * s, fontWeight: 600, color: BRAND.text,
          textAlign: 'center', maxWidth: 760 * s, lineHeight: 1.4}}>
          {stat.label ?? ''}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Brand: corner watermark + outro end card ───────────────────────────
export const Watermark: React.FC<{
  src: string;
  opacity: number;
  corner?: 'br' | 'tl';
}> = ({src, opacity, corner}) => {
  const {width, height} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  const place =
    corner === 'tl'
      ? {left: 36 * s, top: 36 * s}
      : {right: 40 * s, bottom: 36 * s};
  return (
    <Img src={staticFile(src)} style={{
      position: 'absolute', ...place,
      width: 92 * s, height: 92 * s, opacity, pointerEvents: 'none',
    }} />
  );
};

export const Outro: React.FC<{
  brandName: string;
  tagline: string; // accepted for manifest compatibility, intentionally not shown
  style: StylePack;
  watermarkPath: string | null;
}> = ({brandName, style, watermarkPath}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  const inSpring = spring({frame: frame - 4, fps, config: {damping: 200, stiffness: 110}});
  return (
    <AbsoluteFill style={{
      background: `radial-gradient(ellipse at 50% 35%, ${BRAND.panel} 0%, ${BRAND.navy} 70%)`,
      justifyContent: 'center', alignItems: 'center', fontFamily,
    }}>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 26 * s, transform: `scale(${interpolate(inSpring, [0, 1], [0.92, 1])})`,
        opacity: inSpring}}>
        {watermarkPath ? (
          <Img src={staticFile(watermarkPath)}
            style={{width: 170 * s, height: 170 * s, opacity: 0.97}} />
        ) : null}
        <div style={{fontSize: 96 * s, fontWeight: 900, letterSpacing: 10,
          color: BRAND.text, textTransform: 'uppercase'}}>{brandName}</div>
        <div style={{height: 4 * s, width: 220 * s, background: style.accent}} />
      </div>
    </AbsoluteFill>
  );
};

// ── Cinematic overlays (grain + vignette) + light leak + progress ──────
const GRAIN =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2"/></filter><rect width="240" height="240" filter="url(%23n)" opacity="0.6"/></svg>`
  );

export const CinematicOverlay: React.FC = () => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    <AbsoluteFill style={{
      background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 58%, rgba(0,0,0,0.38) 100%)',
    }} />
    <AbsoluteFill style={{
      backgroundImage: `url("${GRAIN}")`, backgroundRepeat: 'repeat',
      opacity: 0.05, mixBlendMode: 'overlay',
    }} />
  </AbsoluteFill>
);

export const LightLeak: React.FC<{seed: string}> = ({seed}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  if (random(`leak-${seed}`) > 0.45) return null;
  const sweepFrames = 26;
  if (frame > sweepFrames) return null;
  const x = interpolate(frame, [0, sweepFrames], [-width * 0.6, width * 1.2]);
  const opacity = interpolate(frame, [0, 6, sweepFrames], [0, 0.28, 0]);
  return (
    <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden'}}>
      <div style={{
        position: 'absolute', top: '-20%', left: x, width: width * 0.45,
        height: '140%', transform: 'rotate(14deg)',
        background: 'linear-gradient(90deg, rgba(255,190,90,0) 0%, rgba(255,200,110,0.9) 50%, rgba(255,190,90,0) 100%)',
        filter: 'blur(28px)', opacity,
      }} />
    </AbsoluteFill>
  );
};

// ── Sound design: whooshes / risers / hits from the manifest ───────────
export const SfxLayer: React.FC<{
  events: {path: string; start: number; volume: number}[];
  fps: number;
}> = ({events, fps}) => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    {(events ?? []).map((e, i) => (
      <Sequence key={i} from={Math.max(Math.round(e.start * fps), 0)}>
        <Audio src={staticFile(e.path)} volume={e.volume} />
      </Sequence>
    ))}
  </AbsoluteFill>
);

export const ProgressBar: React.FC<{accent: string}> = ({accent}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return (
    <div style={{
      position: 'absolute', top: 0, left: 0, height: 8,
      width: `${(frame / Math.max(durationInFrames - 1, 1)) * 100}%`,
      background: accent, opacity: 0.9,
    }} />
  );
};
