import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import type {Manifest} from './Root';
import {fontFamily} from './elements';
import {BRAND, getStyle} from './styles';

/** Branded 1280x720 thumbnail template — Hindi-market high-CTR layout:
 * dramatic Devanagari headline with fiery gradient fill (top-right),
 * big Latin punch text (bottom-left), optional curiosity annotation
 * (bottom-right). lineHeight/letterSpacing tuned so Devanagari matras
 * never clip. */

const FIRE = 'linear-gradient(180deg, #FFE27A 0%, #FFB020 45%, #FF7A1A 75%, #E8420A 100%)';

/** Gradient-filled display text with a thick dark stroke: a stroked copy
 * sits behind a background-clipped gradient copy. */
const FireText: React.FC<{text: string; size: number; align?: 'left' | 'right'}> =
  ({text, size, align}) => {
  const common: React.CSSProperties = {
    fontSize: size, fontWeight: 900, lineHeight: 1.28, letterSpacing: 0,
    textAlign: align ?? 'right', whiteSpace: 'pre-wrap',
  };
  return (
    <div style={{position: 'relative'}}>
      <div style={{
        ...common,
        color: '#12060A',
        WebkitTextStroke: '14px #12060A',
        textShadow: '0 10px 34px rgba(0,0,0,0.85)',
      }}>{text}</div>
      <div style={{
        ...common,
        position: 'absolute', inset: 0,
        backgroundImage: FIRE,
        WebkitBackgroundClip: 'text',
        backgroundClip: 'text',
        color: 'transparent',
      }}>{text}</div>
    </div>
  );
};

export const Thumb: React.FC<{manifest: Manifest}> = ({manifest: m}) => {
  const style = getStyle(m.style);
  const hero = m.thumbAiPath
    ? {path: m.thumbAiPath, kind: 'image'}
    : m.scenes[0]?.assets?.find((a) => a.kind === 'image') ?? m.scenes[0]?.assets?.[0];
  const words = (m.thumbText || m.title || 'NEW VIDEO').toUpperCase();
  const headline = String((m as any).thumbHeadline ?? '').trim();
  const question = String((m as any).thumbQuestion ?? '').trim();

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
      {/* Legibility gradient confined to the title band — a full-frame
          darkening turns dark AI images into black rectangles at feed size. */}
      <AbsoluteFill style={{
        background: 'linear-gradient(180deg, rgba(6,10,20,0.04) 0%, rgba(6,10,20,0.04) 55%, rgba(6,10,20,0.58) 100%)',
      }} />

      {/* brand chip */}
      <div style={{
        position: 'absolute', top: 30, left: 40, display: 'flex',
        alignItems: 'center', gap: 12,
        background: 'rgba(10,20,40,0.78)', border: `2px solid ${style.accent}`,
        borderRadius: 999, padding: '8px 20px',
      }}>
        {m.watermarkPath ? (
          <Img src={staticFile(m.watermarkPath)} style={{width: 26, height: 26}} />
        ) : null}
        <span style={{color: BRAND.text, fontSize: 21, fontWeight: 800,
          letterSpacing: 4}}>TERRA INCOGNITA</span>
      </div>

      {/* dramatic Devanagari headline, top-right */}
      {headline ? (
        <div style={{position: 'absolute', top: 44, right: 44, maxWidth: 640}}>
          <FireText text={headline} size={86} align="right" />
        </div>
      ) : null}

      {/* big Latin punch text, bottom-left */}
      <div style={{
        position: 'absolute', left: 48, right: question ? 400 : 48, bottom: 42,
        color: style.accent, fontSize: 100, lineHeight: 1.18, fontWeight: 900,
        letterSpacing: 0,
        textShadow:
          '0 6px 0 rgba(0,0,0,0.9), 6px 0 0 rgba(0,0,0,0.9), -6px 0 0 rgba(0,0,0,0.9), 0 -4px 0 rgba(0,0,0,0.9), 0 14px 44px rgba(0,0,0,0.8)',
      }}>{words}</div>

      {/* curiosity annotation, bottom-right */}
      {question ? (
        <div style={{position: 'absolute', right: 44, bottom: 52,
          display: 'flex', alignItems: 'center', gap: 10}}>
          <svg width="54" height="44" viewBox="0 0 54 44" style={{overflow: 'visible'}}>
            <path d="M4 40 C 18 34, 34 24, 46 8" fill="none" stroke="#FFFFFF"
              strokeWidth="5" strokeLinecap="round" />
            <path d="M34 8 L 47 6 L 45 19" fill="none" stroke="#FFFFFF"
              strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div style={{
            background: 'rgba(8,13,26,0.92)', border: '2px solid rgba(255,255,255,0.85)',
            borderRadius: 14, padding: '10px 18px', maxWidth: 300,
            color: '#FFFFFF', fontSize: 33, fontWeight: 800, lineHeight: 1.3,
            textAlign: 'center',
          }}>{question}</div>
        </div>
      ) : null}

      {/* brand top bar */}
      <div style={{position: 'absolute', top: 0, left: 0, height: 12,
        width: '100%', background: style.accent}} />
    </AbsoluteFill>
  );
};
