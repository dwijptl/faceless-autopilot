import React, {useId} from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {bodyFamily} from './elements';
import {StylePack} from './styles';
import {GLASS, GLOW, RADIUS, SPRING, panel, text, useEnter, useScale} from './motion-tokens';

export type GlassVariant = 'fact' | 'metric' | 'location' | 'chapter' | 'reveal';

export type GlassData = {
  kicker?: string;
  headline?: string;
  body?: string;
  value?: number;
  suffix?: string;
  label?: string;
  delta?: number;
  deltaDirection?: 'up' | 'down' | 'flat';
  location?: string;
  coordinates?: string;
  chapter?: string;
};

const RefractionFilter: React.FC<{id: string; strong?: boolean}> = ({id, strong}) => (
  <svg width="0" height="0" style={{position: 'absolute'}} aria-hidden>
    <filter id={id} x="-20%" y="-20%" width="140%" height="140%"
      colorInterpolationFilters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency={strong ? '0.009 0.014' : '0.006 0.010'}
        numOctaves="2" seed="17" result="noise" />
      <feGaussianBlur in="noise" stdDeviation={strong ? 2.4 : 3.5} result="softNoise" />
      <feDisplacementMap in="SourceGraphic" in2="softNoise"
        scale={strong ? 38 : 18} xChannelSelector="R" yChannelSelector="G" />
    </filter>
  </svg>
);

const GlassSurface: React.FC<{
  children: React.ReactNode;
  accent: string;
  strong?: boolean;
  style?: React.CSSProperties;
}> = ({children, accent, strong = false, style}) => {
  const frame = useCurrentFrame();
  const s = useScale();
  const rawId = useId();
  const filterId = `glass-${rawId.replace(/:/g, '')}`;
  const sheen = interpolate(frame, [5, 45], [-75, 150], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return <div style={{position: 'relative', ...panel(s),
    background: `linear-gradient(145deg, ${GLASS.frost}, ${GLASS.tint} 44%, rgba(3,10,22,.66))`,
    backdropFilter: `url(#${filterId}) blur(${GLASS.blur * s}px) saturate(1.32)`,
    WebkitBackdropFilter: `url(#${filterId}) blur(${GLASS.blur * s}px) saturate(1.32)`,
    ...style}}>
    <RefractionFilter id={filterId} strong={strong}/>
    <div style={{position: 'absolute', inset: -10 * s,
      filter: `url(#${filterId})`, opacity: strong ? .46 : .25,
      background: `radial-gradient(circle at 22% 8%, ${accent}55, transparent 36%), linear-gradient(115deg, rgba(255,255,255,.24), transparent 38%)`,
      pointerEvents: 'none'}}/>
    <div style={{position: 'absolute', inset: 0, borderRadius: 'inherit',
      borderTop: `${Math.max(1, 2 * s)}px solid ${GLASS.borderTop}`,
      borderLeft: `${Math.max(1, 1 * s)}px solid rgba(255,255,255,.32)`,
      boxShadow: `inset 0 ${Math.max(1, 1*s)}px 0 rgba(255,255,255,.18), ${GLOW(accent, strong ? .8 : .35)}`,
      pointerEvents: 'none'}}/>
    <div style={{position: 'absolute', top: '-45%', bottom: '-45%', width: '32%',
      left: `${sheen}%`, transform: 'skewX(-18deg)', opacity: .32,
      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,.48), transparent)',
      filter: `blur(${10*s}px)`, pointerEvents: 'none'}}/>
    <div style={{position: 'relative', zIndex: 2}}>{children}</div>
  </div>;
};

const formatValue = (value: number, shown: number) =>
  Math.abs(value) >= 100 || Number.isInteger(value)
    ? Math.round(shown).toLocaleString('en-IN')
    : shown.toFixed(1);

const MiniSparkline: React.FC<{accent: string; progress: number; scale: number}> = ({accent, progress, scale}) => {
  const points = [[0,42],[34,31],[69,37],[105,16],[141,23],[178,7]];
  const path = points.map(([x,y], i) => `${i ? 'L' : 'M'} ${x*scale} ${y*scale}`).join(' ');
  return <svg width={180*scale} height={52*scale} viewBox={`0 0 ${180*scale} ${52*scale}`}>
    <path d={path} fill="none" stroke={accent} strokeWidth={3*scale}
      strokeLinecap="round" strokeLinejoin="round" pathLength={1}
      strokeDasharray={1} strokeDashoffset={1-progress}/>
    <circle cx={178*scale} cy={7*scale} r={5*scale} fill={accent} opacity={progress}/>
  </svg>;
};

export const SonarPing: React.FC<{accent: string; size?: number}> = ({accent, size = 220}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return <div style={{position: 'relative', width: size, height: size}}>
    {[0, .36, .72].map((offset, i) => {
      const phase = ((frame / fps + offset) % 1.25) / 1.25;
      return <div key={i} style={{position: 'absolute', left: '50%', top: '50%',
        width: size * phase, height: size * phase, borderRadius: '50%',
        border: `2px solid ${accent}`, opacity: 1-phase,
        transform: 'translate(-50%,-50%)'}}/>;
    })}
    <div style={{position: 'absolute', left: '50%', top: '50%', width: 12, height: 12,
      transform: 'translate(-50%,-50%)', borderRadius: '50%', background: accent,
      boxShadow: GLOW(accent)}}/>
  </div>;
};

export const GlassCard: React.FC<{
  data: GlassData;
  style: StylePack;
  variant?: string;
}> = ({data, style, variant = 'fact'}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = useScale();
  const compact = width < height;
  const enter = useEnter(3, variant === 'reveal' ? 'snap' : 'settle');
  const count = spring({frame: frame - 7, fps, config: SPRING.drift});
  const hasValue = data.value != null && Number.isFinite(Number(data.value));
  const value = Number(data.value ?? 0);
  const shown = interpolate(count, [0,1], [0,value]);
  const display = formatValue(value, shown);
  const padX = (compact ? 46 : 70) * s;
  const padY = (compact ? 44 : 56) * s;
  const maxWidth = (compact ? 1040 : 1120) * s;
  const kicker = data.kicker || (variant === 'chapter' ? data.chapter : '') || '';
  const headline = data.headline || data.label || '';

  let content: React.ReactNode;
  if (variant === 'metric') {
    const direction = data.deltaDirection ?? ((data.delta ?? 0) < 0 ? 'down' : 'up');
    const deltaColor = direction === 'down' ? '#FF6B78' : direction === 'up' ? '#62E7A5' : 'rgba(255,255,255,.7)';
    content = <div style={{display:'grid',gridTemplateColumns:compact?'1fr':'1fr auto',
      alignItems:'end',gap:30*s,minWidth:compact?0:760*s}}>
      <div>
        {kicker ? <div style={{...text(26,800,s),color:'rgba(255,255,255,.65)',marginBottom:18*s}}>{kicker}</div> : null}
        <div style={{...text(compact?132:158,950,s),color:style.accent,lineHeight:.96,
          textShadow:GLOW(style.accent,.75)}}>{display}<span style={{fontSize:'.40em'}}>{data.suffix ?? ''}</span></div>
        <div style={{...text(compact?34:38,680,s),color:'rgba(255,255,255,.88)',marginTop:18*s}}>{headline}</div>
      </div>
      <div style={{display:'flex',flexDirection:'column',alignItems:compact?'flex-start':'flex-end',gap:18*s}}>
        {data.delta != null ? <div style={{...text(27,900,s),color:deltaColor,
          padding:`${9*s}px ${15*s}px`,borderRadius:RADIUS.pill,
          background:`${deltaColor}18`,border:`1px solid ${deltaColor}55`}}>
          {direction==='down'?'▼':direction==='up'?'▲':'•'} {Math.abs(data.delta)}
        </div> : null}
        <MiniSparkline accent={style.accent} progress={count} scale={s}/>
      </div>
    </div>;
  } else if (variant === 'location') {
    content = <div style={{display:'flex',alignItems:'center',gap:38*s,minWidth:compact?0:760*s}}>
      <SonarPing accent={style.accent} size={(compact?170:210)*s}/>
      <div>
        <div style={{...text(25,850,s),color:style.accent,marginBottom:12*s}}>LOCATION · स्थान</div>
        <div style={{...text(compact?54:68,920,s),color:'white'}}>{data.location || headline}</div>
        <div style={{...text(27,650,s),color:'rgba(255,255,255,.62)',marginTop:12*s}}>{data.coordinates || data.body}</div>
      </div>
    </div>;
  } else if (variant === 'chapter') {
    content = <div style={{minWidth:compact?0:900*s}}>
      <div style={{...text(25,900,s),color:style.accent,marginBottom:18*s}}>{kicker || 'अध्याय'}</div>
      <div style={{...text(compact?58:78,930,s),color:'white',maxWidth:940*s}}>{headline}</div>
      {data.body ? <div style={{...text(28,580,s),color:'rgba(255,255,255,.68)',marginTop:20*s,maxWidth:800*s}}>{data.body}</div> : null}
      <div style={{height:3*s,width:`${count*72}%`,marginTop:30*s,
        background:`linear-gradient(90deg,${style.accent},transparent)`,borderRadius:3}}/>
    </div>;
  } else if (variant === 'reveal') {
    content = <div style={{textAlign:'center',minWidth:compact?0:860*s}}>
      {kicker ? <div style={{...text(27,900,s),color:'rgba(255,255,255,.70)',marginBottom:22*s}}>{kicker}</div> : null}
      {hasValue ? <div style={{...text(compact?150:205,970,s),color:style.accent,lineHeight:.92,
        textShadow:GLOW(style.accent,1.15)}}>{display}<span style={{fontSize:'.38em'}}>{data.suffix ?? ''}</span></div> : null}
      <div style={{...text(hasValue?(compact?38:46):(compact?68:92),hasValue?720:940,s),
        color:hasValue?'white':style.accent,marginTop:hasValue?24*s:0,maxWidth:900*s,
        textShadow:hasValue?'none':GLOW(style.accent,.8)}}>{headline}</div>
      {data.body ? <div style={{...text(26,560,s),color:'rgba(255,255,255,.66)',margin:'18px auto 0',maxWidth:720*s}}>{data.body}</div> : null}
    </div>;
  } else {
    content = <div style={{minWidth:compact?0:720*s,maxWidth:940*s}}>
      {kicker ? <div style={{...text(25,900,s),color:style.accent,marginBottom:16*s}}>{kicker}</div> : null}
      {hasValue ? <div style={{...text(compact?112:142,960,s),color:'white',lineHeight:.95}}>
        {display}<span style={{fontSize:'.42em',color:style.accent}}>{data.suffix ?? ''}</span>
      </div> : null}
      <div style={{...text(compact?44:56,880,s),color:'white',marginTop:hasValue?20*s:0}}>{headline}</div>
      {data.body ? <div style={{...text(compact?27:30,560,s),color:'rgba(255,255,255,.70)',marginTop:18*s,maxWidth:800*s}}>{data.body}</div> : null}
    </div>;
  }

  return <AbsoluteFill style={{justifyContent:'center',alignItems:'center',padding:(compact?70:90)*s,
    fontFamily:bodyFamily(style),pointerEvents:'none'}}>
    <div style={{opacity:enter.opacity,transform:enter.transform,maxWidth,
      filter:`drop-shadow(0 ${18*s}px ${38*s}px rgba(0,0,0,.45))`}}>
      <GlassSurface accent={style.accent} strong={variant==='reveal'}
        style={{padding:`${padY}px ${padX}px`}}>{content}</GlassSurface>
    </div>
    {variant==='reveal' ? <div style={{position:'absolute',width:Math.min(width,height)*.68,
      height:Math.min(width,height)*.68,borderRadius:'50%',background:`${style.accent}12`,
      filter:`blur(${90*s}px)`,zIndex:-1}}/> : null}
  </AbsoluteFill>;
};
