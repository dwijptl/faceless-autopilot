/** Explanatory visual modes — meaning-first components (retention round 2).
 *
 * These answer "what must the viewer UNDERSTAND right now?" instead of
 * "what clip matches this noun?":
 *  - ScaleComparator: one unfamiliar number against one familiar anchor
 *    (11,000 m = 13 × बुर्ज ख़लीफ़ा) — the anchor units fill in one by one.
 *  - CausalDiagram: A → B → C mechanism chain with stepwise reveal.
 *  - EvidenceFrame: brackets REAL footage with a named source, date and an
 *    honest confidence tag (पुष्टि / अनुमान / विवादित) — credibility as a
 *    visual asset, and an explicit anti-"generic AI channel" marker.
 */
import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {fontFamily} from './elements';
import {GLASS, GLOW, RADIUS, SHADOW, SPRING, text, useScale} from './motion-tokens';
import type {StylePack} from './styles';

export type CompareData = {
  value?: number;
  unit?: string;
  label?: string;
  anchorLabel?: string;
  anchorValue?: number;
  anchorUnit?: string;
};

export type CausalData = {
  headline?: string;
  steps?: string[];
};

export type EvidenceData = {
  kicker?: string;
  headline?: string;
  source?: string;
  date?: string;
  confidence?: string;
};

const glassPanel = (scale: number): React.CSSProperties => ({
  background: GLASS.tint,
  backdropFilter: `blur(${GLASS.blur}px)`,
  WebkitBackdropFilter: `blur(${GLASS.blur}px)`,
  border: `${Math.max(1, 1.4 * scale)}px solid ${GLASS.border}`,
  borderTop: `${Math.max(1, 1.6 * scale)}px solid ${GLASS.borderTop}`,
  borderRadius: GLASS.radiusLg * scale,
  boxShadow: GLASS.shadow,
});

/** 11,000 मीटर = 13 × बुर्ज ख़लीफ़ा — repeated-unit scale anchor. */
export const ScaleComparator: React.FC<{
  data: CompareData;
  style: StylePack;
}> = ({data, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = useScale();
  const value = Number(data.value ?? 0);
  const anchorValue = Math.max(Number(data.anchorValue ?? 1), 0.0001);
  const count = Math.max(1, Math.round(value / anchorValue));
  const shown = Math.min(count, 18); // visual cap; the ×N figure stays exact
  const enter = spring({frame, fps, config: SPRING.settle});
  const perUnit = Math.max(1.2, 26 / shown); // all units land inside ~1s
  const unitW = Math.min(64 * s, (980 * s) / shown - 6 * s);

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', fontFamily}}>
      <div
        style={{
          ...glassPanel(s),
          width: 1180 * s,
          padding: `${44 * s}px ${56 * s}px ${40 * s}px`,
          opacity: enter,
          transform: `translateY(${interpolate(enter, [0, 1], [46, 0])}px)`,
        }}
      >
        {data.label ? (
          <div style={{...text(30 * s, 700), color: style.accent, opacity: 0.92,
            textTransform: 'uppercase', marginBottom: 10 * s}}>
            {data.label}
          </div>
        ) : null}
        <div style={{display: 'flex', alignItems: 'baseline', gap: 16 * s}}>
          <div style={{...text(96 * s, 800), color: '#fff',
            textShadow: GLOW(style.accent, 0.7)}}>
            {value.toLocaleString('en-IN')}
          </div>
          <div style={{...text(40 * s, 700), color: 'rgba(255,255,255,.82)'}}>
            {data.unit ?? ''}
          </div>
        </div>
        <div style={{display: 'flex', alignItems: 'flex-end', gap: 6 * s,
          marginTop: 30 * s, height: 96 * s}}>
          {Array.from({length: shown}).map((_, i) => {
            const p = spring({frame: frame - 10 - i * perUnit, fps,
              config: SPRING.snap});
            return (
              <div
                key={i}
                style={{
                  width: unitW,
                  height: 92 * s * p,
                  borderRadius: 6 * s,
                  background: `linear-gradient(180deg, ${style.accent} 0%, ${style.accent2} 130%)`,
                  boxShadow: `0 6px 18px rgba(0,0,0,.35)`,
                  opacity: 0.5 + 0.5 * p,
                }}
              />
            );
          })}
        </div>
        <div style={{...text(34 * s, 700), color: 'rgba(255,255,255,.92)',
          marginTop: 22 * s}}>
          = {count.toLocaleString('en-IN')} × {data.anchorLabel ?? ''}
          {data.anchorValue ? (
            <span style={{color: 'rgba(255,255,255,.55)', fontWeight: 500}}>
              {'  '}({Number(data.anchorValue).toLocaleString('en-IN')}
              {data.anchorUnit ? ` ${data.anchorUnit}` : ''})
            </span>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** A → B → C mechanism chain; each step pops in and hands to the next. */
export const CausalDiagram: React.FC<{
  data: CausalData;
  style: StylePack;
}> = ({data, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = useScale();
  const steps = (data.steps ?? []).slice(0, 6);
  if (!steps.length) return null;
  const enter = spring({frame, fps, config: SPRING.settle});
  const stagger = Math.max(6, 42 / steps.length);
  const vertical = steps.length > 3;

  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', fontFamily}}>
      <div
        style={{
          ...glassPanel(s),
          maxWidth: 1360 * s,
          padding: `${40 * s}px ${52 * s}px`,
          opacity: enter,
          transform: `translateY(${interpolate(enter, [0, 1], [46, 0])}px)`,
        }}
      >
        {data.headline ? (
          <div style={{...text(34 * s, 800), color: style.accent,
            marginBottom: 26 * s}}>
            {data.headline}
          </div>
        ) : null}
        <div style={{display: 'flex', flexDirection: vertical ? 'column' : 'row',
          alignItems: vertical ? 'stretch' : 'center', gap: 14 * s}}>
          {steps.map((step, i) => {
            const p = spring({frame: frame - 8 - i * stagger, fps,
              config: SPRING.snap});
            const active = p > 0.35;
            return (
              <React.Fragment key={i}>
                {i > 0 ? (
                  <div style={{
                    ...text(34 * s, 800),
                    color: active ? style.accent : 'rgba(255,255,255,.25)',
                    alignSelf: 'center',
                    transform: vertical ? 'rotate(90deg)' : 'none',
                    flexShrink: 0,
                  }}>
                    →
                  </div>
                ) : null}
                <div
                  style={{
                    ...text(30 * s, 700),
                    color: active ? '#fff' : 'rgba(255,255,255,.4)',
                    background: active
                      ? `linear-gradient(135deg, ${style.accent}26, rgba(255,255,255,.06))`
                      : 'rgba(255,255,255,.04)',
                    border: `${Math.max(1, 1.2 * s)}px solid ${
                      active ? `${style.accent}88` : 'rgba(255,255,255,.14)'}`,
                    borderRadius: RADIUS.md * s,
                    padding: `${16 * s}px ${24 * s}px`,
                    boxShadow: active ? SHADOW.sm : 'none',
                    opacity: 0.35 + 0.65 * p,
                    transform: `scale(${0.92 + 0.08 * p})`,
                    flex: vertical ? undefined : 1,
                  }}
                >
                  {step}
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const CONFIDENCE_COLORS: Record<string, string> = {
  'पुष्टि': '#3ECF8E',
  'अनुमान': '#FFB020',
  'विवादित': '#FF6B57',
};

/** Brackets the scene's REAL footage with source + honest confidence tag. */
export const EvidenceFrame: React.FC<{
  data: EvidenceData;
  style: StylePack;
}> = ({data, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = useScale();
  const enter = spring({frame, fps, config: SPRING.settle});
  const inset = 54 * s;
  const arm = 96 * s * enter;
  const stroke = Math.max(2, 3.4 * s);
  const conf = (data.confidence ?? '').trim();
  const confColor = CONFIDENCE_COLORS[conf] ?? style.accent;

  const corner = (pos: React.CSSProperties, borders: React.CSSProperties) => (
    <div style={{position: 'absolute', width: arm, height: arm, ...pos, ...borders,
      opacity: enter}} />
  );

  return (
    <AbsoluteFill style={{fontFamily}}>
      {corner({top: inset, left: inset},
        {borderTop: `${stroke}px solid ${style.accent}`,
         borderLeft: `${stroke}px solid ${style.accent}`})}
      {corner({top: inset, right: inset},
        {borderTop: `${stroke}px solid ${style.accent}`,
         borderRight: `${stroke}px solid ${style.accent}`})}
      {corner({bottom: inset, left: inset},
        {borderBottom: `${stroke}px solid ${style.accent}`,
         borderLeft: `${stroke}px solid ${style.accent}`})}
      {corner({bottom: inset, right: inset},
        {borderBottom: `${stroke}px solid ${style.accent}`,
         borderRight: `${stroke}px solid ${style.accent}`})}

      <div style={{position: 'absolute', top: inset + 10 * s, left: inset + 20 * s,
        display: 'flex', gap: 12 * s, opacity: enter}}>
        <div style={{...text(24 * s, 800), color: style.bg,
          background: style.accent, borderRadius: RADIUS.pill,
          padding: `${6 * s}px ${18 * s}px`, textTransform: 'uppercase'}}>
          {data.kicker || 'स्रोत'}
        </div>
        {conf ? (
          <div style={{...text(24 * s, 800), color: '#0A1428',
            background: confColor, borderRadius: RADIUS.pill,
            padding: `${6 * s}px ${18 * s}px`,
            boxShadow: GLOW(confColor, 0.5)}}>
            {conf}
          </div>
        ) : null}
      </div>

      <div
        style={{
          position: 'absolute',
          left: inset,
          right: inset,
          bottom: inset + 8 * s,
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 20 * s,
          padding: `${14 * s}px ${22 * s}px`,
          background: 'linear-gradient(90deg, rgba(6,15,30,.86), rgba(6,15,30,.55) 70%, rgba(6,15,30,0))',
          borderLeft: `${Math.max(2, 4 * s)}px solid ${style.accent}`,
          opacity: enter,
          transform: `translateY(${interpolate(enter, [0, 1], [24, 0])}px)`,
        }}
      >
        <div style={{minWidth: 0}}>
          {data.headline ? (
            <div style={{...text(34 * s, 800), color: '#fff'}}>{data.headline}</div>
          ) : null}
          <div style={{...text(26 * s, 600), color: 'rgba(255,255,255,.78)'}}>
            {data.source ?? ''}
          </div>
        </div>
        {data.date ? (
          <div style={{...text(24 * s, 700), color: style.accent, flexShrink: 0}}>
            {data.date}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
