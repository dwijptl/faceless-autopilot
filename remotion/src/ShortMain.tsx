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
  ProgressBar,
  SceneVisual,
  SfxLayer,
  TextureOverlay,
  Watermark,
  headingFamily,
} from './elements';
import {variationFor} from './variation';
import {AnimatedStatCard, CtaLayer, EditorialCard, KineticTitle, SceneFrame} from './motion-library';
import type {MotionSpec} from './motion-library';
import {GlassCard} from './glass';
import {OverlayWindow, TimedDim} from './Main';
import {blurWhip, zoomPunch} from './transitions';

// Shorts: fast vertical whips, slides and punches — but calm packs
// (fades bias) breathe more, aggressive packs (whips/punches) hit harder.
const pickTransition = (i: number, style: StylePack): any => {
  const r = random(`str-${style.name}-${i}`);
  if (style.transitionBias === 'fades') {
    if (r < 0.5) return fade();
    if (r < 0.75) return zoomPunch();
    return slide({direction: 'from-bottom'});
  }
  if (style.transitionBias === 'whips') {
    if (r < 0.4) return blurWhip('from-bottom');
    if (r < 0.65) return blurWhip('from-right');
    if (r < 0.85) return zoomPunch();
    return slide({direction: 'from-bottom'});
  }
  if (style.transitionBias === 'punches') {
    if (r < 0.45) return zoomPunch();
    if (r < 0.7) return blurWhip('from-bottom');
    return fade();
  }
  if (r < 0.28) return blurWhip('from-bottom');
  if (r < 0.45) return slide({direction: 'from-bottom'});
  if (r < 0.6) return blurWhip('from-right');
  if (r < 0.78) return zoomPunch();
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

// Keep the replay bridge, but make channel recall explicit: every Short ends
// with the brand name visible for the final beat instead of adding a dead
// outro card that would break the loop.
const ShortEndBrand: React.FC<{
  brandName: string;
  watermarkPath: string | null;
  style: StylePack;
}> = ({brandName, watermarkPath, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const opacity = interpolate(frame, [0, Math.max(Math.round(0.18 * fps), 1)],
    [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center',
      paddingBottom: 300, opacity, pointerEvents: 'none'}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 18,
        padding: '14px 26px', borderRadius: 999,
        background: 'rgba(10,20,40,0.92)',
        border: `2px solid ${style.accent}`,
        boxShadow: '0 14px 40px rgba(0,0,0,0.48)',
        fontFamily: headingFamily(style)}}>
        {watermarkPath ? (
          <Img src={staticFile(watermarkPath)} style={{width: 58, height: 58}} />
        ) : null}
        <span style={{fontSize: 42, fontWeight: 900, letterSpacing: 4,
          color: '#F4F7FB'}}>{brandName}</span>
      </div>
    </AbsoluteFill>
  );
};

export const ShortMain: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const fps = m.fps;
  const {durationInFrames} = useVideoConfig();
  const style = getStyle(m.style);
  const vr = variationFor(m.motionSeed || m.title || 'short');
  const maxShotSeconds = m.maxShotSeconds ?? 2.4;
  const overlaySeconds = Math.min(
    Math.max(Number((m as any).overlaySeconds ?? 3.5), 1.5), 8);
  const overlayRanges = m.scenes
    .filter((scene) => ['kinetic', 'stat', 'card', 'glass'].includes(scene.visualMode ?? ''))
    .map((scene) => {
      const impact = Number((scene as any).impactStart ?? 0);
      return {start: (scene.start ?? 0) + impact,
        end: (scene.start ?? 0) + Math.min(scene.audioDuration, impact + overlaySeconds)};
    });
  const bridgeFrames = Math.max(Math.round(0.9 * fps), 2);

  const items: React.ReactNode[] = [];
  m.scenes.forEach((scene, i) => {
    const sceneFrames = Math.round(scene.audioDuration * fps);
    const mode = scene.visualMode ?? 'broll';
    const overlayScene = mode === 'kinetic' || mode === 'stat' || mode === 'card' || mode === 'glass';
    // word-synced impact: the graphic enters on the spoken keyword and hands
    // the frame back to footage after ~overlaySeconds
    const impactF = Math.max(0, Math.min(
      Math.round(Number((scene as any).impactStart ?? 0) * fps),
      Math.max(sceneFrames - fps, 0)));
    const overlayFrames = Math.max(1, Math.min(sceneFrames - impactF,
      Math.round(overlaySeconds * fps)));
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
            gradeOpacity={vr.gradeOpacity}
          />
        )}
        {overlayScene ? (
          <TimedDim frames={overlayFrames} fps={fps} from={impactF} />
        ) : null}
        {scene.audioPath ? <Audio src={staticFile(scene.audioPath)} /> : null}
        {mode === 'kinetic' && scene.kineticText ? (
          <OverlayWindow frames={overlayFrames} fps={fps} from={impactF}>
            <KineticTitle text={scene.kineticText} style={style}
              variant={motion.kineticVariant} />
          </OverlayWindow>
        ) : null}
        {mode === 'stat' && scene.stat && scene.stat.label ? (
          <OverlayWindow frames={overlayFrames} fps={fps} from={impactF}>
            <AnimatedStatCard stat={scene.stat} style={style}
              variant={motion.statVariant} />
          </OverlayWindow>
        ) : null}
        {mode === 'card' && scene.card && scene.card.headline ? (
          <OverlayWindow frames={overlayFrames} fps={fps} from={impactF}>
            <EditorialCard card={scene.card} style={style} variant={motion.cardVariant} />
          </OverlayWindow>
        ) : null}
        {mode === 'glass' && scene.glass && (scene.glass.headline || scene.glass.label || scene.glass.location || scene.glass.chapter || scene.glass.value != null) ? (
          <OverlayWindow frames={overlayFrames} fps={fps} from={impactF}>
            <GlassCard data={scene.glass} style={style} variant={motion.glassVariant} />
          </OverlayWindow>
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
        <ShortEndBrand brandName={m.brandName || 'SURAAGNAMA'}
          watermarkPath={m.watermarkPath} style={style} />
      </Sequence>
      <CaptionsLayer
        captions={m.captions}
        style={style}
        yFrac={(m as {captionY?: number}).captionY ?? 0.62}
        compactYFrac={0.75}
        compactRanges={overlayRanges}
        variation={vr}
      />
      <TextureOverlay style={style} opacityMul={vr.texOpacity} />
      <CtaLayer event={m.cta} style={style} fps={fps} />
      {m.watermarkPath ? (
        <Watermark src={m.watermarkPath}
          corner={style.layout?.watermark ?? 'tl'}
          opacity={Math.max(m.watermarkOpacity ?? 0.08, 0.1)} />
      ) : null}
      {m.progressBar && style.layout?.progress !== 'none' ? (
        <ProgressBar accent={style.accent}
          position={style.layout?.progress?.startsWith('bottom') ? 'bottom' : 'top'}
          thickness={style.layout?.progress === 'bottom-thick' ? 12 : 8} />
      ) : null}
      <SfxLayer events={m.sfx ?? []} fps={fps} />
      <MusicTrack m={m} />
    </AbsoluteFill>
  );
};
