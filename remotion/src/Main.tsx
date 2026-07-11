import React from 'react';
import {
  AbsoluteFill,
  Audio,
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
  const vol =
    m.musicVolume *
    interpolate(
      frame,
      [0, fadeF, Math.max(durationInFrames - fadeF, fadeF + 1), durationInFrames],
      [0, 1, 1, 0],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
    );
  return <Audio loop src={staticFile(m.musicPath)} volume={vol} />;
};

export const Main: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const fps = m.fps;
  const style = getStyle(m.style);
  const maxShotSeconds = 8;
  const outroFrames = Math.max(Math.round((m.outroSeconds ?? 4) * fps), fps);

  const items: React.ReactNode[] = [];
  m.scenes.forEach((scene, i) => {
    const sceneFrames = Math.round(scene.audioDuration * fps);
    const mode = scene.visualMode ?? 'broll';
    const overlayScene = mode === 'kinetic' || mode === 'stat' || mode === 'card';
    const isMap = mode === 'map' && scene.map && scene.map.world;
    const motion = scene.motion ?? {};
    items.push(
      <TransitionSeries.Sequence key={`s-${scene.n}`} durationInFrames={sceneFrames}>
        {isMap ? (
          <MapZoom map={scene.map} sceneFrames={sceneFrames} style={style} />
        ) : (
          <SceneVisual
            assets={scene.assets}
            sceneFrames={sceneFrames}
            fps={fps}
            maxShotSeconds={maxShotSeconds}
            sceneN={scene.n}
            style={style}
            dim={overlayScene}
          />
        )}
        {scene.audioPath ? <Audio src={staticFile(scene.audioPath)} /> : null}
        {mode === 'kinetic' && scene.kineticText ? (
          <KineticTitle text={scene.kineticText} style={style}
            variant={motion.kineticVariant} />
        ) : null}
        {mode === 'stat' && scene.stat && scene.stat.label ? (
          <AnimatedStatCard stat={scene.stat} style={style}
            variant={motion.statVariant} />
        ) : null}
        {mode === 'card' && scene.card && scene.card.headline ? (
          <EditorialCard card={scene.card} style={style} variant={motion.cardVariant} />
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
      <CaptionsLayer captions={m.captions} style={style} />
      <CinematicOverlay />
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
