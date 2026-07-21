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
import {BRAND, StylePack, hexA} from './styles';
import {stackFor} from './fonts';
import {DEFAULT_VARIATION, Variation} from './variation';

// ── Fonts ──────────────────────────────────────────────────────────────
// Each style pack declares its own heading/body pairing (fonts.ts loads
// them lazily — all Devanagari-capable). `fontFamily` stays exported as
// the brand-neutral default for components with no pack context.
export const fontFamily = stackFor('Inter');
export const headingFamily = (style?: StylePack): string =>
  stackFor(style?.fontHeading);
export const bodyFamily = (style?: StylePack): string =>
  stackFor(style?.fontBody);

type Asset = {path: string; kind: string; duration?: number; ai?: boolean};
type VisualBeat = {start: number; duration: number; assets: Asset[]};

// ── Ken Burns still ────────────────────────────────────────────────────
export const KenBurnsImage: React.FC<{
  src: string;
  durationInFrames: number;
  seed: string;
  energy?: number; // pack motion DNA: 0.6 calm drift – 1.5 punchy push
}> = ({src, durationInFrames, seed, energy = 1}) => {
  const frame = useCurrentFrame();
  const e = Math.min(Math.max(energy, 0.4), 1.6);
  const zoomIn = random(`kb-${seed}`) < 0.5;
  const driftX = (random(`dx-${seed}`) - 0.5) * 60 * e;
  const driftY = (random(`dy-${seed}`) - 0.5) * 40 * e;
  const t = frame / Math.max(durationInFrames, 1);
  const lo = 1.04 + 0.02 * e;
  const hi = lo + 0.12 * e;
  const scale = zoomIn
    ? interpolate(t, [0, 1], [lo, hi])
    : interpolate(t, [0, 1], [hi, lo]);
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

// ── Parallax Ken Burns: fake 2.5D depth for AI signature stills ────────
// Two layers of the same image: a soft oversized background drifting slowly
// and a sharp foreground moving faster with a subtle counter-rotation —
// reads as a camera moving through space rather than a flat zoom.
export const ParallaxKenBurns: React.FC<{
  src: string;
  durationInFrames: number;
  seed: string;
  energy?: number; // pack motion DNA
}> = ({src, durationInFrames, seed, energy = 1}) => {
  const frame = useCurrentFrame();
  const e = Math.min(Math.max(energy, 0.4), 1.6);
  const t = frame / Math.max(durationInFrames, 1);
  const dirX = random(`px-${seed}`) < 0.5 ? 1 : -1;
  const dirY = random(`py-${seed}`) < 0.5 ? 1 : -1;
  const zoomIn = random(`pz-${seed}`) < 0.6;
  const fgLo = 1.06 + 0.04 * e;
  const fgHi = fgLo + 0.14 * e;
  const fgScale = zoomIn
    ? interpolate(t, [0, 1], [fgLo, fgHi])
    : interpolate(t, [0, 1], [fgHi, fgLo]);
  const bgScale = zoomIn
    ? interpolate(t, [0, 1], [1.3, 1.3 + 0.06 * e])
    : interpolate(t, [0, 1], [1.3 + 0.06 * e, 1.3]);
  const fgX = dirX * interpolate(t, [0, 1], [0, 42 * e]);
  const fgY = dirY * interpolate(t, [0, 1], [0, 26 * e]);
  const rot = dirX * interpolate(t, [0, 1], [0, 0.5 * e]);
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Img
        src={src}
        style={{
          position: 'absolute', width: '100%', height: '100%',
          objectFit: 'cover', filter: 'blur(9px) brightness(0.75)',
          transform: `scale(${bgScale}) translate(${-fgX * 0.35}px, ${-fgY * 0.35}px)`,
        }}
      />
      <Img
        src={src}
        style={{
          position: 'absolute', width: '100%', height: '100%',
          objectFit: 'cover',
          transform: `scale(${fgScale}) translate(${fgX}px, ${fgY}px) rotate(${rot}deg)`,
          maskImage:
            'radial-gradient(ellipse 78% 78% at 50% 50%, black 55%, transparent 100%)',
          WebkitMaskImage:
            'radial-gradient(ellipse 78% 78% at 50% 50%, black 55%, transparent 100%)',
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
  visualBeats?: VisualBeat[];
  sceneFrames: number;
  fps: number;
  maxShotSeconds: number;
  sceneN: number;
  style: StylePack;
  dim?: boolean; // for kinetic/stat overlay scenes
  gradeOpacity?: number; // per-video jitter (variation.ts)
}> = ({assets, visualBeats = [], sceneFrames, fps, maxShotSeconds, sceneN, style, dim,
  gradeOpacity}) => {
  const maxShot = Math.round(maxShotSeconds * fps);
  const shots: {from: number; frames: number; asset: Asset; idx: number}[] = [];
  const addShots = (from: number, frames: number, pool: Asset[], seedOffset: number) => {
    if (frames <= 0 || pool.length === 0) return;
    const count = Math.max(1, Math.ceil(frames / Math.max(maxShot, 1)));
    const base = Math.floor(frames / count);
    let cursor = 0;
    for (let i = 0; i < count; i++) {
      const length = base + (i < frames % count ? 1 : 0);
      shots.push({from: from + cursor, frames: length,
        asset: pool[i % pool.length], idx: seedOffset + i});
      cursor += length;
    }
  };
  if (visualBeats.length > 0) {
    visualBeats.forEach((beat, index) => {
      const from = Math.max(0, Math.round(beat.start * fps));
      const frames = Math.min(Math.max(Math.round(beat.duration * fps), 1),
        Math.max(sceneFrames - from, 0));
      addShots(from, frames, beat.assets?.length ? beat.assets : assets, index * 100);
    });
  } else {
    addShots(0, sceneFrames, assets, 0);
  }
  return (
    <AbsoluteFill style={{backgroundColor: style.bg}}>
      <AbsoluteFill style={{filter: style.visualFilter}}>
        {shots.map((s) => (
          <Sequence key={s.idx} from={s.from} durationInFrames={s.frames}>
            {s.asset.kind === 'video' ? (
              <VideoShot asset={s.asset} shotFrames={s.frames} fps={fps}
                seed={`${sceneN}-${s.idx}`} />
            ) : s.asset.ai ? (
              <ParallaxKenBurns src={staticFile(s.asset.path)}
                durationInFrames={s.frames} seed={`${sceneN}-${s.idx}`}
                energy={style.motion?.kenBurns} />
            ) : (
              <KenBurnsImage src={staticFile(s.asset.path)}
                durationInFrames={s.frames} seed={`${sceneN}-${s.idx}`}
                energy={style.motion?.kenBurns} />
            )}
          </Sequence>
        ))}
      </AbsoluteFill>
      <AbsoluteFill style={{background: style.gradeOverlay, pointerEvents: 'none',
        opacity: Math.min(gradeOpacity ?? 1, 1.5)}} />
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

// ── Captions (12 variants — see styles.ts CaptionVariant) ──────────────
export const CaptionsLayer: React.FC<{
  captions: {start: number; end: number; text: string}[];
  style: StylePack;
  yFrac?: number;
  compactYFrac?: number;
  compactRanges?: {start: number; end: number}[];
  sizeBoost?: number; // long-form mobile readability multiplier
  variation?: Variation; // per-video jitter (variation.ts)
}> = ({captions, style, yFrac, compactYFrac, compactRanges = [], sizeBoost,
  variation}) => {
  const {fps, height, width} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  const vr = variation ?? DEFAULT_VARIATION;
  const clampY = (f: number) => Math.min(Math.max(f + vr.captionYOff, 0.5), 0.9);
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
              y={height * clampY(compact ? (compactYFrac ?? 0.84)
                : (yFrac ?? style.layout?.captionY ?? 0.78))}
              s={s} durFrames={dur} compact={compact}
              sizeBoost={(sizeBoost ?? 1) * vr.captionScale}
              maxW={vr.captionMaxW} tiltSeed={vr.tiltSeed} chunkIndex={i} />
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
  sizeBoost: number;
  maxW: number;
  tiltSeed: string;
  chunkIndex: number;
}> = ({text, style, y, s, durFrames, compact, sizeBoost, maxW, tiltSeed,
  chunkIndex}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 14, stiffness: 240, mass: 0.6}});
  const scale = interpolate(pop, [0, 1], [0.84, 1]);
  const captionScale = (compact ? 0.72 : 1) * sizeBoost;
  const align = style.layout?.captionAlign ?? 'center';
  const alignJustify = align === 'left' ? 'flex-start'
    : align === 'right' ? 'flex-end' : 'center';
  const font = bodyFamily(style);
  const serifFont = headingFamily(style);
  const v = style.captionVariant;
  const stroke =
    '0 3px 0 rgba(0,0,0,0.85), 0 -2px 0 rgba(0,0,0,0.85), 3px 0 0 rgba(0,0,0,0.85), -3px 0 0 rgba(0,0,0,0.85), 0 6px 24px rgba(0,0,0,0.6)';
  const scrim = hexA(style.panel, 0.86);

  // ── karaoke timing: words appear as spoken, active word in accent ──
  // Word-level only — per-letter animation breaks Devanagari conjuncts.
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
  const kineticWords = (
    fontSize: number, doneColor: string, shadow?: string,
    opts?: {tilt?: boolean; altColor?: string; weight?: number}
  ) => (
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: alignJustify,
      columnGap: 13 * s, rowGap: 4 * s, lineHeight: 1.35, textAlign: align}}>
      {words.map((w, i) => {
        const wpop = spring({frame: frame - starts[i], fps,
          config: {damping: 15, stiffness: 260, mass: 0.5}});
        const isActive = i === active;
        const tilt = opts?.tilt
          ? (random(`${tiltSeed}-${chunkIndex}-${i}`) - 0.5) * 3
          : 0;
        const doneC = opts?.altColor && i % 2 ? opts.altColor : doneColor;
        return (
          <span key={i} style={{
            display: 'inline-block',
            fontSize: fontSize * s, fontWeight: opts?.weight ?? 800,
            color: isActive ? style.accent : doneC,
            transform: `translateY(${interpolate(wpop, [0, 1], [16, 0])}px) scale(${isActive ? 1.06 : 1}) rotate(${tilt}deg)`,
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
        background: scrim, textAlign: 'center',
        padding: `${12 * s}px ${28 * s}px`, borderRadius: 12 * s,
        borderLeft: `${8 * s}px solid ${style.accent}`,
      }}>{kineticWords(60 * captionScale, 'white')}</div>
    ) : v === 'minimal' ? (
      <div style={{
        color: BRAND.text, fontSize: 50 * captionScale * s, fontWeight: 600, letterSpacing: 0.4,
        textAlign: align, lineHeight: 1.4, textShadow: '0 3px 18px rgba(0,0,0,0.9)',
        borderBottom: `${3 * s}px solid ${style.accent}`, paddingBottom: 8 * s,
      }}>{text}</div>
    ) : v === 'chip' ? (
      // Premium high-contrast chip: calm dark scrim + white karaoke words,
      // accent only on the active word and a thin rule.
      <div style={{
        background: scrim, textAlign: 'center',
        padding: `${10 * s}px ${26 * s}px`, borderRadius: 10 * s,
        borderBottom: `${4 * s}px solid ${style.accent}`,
        boxShadow: '0 8px 30px rgba(0,0,0,0.45)',
      }}>{kineticWords(54 * captionScale, 'white')}</div>
    ) : v === 'outline' ? (
      // Huge stroked words, no scrim; seeded per-word tilt reads hand-set.
      <div style={{textAlign: 'center'}}>
        {kineticWords(64 * captionScale, 'white',
          `0 4px 0 rgba(0,0,0,0.9), 0 -3px 0 rgba(0,0,0,0.9), 4px 0 0 rgba(0,0,0,0.9), -4px 0 0 rgba(0,0,0,0.9), 0 10px 34px rgba(0,0,0,0.65)`,
          {tilt: true, weight: 900})}
      </div>
    ) : v === 'serif' ? (
      // Editorial: whole line in the pack's display serif between hairlines.
      <div style={{
        fontFamily: serifFont, color: BRAND.text,
        fontSize: 48 * captionScale * s, fontWeight: 600,
        textAlign: align, lineHeight: 1.45,
        textShadow: '0 3px 20px rgba(0,0,0,0.92)',
        borderTop: `${1.5 * s}px solid ${hexA(style.accent, 0.55)}`,
        borderBottom: `${1.5 * s}px solid ${hexA(style.accent, 0.55)}`,
        padding: `${10 * s}px ${34 * s}px`,
      }}>{text}</div>
    ) : v === 'ribbon' ? (
      // Broadcast band: full-width strip, live-dot, left-aligned karaoke.
      <div style={{
        width: width * 0.94, display: 'flex', alignItems: 'center',
        gap: 20 * s, background: `linear-gradient(90deg, ${hexA(style.panel, 0.94)} 0%, ${hexA(style.panel, 0.72)} 78%, transparent 100%)`,
        borderLeft: `${10 * s}px solid ${style.accent}`,
        padding: `${12 * s}px ${26 * s}px`,
      }}>
        <div style={{width: 16 * s, height: 16 * s, borderRadius: '50%',
          background: style.accent, flexShrink: 0,
          opacity: 0.55 + 0.45 * Math.sin(frame / 5) ** 2}} />
        {kineticWords(48 * captionScale, 'white', undefined, {weight: 700})}
      </div>
    ) : v === 'glow' ? (
      <div style={{
        background: 'rgba(2,4,8,0.42)', borderRadius: 14 * s,
        padding: `${10 * s}px ${28 * s}px`, textAlign: 'center',
      }}>{kineticWords(56 * captionScale, 'white',
        `0 0 ${18 * s}px ${hexA(style.accent, 0.85)}, 0 0 ${46 * s}px ${hexA(style.accent, 0.4)}, 0 3px 14px rgba(0,0,0,0.9)`,
        {weight: 800})}</div>
    ) : v === 'ledger' ? (
      // Field-notes column: left-aligned, vertical rule, no karaoke.
      <div style={{
        display: 'flex', gap: 18 * s, alignItems: 'stretch',
        background: hexA(style.panel, 0.78), borderRadius: 8 * s,
        padding: `${12 * s}px ${24 * s}px`,
      }}>
        <div style={{width: 5 * s, background: style.accent, borderRadius: 3,
          flexShrink: 0}} />
        <div style={{
          color: BRAND.text, fontSize: 44 * captionScale * s, fontWeight: 600,
          textAlign: 'left', lineHeight: 1.42, maxWidth: 1100 * s,
        }}>{text}</div>
      </div>
    ) : v === 'stamp' ? (
      <div style={{
        background: hexA(style.panel, 0.88), textAlign: 'center',
        border: `${5 * s}px double ${hexA(style.accent, 0.85)}`,
        padding: `${12 * s}px ${30 * s}px`,
        transform: `rotate(${(random(`${tiltSeed}-st-${chunkIndex}`) - 0.5) * 2.4}deg)`,
        boxShadow: `${8 * s}px ${8 * s}px 0 ${hexA(style.accent, 0.14)}`,
      }}>{kineticWords(52 * captionScale, 'white')}</div>
    ) : v === 'duotone' ? (
      // Two-tone alternating words, heavy shadow, no box — big and loud.
      <div style={{textAlign: 'center'}}>
        {kineticWords(62 * captionScale, 'white',
          '0 8px 26px rgba(0,0,0,0.92), 0 2px 6px rgba(0,0,0,0.9)',
          {altColor: style.accent2, weight: 900})}
      </div>
    ) : v === 'band' ? (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 18 * s,
        background: hexA(style.panel, 0.9), borderRadius: 6 * s,
        borderTop: `${4 * s}px solid ${style.accent}`,
        padding: `${10 * s}px ${26 * s}px`,
        boxShadow: '0 10px 34px rgba(0,0,0,0.5)',
      }}>
        <div style={{width: 12 * s, height: 34 * s, background: style.accent,
          borderRadius: 3, flexShrink: 0}} />
        {kineticWords(50 * captionScale, 'white', undefined, {weight: 750})}
      </div>
    ) : (
      // 'pop' default: stroked karaoke + growing accent underline
      <div style={{textAlign: 'center'}}>
        {kineticWords(58 * captionScale, 'white', stroke)}
        <div style={{
          height: 6 * s, width: `${interpolate(pop, [0, 1], [0, 34])}%`,
          background: style.accent, borderRadius: 3, margin: '8px auto 0',
        }} />
      </div>
    );

  // pack motion DNA: how the caption ENTERS
  const entry = style.motion?.entry ?? 'pop';
  const riseSpring = spring({frame, fps,
    config: {damping: 19, stiffness: 130, mass: 0.8}});
  const fadeIn = interpolate(frame, [0, 9], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const slideFrom = align === 'right' ? 70 : -70;
  const enterStyle: React.CSSProperties =
    entry === 'fade' ? {opacity: fadeIn}
    : entry === 'rise' ? {opacity: riseSpring,
        transform: `translateY(${interpolate(riseSpring, [0, 1], [26, 0])}px)`}
    : entry === 'slide' ? {opacity: riseSpring,
        transform: `translateX(${interpolate(riseSpring, [0, 1], [slideFrom, 0])}px)`}
    : {opacity: pop, transform: `scale(${scale})`};
  return (
    <div style={{position: 'absolute', top: y, width: '100%', display: 'flex',
      justifyContent: alignJustify,
      padding: align === 'center' ? 0 : `0 ${Math.round(width * 0.045)}px`,
      fontFamily: font}}>
      <div style={{...enterStyle, maxWidth: `${Math.round(maxW * 100)}%`}}>
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
  corner?: 'br' | 'bl' | 'tl' | 'tr';
}> = ({src, opacity, corner}) => {
  const {width, height} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  const place =
    corner === 'tl' ? {left: 36 * s, top: 36 * s}
    : corner === 'tr' ? {right: 40 * s, top: 36 * s}
    : corner === 'bl' ? {left: 36 * s, bottom: 36 * s}
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
      background: `radial-gradient(ellipse at 50% 35%, ${style.panel} 0%, ${style.bg} 70%)`,
      justifyContent: 'center', alignItems: 'center',
      fontFamily: headingFamily(style),
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

// ── Pack textures (grain/vignette/halation/scanlines/paper) ────────────
const GRAIN =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2"/></filter><rect width="240" height="240" filter="url(%23n)" opacity="0.6"/></svg>`
  );

const Vignette: React.FC<{strength: number}> = ({strength}) => (
  <AbsoluteFill style={{
    background: `radial-gradient(ellipse at center, rgba(0,0,0,0) ${strength > 0.4 ? 48 : 58}%, rgba(0,0,0,${strength}) 100%)`,
  }} />
);

const Grain: React.FC<{opacity: number}> = ({opacity}) => (
  <AbsoluteFill style={{
    backgroundImage: `url("${GRAIN}")`, backgroundRepeat: 'repeat',
    opacity, mixBlendMode: 'overlay',
  }} />
);

/** Per-pack finishing layer. Replaces the one-size-fits-all
 * CinematicOverlay: each pack declares its texture, and per-video jitter
 * scales the intensity so no two videos wear it identically. */
export const TextureOverlay: React.FC<{style: StylePack; opacityMul?: number}> =
  ({style, opacityMul}) => {
  const mul = Math.min(Math.max(opacityMul ?? 1, 0.4), 1.6);
  const t = style.texture;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {t === 'none' ? (
        <Vignette strength={0.22 * mul} />
      ) : t === 'vignette' ? (
        <Vignette strength={0.5 * mul} />
      ) : t === 'halation' ? (
        <>
          <Vignette strength={0.3 * mul} />
          <AbsoluteFill style={{
            background: `radial-gradient(ellipse 90% 55% at 50% 8%, ${hexA(style.accent, 0.10 * mul)} 0%, transparent 65%)`,
            mixBlendMode: 'screen',
          }} />
        </>
      ) : t === 'scanlines' ? (
        <>
          <Vignette strength={0.34 * mul} />
          <AbsoluteFill style={{
            background: 'repeating-linear-gradient(180deg, rgba(0,0,0,0.16) 0px, rgba(0,0,0,0.16) 1px, transparent 1px, transparent 4px)',
            opacity: 0.35 * mul,
          }} />
        </>
      ) : t === 'paper' ? (
        <>
          <Vignette strength={0.36 * mul} />
          <AbsoluteFill style={{
            background: '#D8C9A8', opacity: 0.06 * mul,
            mixBlendMode: 'multiply',
          }} />
          <Grain opacity={0.06 * mul} />
        </>
      ) : (
        <>
          <Vignette strength={0.38 * mul} />
          <Grain opacity={0.05 * mul} />
        </>
      )}
    </AbsoluteFill>
  );
};

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

export const ProgressBar: React.FC<{
  accent: string;
  marks?: number[]; // chapter positions as 0-1 fractions
  position?: 'top' | 'bottom';
  thickness?: number;
}> = ({accent, marks, position = 'top', thickness = 8}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const edge = position === 'bottom' ? {bottom: 0} : {top: 0};
  return (
    <>
      <div style={{
        position: 'absolute', ...edge, left: 0, height: thickness,
        width: `${(frame / Math.max(durationInFrames - 1, 1)) * 100}%`,
        background: accent, opacity: 0.9,
      }} />
      {(marks ?? []).map((f, i) => (
        <div key={i} style={{
          position: 'absolute', ...edge, left: `${Math.min(Math.max(f, 0), 1) * 100}%`,
          width: 2, height: thickness, background: 'rgba(244,247,251,0.4)',
        }} />
      ))}
    </>
  );
};
