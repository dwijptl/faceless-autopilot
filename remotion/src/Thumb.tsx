import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import type {Manifest} from './Root';
import {fontFamily} from './elements';

/** 1280x720 thumbnail: hero image + big stroked title, rendered as a still. */
export const Thumb: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const hero = m.scenes[0]?.assets?.find((a) => a.kind === 'image')
    ?? m.scenes[0]?.assets?.[0];
  const words = (m.thumbText || m.title || 'NEW VIDEO').toUpperCase();

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0f1a', fontFamily}}>
      {hero ? (
        hero.kind === 'image' ? (
          <Img
            src={staticFile(hero.path)}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        ) : (
          // eslint-disable-next-line @remotion/no-offthreadvideo-in-still
          <video
            src={staticFile(hero.path)}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        )
      ) : null}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(0,0,0,0.12) 30%, rgba(0,0,0,0.78) 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 48,
          right: 48,
          bottom: 44,
          color: m.accent,
          fontSize: 118,
          lineHeight: 1.02,
          fontWeight: 900,
          letterSpacing: -2,
          textShadow:
            '0 6px 0 rgba(0,0,0,0.9), 6px 0 0 rgba(0,0,0,0.9), -6px 0 0 rgba(0,0,0,0.9), 0 -4px 0 rgba(0,0,0,0.9), 0 14px 44px rgba(0,0,0,0.8)',
        }}
      >
        {words}
      </div>
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          height: 14,
          width: '100%',
          background: m.accent,
        }}
      />
    </AbsoluteFill>
  );
};
