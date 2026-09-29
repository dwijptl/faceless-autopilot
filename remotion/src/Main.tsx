import React from 'react';
import {
  AbsoluteFill,
  Audio,
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
import {
  CaptionsLayer,
  SceneVisual,
  SfxLayer,
  Watermark,
  bodyFamily,
} from './elements';

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
    narrativeFactor = interpolate(
      local,
      [0, m.musicTransitionSeconds ?? 0.45],
      [automation[active - 1].factor, automation[active].factor],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
    );
  }
  const volume =
    m.musicVolume *
    narrativeFactor *
    interpolate(
      frame,
      [0, fadeF, Math.max(durationInFrames - fadeF, fadeF + 1), durationInFrames],
      [0, 1, 1, 0],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
    );
  return <Audio loop src={staticFile(m.musicPath)} volume={volume} />;
};

/** A plain number over full-frame media. No card, frame, panel, or layout skin. */
export const NumberOverlay: React.FC<{
  stat?: {value?: number; suffix?: string; label?: string};
  sceneFrames: number;
  fps: number;
  vertical?: boolean;
}> = ({stat, sceneFrames, fps, vertical = false}) => {
  const frame = useCurrentFrame();
  const value = Number(stat?.value);
  if (!Number.isFinite(value) || !stat?.label) return null;
  const holdFrames = Math.max(1, Math.min(
    sceneFrames,
    Math.round((vertical ? 2.4 : 3.2) * fps)
  ));
  const fadeFrames = Math.max(Math.round(0.22 * fps), 3);
  const opacity = interpolate(
    frame,
    [0, fadeFrames, Math.max(holdFrames - fadeFrames, fadeFrames + 1), holdFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );
  const shown = Math.abs(value) >= 100 || Number.isInteger(value)
    ? Math.round(value).toLocaleString('en-IN')
    : value.toFixed(1);
  return (
    <Sequence durationInFrames={holdFrames}>
      <AbsoluteFill style={{
        justifyContent: 'center', alignItems: 'center', opacity,
        pointerEvents: 'none', padding: vertical ? '0 80px' : '0 160px',
        fontFamily: bodyFamily(getStyle('documentary')),
      }}>
        <div style={{
          fontSize: vertical ? 154 : 172, fontWeight: 900,
          color: 'white', lineHeight: 1, textAlign: 'center',
          fontVariantNumeric: 'tabular-nums',
          textShadow: '0 4px 8px rgba(0,0,0,0.96), 0 14px 44px rgba(0,0,0,0.82)',
        }}>
          {shown}{stat.suffix ?? ''}
        </div>
        <div style={{
          marginTop: vertical ? 24 : 20, fontSize: vertical ? 48 : 40,
          fontWeight: 700, color: 'white', lineHeight: 1.35, textAlign: 'center',
          textShadow: '0 3px 7px rgba(0,0,0,0.98), 0 10px 30px rgba(0,0,0,0.85)',
        }}>
          {stat.label}
        </div>
      </AbsoluteFill>
    </Sequence>
  );
};

export const Main: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const fps = m.fps;
  const style = getStyle('documentary');
  const maxShotSeconds = m.maxShotSeconds ?? 8;
  const items: React.ReactNode[] = [];

  m.scenes.forEach((scene, index) => {
    const sceneFrames = Math.max(Math.round(scene.audioDuration * fps), 1);
    const isMap = scene.visualMode === 'map' && scene.map?.world;
    const mapFrames = Math.max(1, Math.min(
      sceneFrames,
      Math.round((m.mapShotSeconds ?? 5.5) * fps)
    ));
    const numberStart = Math.min(
      Math.max(Math.round((scene.impactStart ?? 0) * fps), 0),
      Math.max(sceneFrames - 1, 0)
    );
    items.push(
      <TransitionSeries.Sequence key={`s-${scene.n}`} durationInFrames={sceneFrames}>
        <SceneVisual
          assets={scene.assets}
          visualBeats={scene.visualBeats ?? []}
          sceneFrames={sceneFrames}
          fps={fps}
          maxShotSeconds={maxShotSeconds}
          sceneN={scene.n}
          style={style}
        />
        {isMap ? (
          <Sequence durationInFrames={mapFrames}>
            <MapZoom map={scene.map} sceneFrames={mapFrames} style={style} />
          </Sequence>
        ) : null}
        {scene.audioPath ? <Audio src={staticFile(scene.audioPath)} /> : null}
        {scene.visualMode === 'stat' ? (
          <Sequence from={numberStart} durationInFrames={sceneFrames - numberStart}>
            <NumberOverlay stat={scene.stat}
              sceneFrames={sceneFrames - numberStart} fps={fps} />
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
      <CaptionsLayer captions={m.captions} style={style}
        yFrac={0.79} sizeBoost={0.98} />
      {m.watermarkPath ? (
        <Watermark src={m.watermarkPath} opacity={m.watermarkOpacity ?? 0.08}
          corner="br" />
      ) : null}
      <SfxLayer events={m.sfx ?? []} fps={fps} />
      <MusicTrack m={m} />
    </AbsoluteFill>
  );
};
