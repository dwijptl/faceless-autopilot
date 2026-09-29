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
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {StylePack} from './styles';
import {stackFor} from './fonts';

// ── Fonts ──────────────────────────────────────────────────────────────
export const headingFamily = (style?: StylePack): string =>
  stackFor(style?.fontHeading);
export const bodyFamily = (style?: StylePack): string =>
  stackFor(style?.fontBody);

type Asset = {
  path: string; kind: string; duration?: number; ai?: boolean;
  family?: string; sourcePolicy?: string;
};
type VisualBeat = {
  start: number; duration: number; assets: Asset[];
  fromFrame?: number; durationFrames?: number;
  family?: string; sourcePolicy?: string;
};

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

// ── Full-frame scene media ─────────────────────────────────────────────
export const SceneVisual: React.FC<{
  assets: Asset[];
  visualBeats?: VisualBeat[];
  sceneFrames: number;
  fps: number;
  maxShotSeconds: number;
  sceneN: number;
  style: StylePack;
  splitLongBeats?: boolean;
}> = ({assets, visualBeats = [], sceneFrames, fps, maxShotSeconds, sceneN, style,
  splitLongBeats = true}) => {
  const maxShot = Math.round(maxShotSeconds * fps);
  const shots: {from: number; frames: number; asset: Asset; idx: number;
    sourcePolicy?: string}[] = [];
  const addShots = (from: number, frames: number, pool: Asset[],
    seedOffset: number, sourcePolicy?: string) => {
    if (frames <= 0 || pool.length === 0) return;
    const count = splitLongBeats
      ? Math.max(1, Math.ceil(frames / Math.max(maxShot, 1)))
      : 1;
    const base = Math.floor(frames / count);
    let cursor = 0;
    for (let i = 0; i < count; i++) {
      const length = base + (i < frames % count ? 1 : 0);
      shots.push({from: from + cursor, frames: length,
        asset: pool[i % pool.length], idx: seedOffset + i, sourcePolicy});
      cursor += length;
    }
  };
  if (visualBeats.length > 0) {
    // Quantize shared boundaries, not each beat's start and duration
    // independently.  Independent rounding can leave a one-frame hole that
    // exposes the solid scene background between otherwise contiguous shots.
    const starts = visualBeats.map((beat) => Math.min(Math.max(
      beat.fromFrame ?? Math.round(beat.start * fps), 0), sceneFrames));
    starts[0] = 0;
    for (let index = 1; index < starts.length; index++) {
      starts[index] = Math.max(starts[index], starts[index - 1]);
    }
    visualBeats.forEach((beat, index) => {
      const from = starts[index];
      const end = index + 1 < starts.length ? starts[index + 1] : sceneFrames;
      const frames = Math.max(end - from, 1);
      addShots(from, frames, beat.assets?.length ? beat.assets : assets,
        index * 100, beat.sourcePolicy);
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
            {s.sourcePolicy === 'custom' && s.asset.ai ? (
              <div style={{position: 'absolute', top: 34, right: 42,
                color: 'rgba(255,255,255,0.78)',
                fontFamily: bodyFamily(style), fontSize: 22, fontWeight: 600,
                letterSpacing: 1.2,
                textShadow: '0 2px 6px rgba(0,0,0,0.95)'}}>दृश्य पुनर्निर्माण</div>
            ) : null}
          </Sequence>
        ))}
      </AbsoluteFill>
      <AbsoluteFill style={{background: style.gradeOverlay, pointerEvents: 'none',
        opacity: 1}} />
    </AbsoluteFill>
  );
};

// ── Plain captions ────────────────────────────────────────────────────
export const CaptionsLayer: React.FC<{
  captions: {start: number; end: number; text: string}[];
  style: StylePack;
  yFrac?: number;
  sizeBoost?: number;
}> = ({captions, style, yFrac = 0.78, sizeBoost = 1}) => {
  const {fps, height, width} = useVideoConfig();
  const s = Math.max(width, height) / 1920;
  return (
    <AbsoluteFill>
      {captions.map((c, i) => {
        const from = Math.round(c.start * fps);
        const dur = Math.max(Math.round((c.end - c.start) * fps), 2);
        return (
          <Sequence key={i} from={from} durationInFrames={dur}>
            <CaptionChunk text={c.text} style={style}
              y={height * Math.min(Math.max(yFrac, 0.5), 0.9)}
              s={s} durFrames={dur} sizeBoost={sizeBoost} />
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
  sizeBoost: number;
}> = ({text, style, y, s, durFrames, sizeBoost}) => {
  const frame = useCurrentFrame();
  const fadeFrames = Math.min(7, Math.max(Math.floor(durFrames / 3), 2));
  const opacity = interpolate(
    frame,
    [0, fadeFrames, Math.max(durFrames - fadeFrames, fadeFrames + 1), durFrames - 1],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', top: y, width: '100%', display: 'flex',
      justifyContent: 'center', opacity, fontFamily: bodyFamily(style)}}>
      <div style={{
        maxWidth: '88%', padding: `${4 * s}px ${16 * s}px`,
        color: 'white', fontSize: 48 * sizeBoost * s, fontWeight: 650,
        textAlign: 'center', lineHeight: 1.42,
        textShadow: '0 3px 5px rgba(0,0,0,0.95), 0 8px 24px rgba(0,0,0,0.78)',
      }}>
        {text}
      </div>
    </div>
  );
};

// ── Minimal corner watermark ─────────────────────────────────────────
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
