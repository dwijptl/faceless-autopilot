import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import type {Manifest} from './Root';
import {MapZoom} from './Map';
import {getStyle} from './styles';
import {CaptionsLayer, SceneVisual, SfxLayer, Watermark} from './elements';
import {NumberOverlay} from './Main';

const MusicTrack: React.FC<{m: Manifest}> = ({m}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  if (!m.musicPath || m.musicVolume <= 0) return null;
  if (m.musicLoopSafe) {
    return <Audio loop src={staticFile(m.musicPath)} volume={m.musicVolume} />;
  }
  const fadeF = Math.max(Math.round(0.15 * fps), 2);
  const volume = m.musicVolume * interpolate(
    frame,
    [0, fadeF, Math.max(durationInFrames - fadeF, fadeF + 1), durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );
  return <Audio loop src={staticFile(m.musicPath)} volume={volume} />;
};

const LoopBridge: React.FC<{
  asset?: {path: string; kind: string};
  fps: number;
}> = ({asset, fps}) => {
  const frame = useCurrentFrame();
  if (!asset) return null;
  const frames = Math.max(Math.round(0.45 * fps), 2);
  const opacity = interpolate(frame, [0, frames - 1], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{opacity}}>
      {asset.kind === 'video' ? (
        <OffthreadVideo muted src={staticFile(asset.path)}
          style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      ) : (
        <Img src={staticFile(asset.path)}
          style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      )}
    </AbsoluteFill>
  );
};

export const ShortMain: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const fps = m.fps;
  const {durationInFrames} = useVideoConfig();
  const style = getStyle('documentary');
  const maxShotSeconds = m.maxShotSeconds ?? 2.4;
  const bridgeFrames = Math.max(Math.round(0.45 * fps), 2);
  const items: React.ReactNode[] = [];

  m.scenes.forEach((scene, index) => {
    const sceneFrames = Math.max(Math.round(scene.audioDuration * fps), 1);
    const isMap = scene.visualMode === 'map' && scene.map?.world;
    const numberStart = Math.min(
      Math.max(Math.round((scene.impactStart ?? 0) * fps), 0),
      Math.max(sceneFrames - 1, 0)
    );
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
        {scene.audioPath ? <Audio src={staticFile(scene.audioPath)} /> : null}
        {scene.visualMode === 'stat' ? (
          <Sequence from={numberStart} durationInFrames={sceneFrames - numberStart}>
            <NumberOverlay stat={scene.stat}
              sceneFrames={sceneFrames - numberStart} fps={fps} vertical />
          </Sequence>
        ) : null}
      </TransitionSeries.Sequence>
    );
    if (index < m.scenes.length - 1) {
      items.push(
        <TransitionSeries.Transition
          key={`t-${scene.n}`}
          presentation={fade()}
          timing={linearTiming({durationInFrames: m.xfadeFrames})}
        />
      );
    }
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <TransitionSeries>{items}</TransitionSeries>
      <Sequence from={Math.max(0, durationInFrames - bridgeFrames)}
        durationInFrames={bridgeFrames}>
        <LoopBridge asset={m.scenes[0]?.assets?.[0]} fps={fps} />
      </Sequence>
      <CaptionsLayer captions={m.captions} style={style}
        yFrac={m.captionY ?? 0.62} sizeBoost={1.04} />
      {m.watermarkPath ? (
        <Watermark src={m.watermarkPath} opacity={m.watermarkOpacity ?? 0.1}
          corner="tl" />
      ) : null}
      <SfxLayer events={m.sfx ?? []} fps={fps} />
      <MusicTrack m={m} />
    </AbsoluteFill>
  );
};
