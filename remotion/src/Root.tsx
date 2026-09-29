import React from 'react';
import {Composition} from 'remotion';
import {Main} from './Main';
import {ShortMain} from './ShortMain';
import {Thumb} from './Thumb';

const FALLBACK = {
  fps: 30,
  width: 1920,
  height: 1080,
  xfadeFrames: 8,
  maxShotSeconds: 8,
  mapShotSeconds: 5.5,
  style: 'documentary',
  captionY: 0.78,
  title: 'Suraagnama',
  thumbText: 'PREVIEW',
  thumbHeadline: '',
  thumbQuestion: '',
  thumbAiPath: null as string | null,
  watermarkPath: null as string | null,
  watermarkOpacity: 0.08,
  musicPath: null as string | null,
  musicVolume: 0.12,
  musicLoopSafe: false,
  musicAutomation: [] as {
    start: number; duration: number; factor: number; delivery?: string;
  }[],
  musicTransitionSeconds: 0.45,
  sfx: [] as {path: string; start: number; volume: number}[],
  captions: [] as {start: number; end: number; text: string}[],
  scenes: [
    {
      n: 1,
      start: 0,
      impactStart: 0,
      visualMode: 'broll',
      stat: {} as {value?: number; suffix?: string; label?: string},
      map: {} as {
        world?: string;
        region?: string;
        markerWorld?: number[];
        markerRegion?: number[];
        label?: string;
      },
      audioPath: null as string | null,
      audioDuration: 5,
      assets: [] as {
        path: string; kind: string; duration?: number; ai?: boolean;
        family?: string; sourcePolicy?: string;
      }[],
      visualBeats: [] as {
        start: number; duration: number; cue?: string; purpose?: string;
        fromFrame?: number; durationFrames?: number;
        searchTerms?: string[];
        assets: {
          path: string; kind: string; duration?: number; ai?: boolean;
          family?: string; sourcePolicy?: string;
        }[];
      }[],
    },
  ],
};

export type Manifest = typeof FALLBACK;

const compositionDuration = (m: Manifest) => {
  const sceneTotal = m.scenes.reduce(
    (total, scene) => total + Math.round(scene.audioDuration * m.fps),
    0
  );
  const overlaps = Math.max(m.scenes.length - 1, 0) * m.xfadeFrames;
  return Math.max(m.fps, sceneTotal - overlaps);
};

export const Root: React.FC = () => (
  <>
    <Composition
      id="Main"
      component={Main}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{manifest: FALLBACK}}
      calculateMetadata={async ({props}) => {
        const m = (props.manifest ?? FALLBACK) as Manifest;
        return {
          durationInFrames: compositionDuration(m),
          fps: m.fps,
          width: m.width,
          height: m.height,
          props,
        };
      }}
    />
    <Composition
      id="Short"
      component={ShortMain}
      durationInFrames={300}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{manifest: FALLBACK}}
      calculateMetadata={async ({props}) => {
        const m = (props.manifest ?? FALLBACK) as Manifest;
        return {
          durationInFrames: compositionDuration(m),
          fps: m.fps,
          width: 1080,
          height: 1920,
          props,
        };
      }}
    />
    <Composition
      id="Thumb"
      component={Thumb}
      durationInFrames={1}
      fps={30}
      width={1280}
      height={720}
      defaultProps={{manifest: FALLBACK}}
    />
  </>
);
