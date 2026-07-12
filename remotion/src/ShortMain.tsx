import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  OffthreadVideo,
  random,
  Sequence,
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
import type {MotionSpec} from './motion-library';
import {GlassCard} from './glass';

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
  if (m.musicLoopSafe) {
    return <Audio loop src={staticFile(m.musicPath)} volume={m.musicVolume} />;
  }
  const fadeF = Math.max(Math.round(0.15 * fps), 2); // nearly seamless replay boundary
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

const LoopBridge: React.FC<{asset?: {path: string; kind: string}; fps: number}> = ({asset, fps}) => {
  const frame = useCurrentFrame();
  if (!asset) return null;
  const frames = Math.max(Math.round(0.45 * fps), 2);
  const opacity = interpolate(frame, [0, frames - 1], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{opacity}}>
    {asset.kind === 'video' ? (
      <OffthreadVideo muted src={staticFile(asset.path)}
        style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    ) : (
      <Img src={staticFile(asset.path)}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: 'scale(1.05)'}} />
    )}
  </AbsoluteFill>;
};

export const ShortMain: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const fps = m.fps;
  const {durationInFrames} = useVideoConfig();
  const style = getStyle(m.style);
  const maxShotSeconds = m.maxShotSeconds ?? 2.4;
  const overlayRanges = m.scenes
    .filter((scene) => ['kinetic', 'stat', 'card', 'glass'].includes(scene.visualMode ?? ''))
    .map((scene) => ({start: scene.start ?? 0,
      end: (scene.start ?? 0) + scene.audioDuration}));
  const bridgeFrames = Math.max(Math.round(0.45 * fps), 2);

  const items: React.ReactNode[] = [];
  m.scenes.forEach((scene, i) => {
    const sceneFrames = Math.round(scene.audioDuration * fps);
    const mode = scene.visualMode ?? 'broll';
    const overlayScene = mode === 'kinetic' || mode === 'stat' || mode === 'card' || mode === 'glass';
    const isMap = mode === 'map' && scene.map && scene.map.world;
    const motion: MotionSpec = scene.motion ?? {};
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
        {mode === 'glass' && scene.glass && (scene.glass.headline || scene.glass.label || scene.glass.location || scene.glass.chapter || scene.glass.value != null) ? (
          <GlassCard data={scene.glass} style={style} variant={motion.glassVariant} />
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
      <Sequence from={Math.max(0, durationInFrames - bridgeFrames)}
        durationInFrames={bridgeFrames}>
        <LoopBridge asset={m.scenes[0]?.assets?.[0]} fps={fps} />
      </Sequence>
      <CaptionsLayer
        captions={m.captions}
        style={style}
        yFrac={(m as {captionY?: number}).captionY ?? 0.62}
        compactYFrac={0.75}
        compactRanges={overlayRanges}
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
