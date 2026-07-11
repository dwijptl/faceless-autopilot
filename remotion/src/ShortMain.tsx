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
import type {Manifest} from './Root';
import {MapZoom} from './Map';
import {getStyle, StylePack} from './styles';
import {
  CaptionsLayer,
  CinematicOverlay,
  ProgressBar,
  SceneVisual,
  SfxLayer,
  Watermark,
} from './elements';
import {AnimatedStatCard, CtaLayer, EditorialCard, KineticTitle, SceneFrame} from './motion-library';

// Shorts: fast, mostly vertical slides + fades.
const pickTransition = (i: number, style: StylePack): any => {
  const r = random(`str-${style.name}-${i}`);
  if (r < 0.4) return slide({direction: 'from-bottom'});
  if (r < 0.6) return slide({direction: 'from-right'});
  return fade();
};

const MusicTrack: React.FC<{m: Manifest}> = ({m}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  if (!m.musicPath || m.musicVolume <= 0) return null;
  const fadeF = Math.round(0.6 * fps); // quick fades keep the loop tight
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

export const ShortMain: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const fps = m.fps;
  const style = getStyle(m.style);
  const maxShotSeconds = 3.5;

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
        <SceneFrame variant={motion.frameVariant} style={style} sceneN={scene.n} />
      </TransitionSeries.Sequence>
    );
    if (i < m.scenes.length - 1) {
      items.push(
        <TransitionSeries.Transition
          key={`t-${scene.n}`}
          presentation={pickTransition(i, style)}
          timing={linearTiming({durationInFrames: m.xfadeFrames})}
        />
      );
    }
  });

  return (
    <AbsoluteFill style={{backgroundColor: style.bg}}>
      <TransitionSeries>{items}</TransitionSeries>
      <CaptionsLayer
        captions={m.captions}
        style={style}
        yFrac={(m as {captionY?: number}).captionY ?? 0.62}
      />
      <CinematicOverlay />
      <CtaLayer event={m.cta} style={style} fps={fps} />
      {m.watermarkPath ? (
        <Watermark src={m.watermarkPath} corner="tl"
          opacity={Math.max(m.watermarkOpacity ?? 0.08, 0.1)} />
      ) : null}
      {m.progressBar ? <ProgressBar accent={style.accent} /> : null}
      <SfxLayer events={m.sfx ?? []} fps={fps} />
      <MusicTrack m={m} />
    </AbsoluteFill>
  );
};
