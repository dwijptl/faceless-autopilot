import React from 'react';
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {BRAND, StylePack} from './styles';
import {fontFamily} from './elements';
import {GlassCard, GlassData} from './glass';

export const MOTION_CATALOG = {
  stats: ['glass', 'split', 'radial', 'ticker', 'stamp', 'horizon'],
  kinetic: ['word-pop', 'wipe', 'stack', 'emphasis', 'orbit', 'split', 'marker'],
  cards: ['definition', 'quote', 'split', 'timeline', 'warning'],
  frames: ['corners', 'film', 'grid', 'scanner', 'focus', 'aperture'],
  lowerThirds: ['rail', 'pill', 'underline', 'locator', 'index'],
  ctas: ['pill', 'stamp', 'minimal', 'orbit'],
  glass: ['fact', 'metric', 'location', 'chapter', 'reveal'],
} as const;

export type MotionSpec = {
  statVariant?: string;
  kineticVariant?: string;
  cardVariant?: string;
  frameVariant?: string;
  lowerThirdVariant?: string;
  glassVariant?: string;
};

export type StatData = {
  value?: number;
  suffix?: string;
  label?: string;
  max?: number;
  baseline?: number;
  bars?: {label?: string; value?: number}[];
};

export type CtaEvent = {
  start: number;
  duration: number;
  variant: string;
  title: string;
  subtitle: string;
  compact?: boolean;
};

const useScale = () => {
  const {width, height} = useVideoConfig();
  // Portrait layouts need room for the component padding as well as the card.
  // A 1280-wide design canvas maps cleanly into 1080-wide Shorts; landscape
  // continues to use the native 1920-wide scale.
  return width < height ? width / 1280 : Math.min(width / 1920, height / 1080);
};

const formatStat = (value: number, shown: number) =>
  Math.abs(value) >= 100 || Number.isInteger(value)
    ? Math.round(shown).toLocaleString('en-IN')
    : shown.toFixed(1);

export const AnimatedStatCard: React.FC<{
  stat: StatData;
  style: StylePack;
  variant?: string;
}> = ({stat, style, variant = 'glass'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = useScale();
  const value = Number(stat.value ?? 0);
  const shown = interpolate(frame, [7, 7 + 1.45 * fps], [0, value], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const display = formatStat(value, shown);
  const enter = spring({frame: frame - 3, fps,
    config: {damping: 16, stiffness: 135, mass: 0.75}});
  const line = interpolate(frame, [8, 8 + fps], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const number = <>{display}<span style={{fontSize: '0.47em'}}>{stat.suffix ?? ''}</span></>;
  const label = stat.label ?? '';

  let body: React.ReactNode;
  const bars = (stat.bars ?? []).slice(0, 5).filter((item) =>
    Number.isFinite(Number(item.value))
  );
  const maximum = Number(stat.max);
  const baseline = Number(stat.baseline);

  if (bars.length >= 2) {
    const barMax = Math.max(...bars.map((item) => Math.abs(Number(item.value))), 1);
    body = <div style={{width: 1050 * s, minHeight: 430 * s,
      background: 'rgba(7,14,28,.90)', borderRadius: 24 * s,
      border: `${2 * s}px solid ${style.accent}55`, padding: `${42 * s}px ${58 * s}px`,
      boxShadow: '0 28px 90px rgba(0,0,0,.58)'}}>
      <div style={{fontSize: 28 * s, color: 'rgba(255,255,255,.70)',
        textAlign: 'center', marginBottom: 30 * s, lineHeight: 1.35}}>{label}</div>
      <div style={{height: 280 * s, display: 'flex', alignItems: 'flex-end',
        justifyContent: 'center', gap: 30 * s}}>
        {bars.map((item, index) => {
          const barValue = Number(item.value);
          const height = Math.max(Math.abs(barValue) / barMax, .04) * 210 * s * line;
          const active = Math.abs(barValue) === barMax;
          return <div key={`${item.label}-${index}`} style={{width: 150 * s,
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 9 * s}}>
            <div style={{fontSize: 28 * s, color: active ? style.accent : 'white',
              fontWeight: 850}}>{formatStat(barValue, barValue * line)}{stat.suffix ?? ''}</div>
            <div style={{height, width: 82 * s, borderRadius: `${12 * s}px ${12 * s}px 3px 3px`,
              background: active ? style.accent : `${style.accent2}88`,
              boxShadow: active ? `0 0 ${28 * s}px ${style.accent}44` : 'none'}}/>
            <div style={{fontSize: 22 * s, color: 'rgba(255,255,255,.72)',
              textAlign: 'center', lineHeight: 1.25}}>{item.label ?? ''}</div>
          </div>;
        })}
      </div>
    </div>;
  } else if (Number.isFinite(baseline)) {
    const compareMax = Math.max(Math.abs(baseline), Math.abs(value), 1);
    const valueW = Math.abs(shown) / compareMax * 100;
    const baseW = Math.abs(baseline) / compareMax * 100;
    body = <div style={{width: 1050 * s, background: 'rgba(7,14,28,.91)',
      borderRadius: 24 * s, padding: `${48 * s}px ${62 * s}px`,
      border: `${2 * s}px solid ${style.accent}55`, boxShadow: '0 28px 90px rgba(0,0,0,.58)'}}>
      <div style={{fontSize: 34 * s, color: 'rgba(255,255,255,.76)',
        textAlign: 'center', marginBottom: 34 * s, lineHeight: 1.35}}>{label}</div>
      <div style={{display: 'grid', gridTemplateColumns: '1fr auto 1fr',
        alignItems: 'center', gap: 34 * s}}>
        <div style={{fontSize: 105 * s, fontWeight: 920, color: 'rgba(255,255,255,.62)',
          textAlign: 'right', lineHeight: 1}}>{formatStat(baseline, baseline)}<span style={{fontSize:'.46em'}}>{stat.suffix ?? ''}</span></div>
        <div style={{fontSize: 70 * s, color: style.accent}}>→</div>
        <div style={{fontSize: 126 * s, fontWeight: 950, color: style.accent,
          lineHeight: 1}}>{number}</div>
      </div>
      <div style={{display: 'grid', gap: 13 * s, marginTop: 35 * s}}>
        <div style={{height: 12 * s, width: `${baseW}%`, background: 'rgba(255,255,255,.30)', borderRadius: 8}}/>
        <div style={{height: 16 * s, width: `${valueW}%`, background: style.accent, borderRadius: 8,
          boxShadow: `0 0 ${20 * s}px ${style.accent}44`}}/>
      </div>
    </div>;
  } else if (Number.isFinite(maximum) && maximum > 0) {
    const radius = 156 * s;
    const circumference = 2 * Math.PI * radius;
    const ratio = Math.min(Math.max(shown / maximum, 0), 1);
    body = <div style={{width: 470 * s, height: 470 * s, position: 'relative',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <svg width={470 * s} height={470 * s} style={{position:'absolute', transform:'rotate(-90deg)'}}>
        <circle cx={235*s} cy={235*s} r={radius} fill="rgba(7,14,28,.88)"
          stroke="rgba(255,255,255,.14)" strokeWidth={24*s}/>
        <circle cx={235*s} cy={235*s} r={radius} fill="none" stroke={style.accent}
          strokeWidth={24*s} strokeLinecap="round" strokeDasharray={circumference}
          strokeDashoffset={circumference * (1-ratio)}/>
      </svg>
      <div style={{textAlign:'center', zIndex:2, maxWidth:310*s}}>
        <div style={{fontSize:112*s, fontWeight:950, color:style.accent, lineHeight:1}}>{number}</div>
        <div style={{fontSize:28*s, color:'rgba(255,255,255,.78)', lineHeight:1.35,
          marginTop:18*s}}>{label}</div>
      </div>
    </div>;
  } else if (variant === 'split') {
    body = <div style={{display: 'grid', gridTemplateColumns: '1.15fr 1fr',
      alignItems: 'stretch', width: 1080 * s, minHeight: 310 * s,
      background: 'rgba(7,14,28,0.90)', borderRadius: 18 * s,
      overflow: 'hidden', boxShadow: '0 28px 90px rgba(0,0,0,.58)'}}>
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: style.accent, fontSize: 152 * s, fontWeight: 950,
        borderRight: `${3 * s}px solid ${style.accent}`, lineHeight: 1}}>{number}</div>
      <div style={{display: 'flex', alignItems: 'center', padding: 48 * s,
        color: BRAND.text, fontSize: 42 * s, lineHeight: 1.35,
        background: `linear-gradient(135deg, ${style.accent}16, transparent)`}}>{label}</div>
    </div>;
  } else if (variant === 'radial') {
    const radius = 150 * s;
    const circumference = 2 * Math.PI * radius;
    body = <div style={{position: 'relative', width: 430 * s, height: 430 * s,
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <svg width={430 * s} height={430 * s} style={{position: 'absolute', transform: 'rotate(-90deg)'}}>
        <circle cx={215 * s} cy={215 * s} r={radius} fill="rgba(10,20,40,.70)"
          stroke="rgba(255,255,255,.13)" strokeWidth={20 * s}/>
        <circle cx={215 * s} cy={215 * s} r={radius} fill="none"
          stroke={style.accent} strokeWidth={20 * s} strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - line)}/>
      </svg>
      <div style={{textAlign: 'center', zIndex: 2}}>
        <div style={{color: style.accent, fontSize: 112 * s, fontWeight: 950,
          lineHeight: 1}}>{number}</div>
        <div style={{color: BRAND.text, fontSize: 31 * s, maxWidth: 285 * s,
          lineHeight: 1.35, marginTop: 18 * s}}>{label}</div>
      </div>
    </div>;
  } else if (variant === 'ticker') {
    body = <div style={{width: 1120 * s, borderTop: `${5 * s}px solid ${style.accent}`,
      borderBottom: `${5 * s}px solid ${style.accent}`, padding: `${38 * s}px 0`,
      background: 'rgba(4,9,18,.78)', overflow: 'hidden'}}>
      <div style={{transform: `translateX(${interpolate(enter, [0,1], [-420,0])}px)`,
        display: 'flex', alignItems: 'baseline', gap: 48 * s, whiteSpace: 'nowrap'}}>
        <div style={{fontSize: 174 * s, color: style.accent, fontWeight: 950,
          lineHeight: 1}}>{number}</div>
        <div style={{fontSize: 42 * s, color: BRAND.text, fontWeight: 650,
          whiteSpace: 'normal', lineHeight: 1.35}}>{label}</div>
      </div>
    </div>;
  } else if (variant === 'stamp') {
    body = <div style={{transform: `rotate(${interpolate(enter,[0,1],[-7,-2])}deg)`,
      border: `${8 * s}px double ${style.accent}`, padding: `${55 * s}px ${80 * s}px`,
      background: 'rgba(10,20,40,.84)', boxShadow: `14px 14px 0 ${style.accent}24`,
      textAlign: 'center', maxWidth: 950 * s}}>
      <div style={{fontSize: 166 * s, color: style.accent, fontWeight: 950,
        lineHeight: 1}}>{number}</div>
      <div style={{fontSize: 42 * s, color: BRAND.text, marginTop: 22 * s,
        textTransform: 'uppercase', lineHeight: 1.35}}>{label}</div>
    </div>;
  } else if (variant === 'horizon') {
    body = <div style={{width: '100%', textAlign: 'center'}}>
      <div style={{fontSize: 220 * s, color: style.accent, fontWeight: 950,
        lineHeight: 1, textShadow: '0 20px 70px rgba(0,0,0,.8)'}}>{number}</div>
      <div style={{height: 3 * s, width: `${line * 72}%`, margin: `${30 * s}px auto`,
        background: `linear-gradient(90deg, transparent, ${style.accent}, transparent)`}}/>
      <div style={{fontSize: 48 * s, color: BRAND.text, fontWeight: 650,
        lineHeight: 1.4, maxWidth: 1040 * s, margin: '0 auto'}}>{label}</div>
    </div>;
  } else {
    body = <div style={{background: 'linear-gradient(145deg, rgba(19,36,65,.90), rgba(8,15,30,.76))',
      backdropFilter: 'blur(16px)', border: `${2 * s}px solid ${style.accent}55`,
      borderRadius: 28 * s, padding: `${48 * s}px ${88 * s}px`, textAlign: 'center',
      boxShadow: '0 32px 90px rgba(0,0,0,.58)', minWidth: 720 * s}}>
      <div style={{fontSize: 170 * s, color: style.accent, fontWeight: 950,
        lineHeight: 1}}>{number}</div>
      <div style={{height: 6 * s, width: 390 * s * line, background: style.accent2,
        borderRadius: 3, margin: `${22 * s}px auto`}}/>
      <div style={{fontSize: 42 * s, color: BRAND.text, fontWeight: 620,
        lineHeight: 1.4, maxWidth: 780 * s}}>{label}</div>
    </div>;
  }

  return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center',
    fontFamily, padding: 70 * s}}>
    <div style={{opacity: enter, transform: `translateY(${interpolate(enter,[0,1],[70,0])}px) scale(${interpolate(enter,[0,1],[.90,1])})`}}>
      {body}
    </div>
  </AbsoluteFill>;
};

export const KineticTitle: React.FC<{
  text: string;
  style: StylePack;
  variant?: string;
}> = ({text, style, variant = 'word-pop'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = useScale();
  const words = text.split(/\s+/).filter(Boolean).slice(0, 9);
  const base = spring({frame: frame - 3, fps,
    config: {damping: 15, stiffness: 150, mass: .75}});

  if (variant === 'wipe') {
    return <AbsoluteFill style={{justifyContent: 'center', padding: 120 * s, fontFamily}}>
      <div style={{overflow: 'hidden', borderLeft: `${12 * s}px solid ${style.accent}`,
        paddingLeft: 42 * s}}>
        <div style={{transform: `translateX(${interpolate(base,[0,1],[-105,0])}%)`,
          color: 'white', fontSize: 120 * s, fontWeight: 950, lineHeight: 1.28}}>{text}</div>
      </div>
    </AbsoluteFill>;
  }
  if (variant === 'stack') {
    return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily}}>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        {words.map((word, i) => {
          const p = spring({frame: frame - 4 - i * 4, fps,
            config: {damping: 17, stiffness: 190}});
          return <div key={i} style={{fontSize: 96 * s, fontWeight: 950,
            lineHeight: 1.16, color: i % 2 ? style.accent : 'white',
            opacity: p, transform: `translateX(${interpolate(p,[0,1],[i%2?-140:140,0])}px)`}}>{word}</div>;
        })}
      </div>
    </AbsoluteFill>;
  }
  if (variant === 'emphasis') {
    const focusIndex = Math.max(words.findIndex((word) => /\d/.test(word)), words.length - 1);
    const before = words.slice(0, focusIndex).join(' ');
    const focus = words[focusIndex] ?? '';
    const after = words.slice(focusIndex + 1).join(' ');
    return <AbsoluteFill style={{justifyContent:'center', alignItems:'center', fontFamily,
      padding:100*s, textAlign:'center'}}>
      <div style={{opacity:base, maxWidth:1100*s}}>
        {before ? <div style={{fontSize:56*s, color:'white', fontWeight:760,
          lineHeight:1.4}}>{before}</div> : null}
        <div style={{fontSize:230*s, color:style.accent, fontWeight:950,
          lineHeight:1.05, transform:`scale(${interpolate(base,[0,1],[.72,1])})`,
          textShadow:`0 14px 64px ${style.accent}44`}}>{focus}</div>
        {after ? <div style={{fontSize:62*s, color:'white', fontWeight:820,
          lineHeight:1.4}}>{after}</div> : null}
      </div>
    </AbsoluteFill>;
  }
  if (variant === 'orbit') {
    return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily}}>
      <div style={{position: 'absolute', width: 720 * s, height: 720 * s,
        border: `${3 * s}px solid ${style.accent}55`, borderRadius: '50%',
        transform: `scale(${interpolate(base,[0,1],[.55,1])}) rotate(${frame * .22}deg)`}}>
        <div style={{position: 'absolute', top: -10 * s, left: '48%', width: 20 * s,
          height: 20 * s, borderRadius: '50%', background: style.accent}}/>
      </div>
      <div style={{fontSize: 105 * s, fontWeight: 950, lineHeight: 1.25,
        maxWidth: 850 * s, textAlign: 'center', color: 'white', opacity: base}}>{text}</div>
    </AbsoluteFill>;
  }
  if (variant === 'split') {
    return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily}}>
      <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center',
        maxWidth: 1200 * s, gap: 22 * s}}>
        {words.map((word, i) => {
          const p = spring({frame: frame - 2 - i * 3, fps,
            config: {damping: 13, stiffness: 210}});
          return <span key={i} style={{fontSize: 110 * s, fontWeight: 950,
            lineHeight: 1.2, color: i === words.length - 1 ? style.accent : 'white',
            opacity: p, transform: `translateY(${interpolate(p,[0,1],[i%2?-80:80,0])}px) rotate(${interpolate(p,[0,1],[i%2?-5:5,0])}deg)`}}>{word}</span>;
        })}
      </div>
    </AbsoluteFill>;
  }
  if (variant === 'marker') {
    return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily}}>
      <div style={{position: 'relative', maxWidth: 1100 * s, padding: `${20 * s}px ${42 * s}px`}}>
        <div style={{position: 'absolute', left: 0, bottom: 18 * s,
          height: 36 * s, width: `${base * 100}%`, background: style.accent,
          opacity: .78, transform: 'rotate(-1deg)'}}/>
        <div style={{position: 'relative', fontSize: 118 * s, fontWeight: 950,
          lineHeight: 1.26, color: 'white', textShadow: '0 8px 36px rgba(0,0,0,.8)'}}>{text}</div>
      </div>
    </AbsoluteFill>;
  }
  return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center',
    padding: 100 * s, fontFamily}}>
    <div style={{display: 'flex', flexWrap: 'wrap', gap: 22 * s, justifyContent: 'center'}}>
      {words.map((word, i) => {
        const p = spring({frame: frame - 5 - i * 4, fps,
          config: {damping: 13, stiffness: 205, mass: .7}});
        return <span key={i} style={{fontSize: 114 * s, fontWeight: 950,
          lineHeight: 1.24, color: i === words.length - 1 || /\d/.test(word) ? style.accent : 'white',
          opacity: p, transform: `translateY(${interpolate(p,[0,1],[68,0])}px) scale(${interpolate(p,[0,1],[.82,1])})`,
          textShadow: '0 10px 44px rgba(0,0,0,.76)'}}>{word}</span>;
      })}
    </div>
  </AbsoluteFill>;
};

export const EditorialCard: React.FC<{
  card: {kicker?: string; headline?: string; body?: string};
  style: StylePack;
  variant?: string;
}> = ({card, style, variant = 'definition'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = useScale();
  const enter = spring({frame: frame - 4, fps,
    config: {damping: 17, stiffness: 145, mass: .8}});
  const kicker = card.kicker ?? 'TERRA NOTE';
  const headline = card.headline ?? '';
  const body = card.body ?? '';
  let content: React.ReactNode;

  if (variant === 'quote') content = <div style={{maxWidth: 1050*s,
    padding:`${50*s}px ${80*s}px`,background:'rgba(8,15,30,.84)',
    borderRadius:24*s,borderLeft:`10px solid ${style.accent}`}}>
    <div style={{fontSize:150*s,color:style.accent,lineHeight:.55,fontFamily:'serif'}}>“</div>
    <div style={{fontSize:62*s,color:'white',fontWeight:760,lineHeight:1.35}}>{headline}</div>
    <div style={{fontSize:31*s,color:'rgba(255,255,255,.72)',marginTop:22*s,lineHeight:1.45}}>{body}</div>
  </div>;
  else if (variant === 'split') content = <div style={{display:'grid',gridTemplateColumns:'1fr 1.25fr',
    width:1120*s,minHeight:350*s,background:'rgba(7,14,28,.88)',borderRadius:22*s,overflow:'hidden'}}>
    <div style={{background:style.accent,color:BRAND.navy,padding:48*s,
      display:'flex',flexDirection:'column',justifyContent:'space-between'}}>
      <div style={{fontSize:22*s,fontWeight:900,letterSpacing:4}}>{kicker}</div>
      <div style={{fontSize:58*s,fontWeight:950,lineHeight:1.22}}>{headline}</div>
    </div>
    <div style={{padding:54*s,display:'flex',alignItems:'center',fontSize:38*s,
      color:'white',lineHeight:1.48}}>{body}</div>
  </div>;
  else if (variant === 'timeline') content = <div style={{width:1080*s,display:'flex',gap:36*s,
    alignItems:'stretch'}}>
    <div style={{width:6*s,background:`linear-gradient(${style.accent},${style.accent}22)`,
      position:'relative'}}><div style={{position:'absolute',left:-12*s,top:34*s,width:30*s,height:30*s,
      borderRadius:'50%',background:style.accent,boxShadow:`0 0 ${28*s}px ${style.accent}`}}/></div>
    <div style={{background:'rgba(8,16,32,.84)',padding:`${38*s}px ${52*s}px`,
      borderRadius:18*s,flex:1}}><div style={{fontSize:22*s,fontWeight:900,letterSpacing:4,
      color:style.accent}}>{kicker}</div><div style={{fontSize:63*s,fontWeight:920,color:'white',
      lineHeight:1.25,marginTop:15*s}}>{headline}</div><div style={{fontSize:34*s,color:'rgba(255,255,255,.75)',
      lineHeight:1.45,marginTop:18*s}}>{body}</div></div>
  </div>;
  else if (variant === 'warning') content = <div style={{maxWidth:1050*s,padding:`${44*s}px ${58*s}px`,
    background:'rgba(16,11,8,.88)',border:`3px solid ${style.accent}`,borderRadius:18*s,
    boxShadow:`inset 0 0 ${60*s}px ${style.accent}18`}}>
    <div style={{display:'flex',alignItems:'center',gap:28*s}}><div style={{width:0,height:0,
      borderLeft:`${32*s}px solid transparent`,borderRight:`${32*s}px solid transparent`,
      borderBottom:`${58*s}px solid ${style.accent}`,position:'relative'}}><span style={{position:'absolute',
      left:-5*s,top:21*s,color:BRAND.navy,fontWeight:950,fontSize:26*s}}>!</span></div>
      <div><div style={{fontSize:21*s,fontWeight:900,letterSpacing:4,color:style.accent}}>{kicker}</div>
      <div style={{fontSize:62*s,fontWeight:930,color:'white',lineHeight:1.24,marginTop:8*s}}>{headline}</div></div></div>
    <div style={{fontSize:34*s,color:'rgba(255,255,255,.76)',lineHeight:1.45,marginTop:27*s}}>{body}</div>
  </div>;
  else content = <div style={{maxWidth:1050*s,padding:`${48*s}px ${64*s}px`,
    background:'linear-gradient(145deg,rgba(19,36,65,.92),rgba(7,14,28,.82))',
    borderRadius:26*s,border:`2px solid ${style.accent}55`,boxShadow:'0 30px 90px rgba(0,0,0,.55)'}}>
    <div style={{fontSize:22*s,fontWeight:900,letterSpacing:5,color:style.accent}}>{kicker}</div>
    <div style={{height:4*s,width:120*s,background:style.accent,margin:`${18*s}px 0`}}/>
    <div style={{fontSize:66*s,fontWeight:930,color:'white',lineHeight:1.25}}>{headline}</div>
    <div style={{fontSize:35*s,color:'rgba(255,255,255,.76)',lineHeight:1.48,marginTop:22*s}}>{body}</div>
  </div>;

  return <AbsoluteFill style={{justifyContent:'center',alignItems:'center',padding:80*s,fontFamily}}>
    <div style={{opacity:enter,transform:`translateY(${interpolate(enter,[0,1],[60,0])}px) scale(${interpolate(enter,[0,1],[.94,1])})`}}>{content}</div>
  </AbsoluteFill>;
};

export const SceneFrame: React.FC<{
  variant?: string;
  style: StylePack;
  sceneN: number;
}> = ({variant = 'corners', style, sceneN}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const s = useScale();
  const reveal = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  if (variant === 'film') {
    return <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{height: 42 * s, background: 'rgba(0,0,0,.82)'}}/>
      <div style={{position: 'absolute', bottom: 0, height: 42 * s, width: '100%',
        background: 'rgba(0,0,0,.82)'}}/>
      <div style={{position: 'absolute', right: 36 * s, bottom: 55 * s,
        fontFamily, fontSize: 18 * s, letterSpacing: 5, color: 'rgba(255,255,255,.55)'}}>
        TI · {String(sceneN).padStart(2, '0')}
      </div>
    </AbsoluteFill>;
  }
  if (variant === 'grid') {
    return <AbsoluteFill style={{pointerEvents: 'none', opacity: .18 * reveal,
      backgroundImage: `linear-gradient(${style.accent}66 1px, transparent 1px), linear-gradient(90deg, ${style.accent}66 1px, transparent 1px)`,
      backgroundSize: `${96 * s}px ${96 * s}px`}}/>;
  }
  if (variant === 'scanner') {
    const y = interpolate(frame % 120, [0, 119], [-20, height + 20]);
    return <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: y, left: 0, width: '100%', height: 3 * s,
        background: style.accent, boxShadow: `0 0 ${22 * s}px ${style.accent}`,
        opacity: .42}}/>
      <div style={{position: 'absolute', inset: 30 * s,
        border: `${1 * s}px solid ${style.accent}44`}}/>
    </AbsoluteFill>;
  }
  if (variant === 'focus') {
    return <AbsoluteFill style={{pointerEvents: 'none', justifyContent: 'center', alignItems: 'center'}}>
      <div style={{width: Math.min(width, height) * .42, height: Math.min(width, height) * .42,
        border: `${2 * s}px solid ${style.accent}77`, borderRadius: '50%',
        transform: `scale(${interpolate(reveal,[0,1],[1.35,1])})`}}/>
      <div style={{position: 'absolute', width: 1, height: '72%', background: `${style.accent}35`}}/>
      <div style={{position: 'absolute', height: 1, width: '72%', background: `${style.accent}35`}}/>
    </AbsoluteFill>;
  }
  if (variant === 'aperture') {
    return <AbsoluteFill style={{pointerEvents: 'none', opacity: .32,
      background: `conic-gradient(from ${frame * .12}deg at 50% 50%, transparent 0 12%, ${style.accent}22 12% 14%, transparent 14% 26%, ${style.accent}18 26% 28%, transparent 28% 100%)`,
      maskImage: 'radial-gradient(circle, transparent 0 32%, black 60%, transparent 90%)'}}/>;
  }
  const size = 110 * s;
  const corner = (pos: React.CSSProperties) => <div style={{position: 'absolute',
    width: size, height: size, ...pos, borderColor: style.accent,
    opacity: reveal * .78}}/>;
  return <AbsoluteFill style={{pointerEvents: 'none', padding: 34 * s}}>
    {corner({top: 34*s,left: 34*s,borderTop: `${4*s}px solid`,borderLeft: `${4*s}px solid`})}
    {corner({top: 34*s,right: 34*s,borderTop: `${4*s}px solid`,borderRight: `${4*s}px solid`})}
    {corner({bottom: 34*s,left: 34*s,borderBottom: `${4*s}px solid`,borderLeft: `${4*s}px solid`})}
    {corner({bottom: 34*s,right: 34*s,borderBottom: `${4*s}px solid`,borderRight: `${4*s}px solid`})}
  </AbsoluteFill>;
};

export const AnimatedLowerThird: React.FC<{
  title: string;
  style: StylePack;
  variant?: string;
  index?: number;
}> = ({title, style, variant = 'rail', index = 1}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const s = useScale();
  const enter = spring({frame: frame - 7, fps, config: {damping: 18, stiffness: 150}});
  const common: React.CSSProperties = {position: 'absolute', left: 54 * s,
    top: height * .085, fontFamily, opacity: enter,
    transform: `translateX(${interpolate(enter,[0,1],[-320,0])}px)`};
  if (variant === 'pill') return <div style={{...common, borderRadius: 999,
    background: style.accent, color: BRAND.navy, fontSize: 31 * s,
    fontWeight: 850, padding: `${10*s}px ${26*s}px`}}>{title}</div>;
  if (variant === 'underline') return <div style={{...common, color: 'white',
    fontSize: 36*s, fontWeight: 750}}>{title}<div style={{height: 4*s,
      width: 150*s*enter, background: style.accent, marginTop: 8*s}}/></div>;
  if (variant === 'locator') return <div style={{...common, display: 'flex',
    alignItems: 'center', gap: 16*s, color: 'white', fontSize: 34*s, fontWeight: 760}}>
      <div style={{width: 24*s,height: 24*s,borderRadius:'50%',border:`5px solid ${style.accent}`,
        boxShadow:`0 0 ${18*s}px ${style.accent}`}}/>{title}</div>;
  if (variant === 'index') return <div style={{...common, display:'flex',alignItems:'center',gap:18*s}}>
      <div style={{fontSize:68*s,fontWeight:950,color:style.accent,lineHeight:1}}>{String(index).padStart(2,'0')}</div>
      <div style={{width:2*s,height:60*s,background:'rgba(255,255,255,.35)'}}/>
      <div style={{fontSize:34*s,fontWeight:720,color:'white'}}>{title}</div></div>;
  return <div style={{...common, display:'flex',alignItems:'center',gap:16*s}}>
    <div style={{width:9*s,height:58*s,background:style.accent,borderRadius:4*s}}/>
    <div style={{fontSize:35*s,fontWeight:760,color:'white',background:'rgba(6,12,24,.68)',
      padding:`9px ${18*s}px`,borderRadius:8*s}}>{title}</div></div>;
};

const BellIcon: React.FC<{accent: string; progress: number; size: number}> = ({accent, progress, size}) => {
  const wobble = Math.sin(progress * Math.PI * 5) * (1 - progress) * 16;
  return <div style={{position:'relative',width:size,height:size,
    transform:`rotate(${wobble}deg)`,transformOrigin:'50% 15%'}}>
    <svg viewBox="0 0 64 64" width={size} height={size}>
      <path d="M17 43h30l-4-6V26c0-7-4-12-11-13-7 1-11 6-11 13v11z"
        fill="none" stroke={accent} strokeWidth="5" strokeLinejoin="round"/>
      <path d="M27 47c1 5 9 5 10 0" fill="none" stroke={accent} strokeWidth="5"
        strokeLinecap="round"/>
      <path d="M32 7v4" stroke={accent} strokeWidth="5" strokeLinecap="round"/>
    </svg>
    <div style={{position:'absolute',inset:-size*.18,border:`2px solid ${accent}`,
      borderRadius:'50%',opacity:interpolate(progress,[0,.35,1],[0,.7,0]),
      transform:`scale(${interpolate(progress,[0,1],[.6,1.35])})`}}/>
  </div>;
};

export const SubscribeBell: React.FC<{event: CtaEvent; style: StylePack}> = ({event, style}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = useScale();
  const enter = spring({frame, fps, config:{damping:15,stiffness:170,mass:.7}});
  const bellProgress = Math.min(Math.max((frame - fps*.35)/(fps*.9),0),1);
  const compact = Boolean(event.compact);
  const icon = <div style={{width:(compact?58:72)*s,height:(compact?58:72)*s,
    borderRadius:'50%',background:style.accent,display:'flex',alignItems:'center',
    justifyContent:'center',boxShadow:`0 0 ${28*s}px ${style.accent}55`}}>
      <div style={{width:0,height:0,borderTop:`${11*s}px solid transparent`,
        borderBottom:`${11*s}px solid transparent`,borderLeft:`${18*s}px solid ${BRAND.navy}`,
        marginLeft:4*s}}/>
    </div>;
  const bell = <BellIcon accent={style.accent} progress={bellProgress} size={(compact?48:60)*s}/>;
  const text = <div><div style={{fontSize:(compact?28:35)*s,fontWeight:900,color:'white',
    lineHeight:1.25}}>{event.title}</div>{!compact ? <div style={{fontSize:22*s,
      color:'rgba(255,255,255,.72)',marginTop:4*s}}>{event.subtitle}</div> : null}</div>;

  let body: React.ReactNode;
  if (event.variant === 'stamp') body = <div style={{display:'flex',alignItems:'center',gap:18*s,
    border:`4px double ${style.accent}`,background:'rgba(7,13,25,.88)',
    padding:`${14*s}px ${22*s}px`,transform:'rotate(-2deg)'}}>{icon}{text}{bell}</div>;
  else if (event.variant === 'minimal') body = <div style={{display:'flex',alignItems:'center',
    gap:15*s,background:'rgba(6,12,24,.65)',borderBottom:`3px solid ${style.accent}`,
    padding:`${10*s}px ${18*s}px`}}>{icon}{text}{bell}</div>;
  else if (event.variant === 'orbit') body = <div style={{display:'flex',alignItems:'center',gap:20*s,
    background:'rgba(7,14,29,.88)',padding:`${13*s}px ${24*s}px`,borderRadius:18*s,
    boxShadow:`0 0 0 ${3*s}px ${style.accent}33, 0 20px 60px rgba(0,0,0,.45)`}}>
    <div style={{position:'relative'}}>{icon}<div style={{position:'absolute',inset:-9*s,
      border:`2px dashed ${style.accent}`,borderRadius:'50%',transform:`rotate(${frame*3}deg)`}}/></div>{text}{bell}</div>;
  else body = <div style={{display:'flex',alignItems:'center',gap:18*s,
    background:'rgba(8,16,32,.90)',border:`2px solid ${style.accent}66`,
    borderRadius:999,padding:`${11*s}px ${20*s}px ${11*s}px ${12*s}px`,
    boxShadow:'0 20px 60px rgba(0,0,0,.48)'}}>{icon}{text}{bell}</div>;

  return <div style={{position:'absolute',right:compact?26*s:48*s,
    top:compact?height*.16:height*.13,fontFamily,
    opacity:enter,transform:`translateX(${interpolate(enter,[0,1],[220,0])}px) scale(${interpolate(enter,[0,1],[.88,1])})`,
    maxWidth:width*.72}}>{body}</div>;
};

export const CtaLayer: React.FC<{event?: CtaEvent | null; style: StylePack; fps: number}> = ({event, style, fps}) => {
  if (!event) return null;
  return <Sequence from={Math.max(0,Math.round(event.start*fps))}
    durationInFrames={Math.max(2,Math.round(event.duration*fps))}>
    <SubscribeBell event={event} style={style}/>
  </Sequence>;
};

type GalleryItem = {family:string;variant:string};
const GALLERY: GalleryItem[] = [
  ...MOTION_CATALOG.stats.map((variant)=>({family:'STAT',variant})),
  ...MOTION_CATALOG.kinetic.map((variant)=>({family:'TITLE',variant})),
  ...MOTION_CATALOG.cards.map((variant)=>({family:'CARD',variant})),
  ...MOTION_CATALOG.frames.map((variant)=>({family:'FRAME',variant})),
  ...MOTION_CATALOG.lowerThirds.map((variant)=>({family:'LOWER THIRD',variant})),
  ...MOTION_CATALOG.ctas.map((variant)=>({family:'CTA',variant})),
  ...MOTION_CATALOG.glass.map((variant)=>({family:'GLASS',variant})),
];

export const MOTION_GALLERY_DURATION = GALLERY.length * 75;

const galleryStat = (variant: string): StatData => {
  if (variant === 'glass') return {value:50,suffix:'%',label:'समुद्र का संरक्षित हिस्सा',max:100};
  if (variant === 'split') return {value:49,suffix:'%',label:'ऑक्सीजन स्तर',baseline:8};
  if (variant === 'radial') return {suffix:'%',label:'तीन क्षेत्रों की तुलना',bars:[
    {label:'उत्तर',value:28},{label:'मध्य',value:49},{label:'दक्षिण',value:36},
  ]};
  return {value:12742,suffix:' km',label:'एक असंभव लगने वाली दूरी'};
};

const galleryGlass = (variant: string): GlassData => {
  if (variant === 'metric') return {kicker:'लवणता',value:35,suffix:'‰',
    label:'औसत समुद्री लवणता',delta:12,deltaDirection:'down'};
  if (variant === 'location') return {location:'मरियाना गर्त',
    coordinates:'11.3°N · 142.2°E',headline:'प्रशांत महासागर'};
  if (variant === 'chapter') return {chapter:'भाग 02',
    headline:'पानी नीचे कहाँ जाता है?',body:'समुद्र की सबसे गहरी परतों में'};
  if (variant === 'reveal') return {kicker:'अंतिम उत्तर',value:11034,suffix:' मीटर',
    label:'सबसे गहरा ज्ञात बिंदु',body:'माउंट एवरेस्ट से भी अधिक गहरा'};
  return {kicker:'गहराई',value:8848,suffix:' मीटर',
    headline:'एवरेस्ट की पूरी ऊँचाई',body:'फिर भी यह तल तक नहीं पहुँचेगा।'};
};

export const MotionGallery: React.FC<{style: StylePack}> = ({style}) => (
  <AbsoluteFill style={{background:`radial-gradient(circle at 30% 20%, ${BRAND.panel}, ${BRAND.navy} 65%)`,fontFamily}}>
    {GALLERY.map((item,index)=><Sequence key={`${item.family}-${item.variant}`}
      from={index*75} durationInFrames={75}>
      <AbsoluteFill>
        <div style={{position:'absolute',left:42,top:28,zIndex:20,color:style.accent,
          fontSize:22,fontWeight:900,letterSpacing:4}}>{item.family} · {item.variant.toUpperCase()}</div>
        {item.family==='STAT' ? <AnimatedStatCard stat={galleryStat(item.variant)} style={style} variant={item.variant}/> : null}
        {item.family==='TITLE' ? <KineticTitle text="धरती का सबसे गहरा रहस्य" style={style} variant={item.variant}/> : null}
        {item.family==='CARD' ? <EditorialCard card={{kicker:'FIELD NOTE',headline:'यहाँ समय अलग चलता है',body:'एक साफ, सिनेमाई व्याख्या जो दर्शक तुरंत समझ सके।'}} style={style} variant={item.variant}/> : null}
        {item.family==='FRAME' ? <><div style={{position:'absolute',inset:180,background:`linear-gradient(135deg,${style.accent}22,${BRAND.panel})`,borderRadius:28}}/><SceneFrame variant={item.variant} style={style} sceneN={index+1}/></> : null}
        {item.family==='LOWER THIRD' ? <AnimatedLowerThird title="अज्ञात की सीमा" style={style} variant={item.variant} index={index+1}/> : null}
        {item.family==='CTA' ? <SubscribeBell event={{start:0,duration:2.5,variant:item.variant,title:'सब्सक्राइब करें',subtitle:'नई खोजें हर हफ्ते'}} style={style}/> : null}
        {item.family==='GLASS' ? <GlassCard data={galleryGlass(item.variant)} style={style} variant={item.variant}/> : null}
      </AbsoluteFill>
    </Sequence>)}
  </AbsoluteFill>
);
