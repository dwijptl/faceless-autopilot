import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import type {Manifest} from './Root';
import {fontFamily} from './elements';
import {BRAND, getStyle} from './styles';

/** Branded 1280x720 thumbnail template — consistent across style packs. */
export const Thumb: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const style = getStyle(m.style);
  const hero =
    m.scenes[0]?.assets?.find((a) => a.kind === 'image') ?? m.scenes[0]?.assets?.[0];
  const words = (m.thumbText || m.title || 'NEW VIDEO').toUpperCase();

  return (
    <AbsoluteFill style={{backgroundColor: BRAND.navy, fontFamily}}>
      {hero ? (
        hero.kind === 'image' ? (
          <Img src={staticFile(hero.path)}
            style={{width: '100%', height: '100%', objectFit: 'cover',
              filter: style.visualFilter}} />
        ) : (
          // eslint-disable-next-line @remotion/no-offthreadvideo-in-still
          <video src={staticFile(hero.path)}
            style={{width: '100%', height: '100%', objectFit: 'cover',
              filter: style.visualFilter}} />
        )
      ) : null}
      <AbsoluteFill style={{
        background: 'linear-gradient(180deg, rgba(6,10,20,0.10) 25%, rgba(6,10,20,0.82) 100%)',
      }} />

      {/* brand chip */}
      <div style={{
        position: 'absolute', top: 34, left: 40, display: 'flex',
        alignItems: 'center', gap: 12,
        background: 'rgba(10,20,40,0.78)', border: `2px solid ${style.accent}`,
        borderRadius: 999, padding: '10px 22px',
      }}>
        {m.watermarkPath ? (
          <Img src={staticFile(m.watermarkPath)} style={{width: 30, height: 30}} />
        ) : null}
        <span style={{color: BRAND.text, fontSize: 24, fontWeight: 800,
          letterSpacing: 4}}>TERRA INCOGNITA</span>
      </div>

      {/* title */}
      <div style={{
        position: 'absolute', left: 48, right: 48, bottom: 48,
        color: style.accent, fontSize: 116, lineHeight: 1.02, fontWeight: 900,
        letterSpacing: -2,
        textShadow:
          '0 6px 0 rgba(0,0,0,0.9), 6px 0 0 rgba(0,0,0,0.9), -6px 0 0 rgba(0,0,0,0.9), 0 -4px 0 rgba(0,0,0,0.9), 0 14px 44px rgba(0,0,0,0.8)',
      }}>{words}</div>

      {/* brand top bar */}
      <div style={{position: 'absolute', top: 0, left: 0, height: 12,
        width: '100%', background: style.accent}} />
    </AbsoluteFill>
  );
};
