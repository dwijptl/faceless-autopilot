import React from 'react';
import {
  AbsoluteFill,
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

// ── Font (Google Fonts, loaded at render time; safe fallback) ──────────
let FONT = 'Inter, -apple-system, "DejaVu Sans", sans-serif';
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const {loadFont} = require('@remotion/google-fonts/Inter');
  const loaded = loadFont();
  FONT = `${loaded.fontFamily}, sans-serif`;
} catch {
  // keep system fallback
}
export const fontFamily = FONT;

type Asset = {path: string; kind: string; duration?: number};

// ── Ken Burns still: slow zoom + drift, alternating direction ─────────
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

// ── Video shot: cover-fit, gentle push-in, loops if clip is short ─────
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

// ── Scene visual: chops the scene into shots across its assets ────────
export const SceneVisual: React.FC<{
  assets: Asset[];
  sceneFrames: number;
  fps: number;
  maxShotSeconds: number;
  sceneN: number;
}> = ({assets, sceneFrames, fps, maxShotSeconds, sceneN}) => {
  const maxShot = Math.round(maxShotSeconds * fps);
  const shots: {from: number; frames: number; asset: Asset; idx: number}[] = [];
  let cursor = 0;
  let i = 0;
  while (cursor < sceneFrames) {
    const remaining = sceneFrames - cursor;
    const frames = remaining < maxShot * 1.5 ? remaining : maxShot;
    shots.push({from: cursor, frames, asset: assets[i % assets.length], idx: i});
    cursor += frames;
    i += 1;
    if (i > 200) break; // safety
  }
  return (
    <AbsoluteFill style={{backgroundColor: '#0b0f1a'}}>
      {shots.map((s) => (
        <Sequence key={s.idx} from={s.from} durationInFrames={s.frames}>
          {s.asset.kind === 'video' ? (
            <VideoShot
              asset={s.asset}
              shotFrames={s.frames}
              fps={fps}
              seed={`${sceneN}-${s.idx}`}
            />
          ) : (
            <KenBurnsImage
              src={staticFile(s.asset.path)}
              durationInFrames={s.frames}
              seed={`${sceneN}-${s.idx}`}
            />
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

// ── Lower third scene title: springs in, slides away ──────────────────
export const LowerThird: React.FC<{title: string; accent: string}> = ({
  title,
  accent,
}) => {
  const frame = useCurrentFrame();
  const {fps, height, width} = useVideoConfig();
  const appear = spring({frame: frame - 8, fps, config: {damping: 200, stiffness: 120}});
  const hold = 2.6 * fps;
  const exit = interpolate(frame, [hold, hold + 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const x = interpolate(appear, [0, 1], [-420, 0]) - exit * 480;
  const scaleUi = width / 1920;
  return (
    <div
      style={{
        position: 'absolute',
        left: 56 * scaleUi,
        top: height * 0.08,
        transform: `translateX(${x * scaleUi}px)`,
        opacity: Math.min(appear, 1 - exit),
        display: 'flex',
        alignItems: 'center',
        gap: 16 * scaleUi,
        fontFamily,
      }}
    >
      <div
        style={{
          width: 10 * scaleUi,
          height: 54 * scaleUi,
          background: accent,
          borderRadius: 3 * scaleUi,
        }}
      />
      <div
        style={{
          color: 'white',
          fontSize: 34 * scaleUi,
          fontWeight: 700,
          letterSpacing: 1.2,
          textTransform: 'uppercase',
          textShadow: '0 2px 12px rgba(0,0,0,0.75)',
          background: 'rgba(8,10,18,0.45)',
          padding: `${8 * scaleUi}px ${18 * scaleUi}px`,
          borderRadius: 8 * scaleUi,
        }}
      >
        {title}
      </div>
    </div>
  );
};

// ── Captions: word-chunks that pop with spring physics ────────────────
export const CaptionsLayer: React.FC<{
  captions: {start: number; end: number; text: string}[];
  accent: string;
}> = ({captions, accent}) => {
  const {fps, height, width} = useVideoConfig();
  const scaleUi = width / 1920;
  return (
    <AbsoluteFill>
      {captions.map((c, i) => {
        const from = Math.round(c.start * fps);
        const dur = Math.max(Math.round((c.end - c.start) * fps), 2);
        return (
          <Sequence key={i} from={from} durationInFrames={dur}>
            <CaptionChunk text={c.text} accent={accent} y={height * 0.78} scaleUi={scaleUi} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const CaptionChunk: React.FC<{
  text: string;
  accent: string;
  y: number;
  scaleUi: number;
}> = ({text, accent, y, scaleUi}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 14, stiffness: 240, mass: 0.6}});
  const scale = interpolate(pop, [0, 1], [0.82, 1]);
  return (
    <div
      style={{
        position: 'absolute',
        top: y,
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        fontFamily,
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          opacity: pop,
          color: 'white',
          fontSize: 58 * scaleUi,
          fontWeight: 800,
          textAlign: 'center',
          maxWidth: '78%',
          lineHeight: 1.25,
          textShadow:
            '0 3px 0 rgba(0,0,0,0.85), 0 -2px 0 rgba(0,0,0,0.85), 3px 0 0 rgba(0,0,0,0.85), -3px 0 0 rgba(0,0,0,0.85), 0 6px 24px rgba(0,0,0,0.6)',
        }}
      >
        {text}
        <div
          style={{
            height: 6 * scaleUi,
            width: `${interpolate(pop, [0, 1], [0, 34])}%`,
            background: accent,
            borderRadius: 3,
            margin: '6px auto 0',
          }}
        />
      </div>
    </div>
  );
};

// ── Cinematic overlays: vignette + film grain + light leak ────────────
const GRAIN =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2"/></filter><rect width="240" height="240" filter="url(%23n)" opacity="0.6"/></svg>`
  );

export const CinematicOverlay: React.FC = () => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    <AbsoluteFill
      style={{
        background:
          'radial-gradient(ellipse at center, rgba(0,0,0,0) 58%, rgba(0,0,0,0.38) 100%)',
      }}
    />
    <AbsoluteFill
      style={{
        backgroundImage: `url("${GRAIN}")`,
        backgroundRepeat: 'repeat',
        opacity: 0.05,
        mixBlendMode: 'overlay',
      }}
    />
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
      <div
        style={{
          position: 'absolute',
          top: '-20%',
          left: x,
          width: width * 0.45,
          height: '140%',
          transform: 'rotate(14deg)',
          background:
            'linear-gradient(90deg, rgba(255,190,90,0) 0%, rgba(255,200,110,0.9) 50%, rgba(255,190,90,0) 100%)',
          filter: 'blur(28px)',
          opacity,
        }}
      />
    </AbsoluteFill>
  );
};

export const ProgressBar: React.FC<{accent: string}> = ({accent}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        height: 8,
        width: `${(frame / Math.max(durationInFrames - 1, 1)) * 100}%`,
        background: accent,
        opacity: 0.9,
      }}
    />
  );
};
