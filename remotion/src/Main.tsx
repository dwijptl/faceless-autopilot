import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  random,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {wipe} from '@remotion/transitions/wipe';
import type {Manifest} from './Root';
import {MapZoom} from './Map';
import {getStyle, StylePack} from './styles';
import {
  CaptionsLayer,
  CinematicOverlay,
  LightLeak,
  Outro,
  ProgressBar,
  SceneVisual,
  SfxLayer,
  Watermark,
} from './elements';
import {
  AnimatedLowerThird,
  AnimatedStatCard,
  CtaLayer,
  EditorialCard,
  KineticTitle,
  SceneFrame,
} from './motion-library';
import type {MotionSpec} from './motion-library';
import {GlassCard} from './glass';
import {TelemetryHUD} from './hud';

// Deterministic transition choice, biased by the video's style pack.
// Remotion's transition presentations are invariant generic types; this helper
// intentionally mixes slide, fade and wipe presentations at runtime.
const pickTransition = (i: number, style: StylePack): any => {
  const r = random(`tr-${style.name}-${i}`);
  switch (style.transitionBias) {
    case 'slides':
      if (r < 0.5) return slide({direction: 'from-right'});
      if (r < 0.8) return slide({direction: 'from-left'});
      return fade();
    case 'fades':
      return r < 0.85 ? fade() : slide({direction: 'from-right'});
    case 'wipes':
      if (r < 0.45) return wipe({direction: 'from-left'});
      if (r < 0.7) return wipe({direction: 'from-top-left'});
      return fade();
    default:
      if (r < 0.45) return fade();
      if (r < 0.65) return slide({direction: 'from-right'});
      if (r < 0.8) return slide({direction: 'from-left'});
      if (r < 0.9) return wipe({direction: 'from-left'});
      return wipe({direction: 'from-top-left'});
  }
};

const MusicTrack: React.FC<{m: Manifest}> = ({m}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  if (!m.musicPath || m.musicVolume <= 0) return null;
  const fadeF = Math.round(1.5 * fps);
  const seconds = frame / fps;
  const automation = m.musicAutomation ?? [];
  let active = -1;
  for (let i = 0; i < automation.length; i++) {
    if (seconds >= automation[i].start) active = i;
  }
  let narrativeFactor = active >= 0 ? automation[active].factor : 1;
  if (active > 0) {
    const local = seconds - automation[active].start;
    narrativeFactor = interpolate(local, [0, m.musicTransitionSeconds ?? 0.45],
      [automation[active - 1].factor, automation[active].factor],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  }
  const vol =
    m.musicVolume *
    narrativeFactor *
    interpolate(
      frame,
      [0, fadeF, Math.max(durationInFrames - fadeF, fadeF + 1), durationInFrames],
      [0, 1, 1, 0],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
    );
  return <Audio loop src={staticFile(m.musicPath)} volume={vol} />;
};

// ── Impact-graphic windowing ────────────────────────────────────────────
// Overlay graphics (kinetic/stat/card/glass) are impact moments, not
// wallpaper: they hold for ~overlaySeconds, fade out, and hand the frame
// back to the footage for the rest of the scene's narration.

const FadeShell: React.FC<{frames: number; fps: number;
  children: React.ReactNode}> = ({frames, fps, children}) => {
  const frame = useCurrentFrame();
  const fadeF = Math.max(Math.round(0.4 * fps), 6);
  const opacity = interpolate(frame,
    [Math.max(frames - fadeF, 1), Math.max(frames - 1, 2)], [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{opacity}}>{children}</AbsoluteFill>;
};

const OverlayWindow: React.FC<{frames: number; fps: number;
  children: React.ReactNode}> = ({frames, fps, children}) => (
  <Sequence durationInFrames={Math.max(frames, 1)}>
    <FadeShell frames={frames} fps={fps}>{children}</FadeShell>
  </Sequence>
);

const DimFill: React.FC<{frames: number; fps: number}> = ({frames, fps}) => {
  const frame = useCurrentFrame();
  const fadeF = Math.max(Math.round(0.4 * fps), 6);
  const opacity = interpolate(frame,
    [0, 8, Math.max(frames - fadeF, 9), Math.max(frames - 1, 10)],
    [0, 0.55, 0.55, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{background: 'rgb(6,10,20)', opacity,
    pointerEvents: 'none'}} />;
};

const TimedDim: React.FC<{frames: number; fps: number}> = ({frames, fps}) => (
  <Sequence durationInFrames={Math.max(frames, 1)}>
    <DimFill frames={frames} fps={fps} />
  </Sequence>
);

export const Main: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const fps = m.fps;
  const style = getStyle(m.style);
  const maxShotSeconds = m.maxShotSeconds ?? 5;
  const overlaySeconds = Math.min(
    Math.max(Number((m as any).overlaySeconds ?? 5), 2.5), 12);
  const overlayRanges = m.scenes
    .filter((scene) => ['kinetic', 'stat', 'card', 'glass'].includes(scene.visualMode ?? ''))
    .map((scene) => ({start: scene.start ?? 0,
      end: (scene.start ?? 0) + Math.min(scene.audioDuration, overlaySeconds)}));
  const outroFrames = Math.max(Math.round((m.outroSeconds ?? 4) * fps), fps);

  const items: React.ReactNode[] = [];
  m.scenes.forEach((scene, i) => {
    const sceneFrames = Math.round(scene.audioDuration * fps);
    const mode = scene.visualMode ?? 'broll';
    const overlayScene = mode === 'kinetic' || mode === 'stat' || mode === 'card' || mode === 'glass';
    const overlayFrames = Math.min(sceneFrames,
      Math.round(overlaySeconds * fps));
    const isMap = mode === 'map' && scene.map && scene.map.world;
    const motion: MotionSpec = scene.motion ?? {};
    items.push(
      <TransitionSeries.Sequence key={`s-${scene.n}`} durationInFrames={sceneFrames}>
        {isMap ? (
          <MapZoom map={scene.map} sceneFrames={sceneFrames} style={style} />
        ) : (
          <SceneVisual
            assets={scene.assets}
            visualBeats={scene.visualBeats ?? []}
            sceneFrames={sceneFrames}
            fps={fps}
            maxShotSeconds={maxShotSeconds}
            sceneN={scene.n}
            style={style}
          />
        )}
        {overlayScene ? <TimedDim frames={overlayFrames} fps={fps} /> : null}
        {scene.audioPath ? <Audio src={staticFile(scene.audioPath)} /> : null}
        {mode === 'kinetic' && scene.kineticText ? (
          <OverlayWindow frames={overlayFrames} fps={fps}>
            <KineticTitle text={scene.kineticText} style={style}
              variant={motion.kineticVariant} />
          </OverlayWindow>
        ) : null}
        {mode === 'stat' && scene.stat && scene.stat.label ? (
          <OverlayWindow frames={overlayFrames} fps={fps}>
            <AnimatedStatCard stat={scene.stat} style={style}
              variant={motion.statVariant} />
          </OverlayWindow>
        ) : null}
        {mode === 'card' && scene.card && scene.card.headline ? (
          <OverlayWindow frames={overlayFrames} fps={fps}>
            <EditorialCard card={scene.card} style={style} variant={motion.cardVariant} />
          </OverlayWindow>
        ) : null}
        {mode === 'glass' && scene.glass && (scene.glass.headline || scene.glass.label || scene.glass.location || scene.glass.chapter || scene.glass.value != null) ? (
          <OverlayWindow frames={overlayFrames} fps={fps}>
            <GlassCard data={scene.glass} style={style} variant={motion.glassVariant} />
          </OverlayWindow>
        ) : null}
        {!overlayScene && !isMap && scene.title ? (
          <AnimatedLowerThird title={scene.title} style={style}
            variant={motion.lowerThirdVariant} index={scene.n} />
        ) : null}
        <SceneFrame variant={motion.frameVariant} style={style} sceneN={scene.n} />
        {i > 0 ? <LightLeak seed={`scene-${scene.n}`} /> : null}
      </TransitionSeries.Sequence>
    );
    items.push(
      <TransitionSeries.Transition
        key={`t-${scene.n}`}
        presentation={pickTransition(i, style)}
        timing={linearTiming({durationInFrames: m.xfadeFrames})}
      />
    );
  });
  // branded outro end card
  items.push(
    <TransitionSeries.Sequence key="outro" durationInFrames={outroFrames}>
      <Outro
        brandName={m.brandName || 'TERRA INCOGNITA'}
        tagline={m.brandTagline || "Mapping the world's hidden places"}
        style={style}
        watermarkPath={m.watermarkPath}
      />
    </TransitionSeries.Sequence>
  );

  return (
    <AbsoluteFill style={{backgroundColor: style.bg}}>
      <TransitionSeries>{items}</TransitionSeries>
      <CaptionsLayer captions={m.captions} style={style}
        compactRanges={overlayRanges} compactYFrac={0.84} sizeBoost={1.15} />
      <CinematicOverlay />
      {style.hud ? (
        <TelemetryHUD starts={m.scenes.map((sc) => sc.start ?? 0)}
          accent={style.accent} accent2={style.accent2} />
      ) : null}
      <CtaLayer event={m.cta} style={style} fps={fps} />
      {m.watermarkPath ? (
        <Watermark src={m.watermarkPath} opacity={m.watermarkOpacity ?? 0.08} />
      ) : null}
      {m.progressBar ? <ProgressBar accent={style.accent} /> : null}
      <SfxLayer events={m.sfx ?? []} fps={fps} />
      <MusicTrack m={m} />
    </AbsoluteFill>
  );
};
