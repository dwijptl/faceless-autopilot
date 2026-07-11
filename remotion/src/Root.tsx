import React from 'react';
import {Composition} from 'remotion';
import {Main} from './Main';
import {ShortMain} from './ShortMain';
import {Thumb} from './Thumb';

// A tiny placeholder manifest so the Studio can open without props.
const FALLBACK = {
  fps: 30,
  width: 1920,
  height: 1080,
  xfadeFrames: 12,
  style: 'documentary',
  accent: '#FFB020',
  progressBar: true,
  brandName: 'TERRA INCOGNITA',
  brandTagline: "Mapping the world's hidden places",
  watermarkPath: null as string | null,
  watermarkOpacity: 0.08,
  outroSeconds: 4,
  captionY: 0.78,
  title: 'Terra Incognita',
  thumbText: 'PREVIEW',
  thumbAiPath: null as string | null,
  sfx: [] as {path: string; start: number; volume: number}[],
  musicPath: null as string | null,
  musicVolume: 0.12,
  captions: [] as {start: number; end: number; text: string}[],
  scenes: [
    {
      n: 1,
      title: 'Preview scene',
      visualMode: 'broll',
      kineticText: '',
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
      assets: [] as {path: string; kind: string; duration?: number}[],
    },
  ],
};

export type Manifest = typeof FALLBACK;

const mainDuration = (m: Manifest) => {
  const sceneTotal = m.scenes.reduce(
    (acc, s) => acc + Math.round(s.audioDuration * m.fps),
    0
  );
  const outro = Math.max(Math.round((m.outroSeconds ?? 4) * m.fps), m.fps);
  // one transition between each pair of scenes + one into the outro
  const overlaps = m.scenes.length * m.xfadeFrames;
  return Math.max(m.fps, sceneTotal + outro - overlaps);
};

const shortDuration = (m: Manifest) => {
  const sceneTotal = m.scenes.reduce(
    (acc, s) => acc + Math.round(s.audioDuration * m.fps),
    0
  );
  const overlaps = (m.scenes.length - 1) * m.xfadeFrames; // no outro
  return Math.max(m.fps, sceneTotal - overlaps);
};

export const Root: React.FC = () => {
  return (
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
            durationInFrames: mainDuration(m),
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
            durationInFrames: shortDuration(m),
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
};
