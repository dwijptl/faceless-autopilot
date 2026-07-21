/** Terra Incognita brand tokens + the topic-driven visual identity system.
 *
 * v2 — 30 distinct style packs. Brand stays constant (watermark, outro,
 * channel name); everything else — palette, font pairing, caption
 * treatment, grade, texture, transition grammar — belongs to the pack.
 * The pack is chosen from the TOPIC (pipeline/style_packs.py), so a deep-sea
 * video looks nothing like a space video, which looks nothing like a
 * history video. pipeline/style_packs.py mirrors this registry (AI-image
 * wrappers, hero-shot cameras, topic keywords) — tests keep both in sync.
 *
 * Devanagari rules for every pack: letterSpacing >= 0 on Hindi text,
 * word-level animation only, lineHeight >= 1.2.
 */

export const BRAND = {
  navy: '#0A1428',
  panel: '#132441',
  amber: '#FFB020',
  amberSoft: '#FFC85C',
  sky: '#4DA3FF',
  text: '#F4F7FB',
};

export type CaptionVariant =
  | 'pop'      // karaoke word-pop, stroked, growing underline
  | 'boxed'    // dark box, accent left border
  | 'minimal'  // clean line, thin accent underline
  | 'chip'     // dark chip, accent bottom rule
  | 'outline'  // huge stroked words, no scrim, seeded per-word tilt
  | 'serif'    // editorial line between hairlines, no karaoke
  | 'ribbon'   // full-width broadcast band
  | 'glow'     // neon accent glow words
  | 'ledger'   // left-aligned column with vertical rule
  | 'stamp'    // tilted double-border card
  | 'duotone'  // alternating two-tone words, heavy shadow, no box
  | 'band';    // compact bar with accent notch

export type TextureKind =
  | 'none'
  | 'grain'      // film grain + soft vignette
  | 'vignette'   // heavy corners, no grain
  | 'halation'   // soft accent bloom
  | 'scanlines'  // thin CRT lines
  | 'paper';     // warm archival wash + grain

export type TransitionBias =
  | 'mixed' | 'slides' | 'fades' | 'wipes' | 'whips' | 'punches';

// ── Layout DNA: where things LIVE on screen, per pack ──────────────────
export type CaptionAlign = 'center' | 'left' | 'right';
export type LowerThirdPos = 'tl' | 'tr' | 'bl';
export type OverlayAnchor = 'center' | 'left' | 'right' | 'high';
export type WatermarkCorner = 'br' | 'bl' | 'tl' | 'tr';
export type ProgressStyle = 'top' | 'bottom' | 'bottom-thick' | 'none';

export type PackLayout = {
  captionAlign: CaptionAlign;
  captionY: number;        // long-form caption anchor (fraction of height)
  lowerThird: LowerThirdPos;
  overlayAnchor: OverlayAnchor; // where stat/card/glass/kinetic graphics sit
  watermark: WatermarkCorner;
  progress: ProgressStyle;
};

// ── Motion DNA: how things MOVE, per pack ──────────────────────────────
export type CaptionEntry = 'pop' | 'fade' | 'rise' | 'slide';
export type Springiness = 'calm' | 'settle' | 'snappy';

export type PackMotion = {
  entry: CaptionEntry;   // caption entrance animation
  spring: Springiness;   // card/lower-third spring character
  kenBurns: number;      // still-photo movement energy (0.6 calm – 1.5 punchy)
};

export type StylePack = {
  name: string;
  accent: string;
  accent2: string;
  bg: string;
  panel: string; // card/panel base tint (hex) — overlays derive rgba from it
  fontHeading: string; // @remotion/google-fonts module name (see fonts.ts)
  fontBody: string;
  captionVariant: CaptionVariant;
  lowerThirdVariant: 'bar' | 'chip' | 'underline';
  gradeOverlay: string; // CSS background layered over footage
  visualFilter: string; // CSS filter applied to footage
  transitionBias: TransitionBias;
  texture: TextureKind;
  layout: PackLayout;
  motion: PackMotion;
  hud?: boolean; // persistent sci-doc HUD overlay
};

/** rgba() from a #RRGGBB hex — used to tint panels per pack. */
export const hexA = (hex: string, alpha: number): string => {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
};

/** Panel background for cards/overlays, tinted to the pack. */
export const panelBg = (style: StylePack, alpha = 0.9): string =>
  hexA(style.panel, alpha);

export const STYLE_PACKS: Record<string, StylePack> = {
  // ── The original five, now with their own type ───────────────────────
  documentary: {
    name: 'documentary',
    accent: '#FFB020', accent2: '#4DA3FF', bg: '#0A1428', panel: '#0E1B33',
    fontHeading: 'Mukta', fontBody: 'Mukta',
    captionVariant: 'pop', lowerThirdVariant: 'bar',
    gradeOverlay:
      'linear-gradient(180deg, rgba(255,176,32,0.05) 0%, rgba(10,20,40,0.14) 100%)',
    visualFilter: 'saturate(1.06) contrast(1.04)',
    transitionBias: 'mixed', texture: 'grain',
    layout: {captionAlign: 'center', captionY: 0.78, lowerThird: 'tl',
      overlayAnchor: 'center', watermark: 'br', progress: 'top'},
    motion: {entry: 'pop', spring: 'settle', kenBurns: 1.0},
  },
  kinetic: {
    name: 'kinetic',
    accent: '#FFB020', accent2: '#FFFFFF', bg: '#080D1A', panel: '#0B1224',
    fontHeading: 'Poppins', fontBody: 'Poppins',
    captionVariant: 'boxed', lowerThirdVariant: 'chip',
    gradeOverlay:
      'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(4,8,16,0.42) 100%)',
    visualFilter: 'saturate(1.16) contrast(1.12)',
    transitionBias: 'whips', texture: 'none',
    layout: {captionAlign: 'center', captionY: 0.74, lowerThird: 'tl',
      overlayAnchor: 'center', watermark: 'tl', progress: 'top'},
    motion: {entry: 'pop', spring: 'snappy', kenBurns: 1.35},
  },
  editorial: {
    name: 'editorial',
    accent: '#FFC85C', accent2: '#4DA3FF', bg: '#101720', panel: '#161F2B',
    fontHeading: 'RozhaOne', fontBody: 'Martel',
    captionVariant: 'serif', lowerThirdVariant: 'underline',
    gradeOverlay:
      'linear-gradient(180deg, rgba(77,163,255,0.05) 0%, rgba(16,23,32,0.12) 100%)',
    visualFilter: 'saturate(0.92) contrast(1.02)',
    transitionBias: 'fades', texture: 'paper',
    layout: {captionAlign: 'center', captionY: 0.8, lowerThird: 'tr',
      overlayAnchor: 'center', watermark: 'br', progress: 'none'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.7},
  },
  noir: {
    name: 'noir',
    accent: '#E8ECF4', accent2: '#FFB020', bg: '#06090F', panel: '#0A0F17',
    fontHeading: 'Teko', fontBody: 'Hind',
    captionVariant: 'chip', lowerThirdVariant: 'bar',
    gradeOverlay:
      'linear-gradient(180deg, rgba(10,20,40,0.22) 0%, rgba(6,9,15,0.38) 100%)',
    visualFilter: 'grayscale(0.85) contrast(1.18) brightness(0.96)',
    transitionBias: 'wipes', texture: 'vignette',
    layout: {captionAlign: 'left', captionY: 0.76, lowerThird: 'bl',
      overlayAnchor: 'left', watermark: 'bl', progress: 'bottom'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.8},
  },
  telemetry: {
    name: 'telemetry',
    accent: '#6FE3D4', accent2: '#FFB020', bg: '#060B14', panel: '#0A1420',
    fontHeading: 'Rajdhani', fontBody: 'AnekDevanagari',
    captionVariant: 'minimal', lowerThirdVariant: 'underline',
    gradeOverlay:
      'linear-gradient(180deg, rgba(111,227,212,0.04) 0%, rgba(6,11,20,0.30) 100%)',
    visualFilter: 'saturate(0.88) contrast(1.10) brightness(0.97)',
    transitionBias: 'fades', texture: 'scanlines', hud: true,
    layout: {captionAlign: 'left', captionY: 0.74, lowerThird: 'tr',
      overlayAnchor: 'left', watermark: 'tr', progress: 'top'},
    motion: {entry: 'rise', spring: 'settle', kenBurns: 0.75},
  },

  // ── History / culture ────────────────────────────────────────────────
  archive: {
    name: 'archive', // old records, lost history, "पुराना"
    accent: '#D8A24A', accent2: '#B8B2A6', bg: '#14100A', panel: '#1C1610',
    fontHeading: 'Halant', fontBody: 'Martel',
    captionVariant: 'ledger', lowerThirdVariant: 'underline',
    gradeOverlay:
      'linear-gradient(180deg, rgba(216,162,74,0.08) 0%, rgba(20,16,10,0.34) 100%)',
    visualFilter: 'sepia(0.34) saturate(0.86) contrast(1.06)',
    transitionBias: 'fades', texture: 'paper',
    layout: {captionAlign: 'left', captionY: 0.78, lowerThird: 'bl',
      overlayAnchor: 'left', watermark: 'br', progress: 'bottom'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.75},
  },
  manuscript: {
    name: 'manuscript', // mythology, ancient texts, sacred geometry
    accent: '#C9A86A', accent2: '#8E7CFF', bg: '#100C14', panel: '#171120',
    fontHeading: 'Amita', fontBody: 'TiroDevanagariHindi',
    captionVariant: 'serif', lowerThirdVariant: 'underline',
    gradeOverlay:
      'radial-gradient(ellipse at 50% 20%, rgba(201,168,106,0.07) 0%, rgba(16,12,20,0.36) 100%)',
    visualFilter: 'sepia(0.18) saturate(0.9) contrast(1.05) brightness(0.97)',
    transitionBias: 'fades', texture: 'paper',
    layout: {captionAlign: 'center', captionY: 0.8, lowerThird: 'tr',
      overlayAnchor: 'center', watermark: 'br', progress: 'none'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.65},
  },
  relic: {
    name: 'relic', // archaeology, ruins, museums
    accent: '#B08D57', accent2: '#E5DDD0', bg: '#0E0D0B', panel: '#161412',
    fontHeading: 'Halant', fontBody: 'Laila',
    captionVariant: 'serif', lowerThirdVariant: 'bar',
    gradeOverlay:
      'linear-gradient(180deg, rgba(176,141,87,0.06) 0%, rgba(14,13,11,0.40) 100%)',
    visualFilter: 'saturate(0.8) contrast(1.12) brightness(0.95)',
    transitionBias: 'wipes', texture: 'vignette',
    layout: {captionAlign: 'center', captionY: 0.78, lowerThird: 'bl',
      overlayAnchor: 'center', watermark: 'bl', progress: 'bottom'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.7},
  },
  bazaar: {
    name: 'bazaar', // Indian festivals, food, street culture
    accent: '#FF9F1C', accent2: '#E71D73', bg: '#170A12', panel: '#22101B',
    fontHeading: 'YatraOne', fontBody: 'Mukta',
    captionVariant: 'band', lowerThirdVariant: 'chip',
    gradeOverlay:
      'linear-gradient(160deg, rgba(255,159,28,0.08) 0%, rgba(231,29,115,0.06) 55%, rgba(23,10,18,0.30) 100%)',
    visualFilter: 'saturate(1.28) contrast(1.06)',
    transitionBias: 'slides', texture: 'grain',
    layout: {captionAlign: 'center', captionY: 0.76, lowerThird: 'tl',
      overlayAnchor: 'center', watermark: 'tr', progress: 'top'},
    motion: {entry: 'slide', spring: 'snappy', kenBurns: 1.2},
  },
  terracotta: {
    name: 'terracotta', // crafts, villages, human stories, warm earth
    accent: '#E2725B', accent2: '#F4D8A8', bg: '#1A0F0A', panel: '#241511',
    fontHeading: 'Baloo2', fontBody: 'Baloo2',
    captionVariant: 'band', lowerThirdVariant: 'chip',
    gradeOverlay:
      'linear-gradient(180deg, rgba(226,114,91,0.08) 0%, rgba(26,15,10,0.26) 100%)',
    visualFilter: 'saturate(1.12) contrast(1.02) sepia(0.08)',
    transitionBias: 'slides', texture: 'grain',
    layout: {captionAlign: 'right', captionY: 0.78, lowerThird: 'tl',
      overlayAnchor: 'right', watermark: 'br', progress: 'top'},
    motion: {entry: 'rise', spring: 'settle', kenBurns: 0.95},
  },
  folklore: {
    name: 'folklore', // legends, village mysteries, night stories
    accent: '#C9B458', accent2: '#9C6BFF', bg: '#0B0714', panel: '#140E20',
    fontHeading: 'Kalam', fontBody: 'Sarala',
    captionVariant: 'stamp', lowerThirdVariant: 'underline',
    gradeOverlay:
      'radial-gradient(ellipse at 50% 80%, rgba(201,180,88,0.07) 0%, rgba(11,7,20,0.42) 100%)',
    visualFilter: 'saturate(0.94) contrast(1.08) brightness(0.94)',
    transitionBias: 'fades', texture: 'vignette',
    layout: {captionAlign: 'center', captionY: 0.8, lowerThird: 'bl',
      overlayAnchor: 'center', watermark: 'bl', progress: 'none'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.7},
  },

  // ── Space / physics ──────────────────────────────────────────────────
  cosmos: {
    name: 'cosmos', // space, planets, deep sky
    accent: '#8E7CFF', accent2: '#E8E4FF', bg: '#05060F', panel: '#0B0C1E',
    fontHeading: 'Khand', fontBody: 'Palanquin',
    captionVariant: 'outline', lowerThirdVariant: 'underline',
    gradeOverlay:
      'radial-gradient(ellipse at 50% 10%, rgba(142,124,255,0.07) 0%, rgba(5,6,15,0.38) 100%)',
    visualFilter: 'saturate(1.08) contrast(1.10) brightness(0.96)',
    transitionBias: 'punches', texture: 'halation',
    layout: {captionAlign: 'center', captionY: 0.74, lowerThird: 'tr',
      overlayAnchor: 'center', watermark: 'tr', progress: 'none'},
    motion: {entry: 'rise', spring: 'settle', kenBurns: 0.9},
  },
  quantum: {
    name: 'quantum', // physics, particles, the very small
    accent: '#B26BFF', accent2: '#6FE3D4', bg: '#060310', panel: '#0D081C',
    fontHeading: 'Rajdhani', fontBody: 'Palanquin',
    captionVariant: 'minimal', lowerThirdVariant: 'underline',
    gradeOverlay:
      'radial-gradient(ellipse at 30% 30%, rgba(178,107,255,0.06) 0%, rgba(6,3,16,0.36) 100%)',
    visualFilter: 'saturate(1.05) contrast(1.12) hue-rotate(-6deg)',
    transitionBias: 'punches', texture: 'halation',
    layout: {captionAlign: 'left', captionY: 0.72, lowerThird: 'tr',
      overlayAnchor: 'left', watermark: 'tl', progress: 'top'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.8},
  },
  horizon: {
    name: 'horizon', // exploration, records, human achievement
    accent: '#FF8E5A', accent2: '#FFD86B', bg: '#120D14', panel: '#1B1420',
    fontHeading: 'Eczar', fontBody: 'Mukta',
    captionVariant: 'pop', lowerThirdVariant: 'bar',
    gradeOverlay:
      'linear-gradient(200deg, rgba(255,142,90,0.09) 0%, rgba(18,13,20,0.30) 100%)',
    visualFilter: 'saturate(1.14) contrast(1.05)',
    transitionBias: 'mixed', texture: 'halation',
    layout: {captionAlign: 'center', captionY: 0.78, lowerThird: 'tl',
      overlayAnchor: 'center', watermark: 'br', progress: 'top'},
    motion: {entry: 'pop', spring: 'settle', kenBurns: 1.1},
  },

  // ── Ocean / water / weather ──────────────────────────────────────────
  abyss: {
    name: 'abyss', // deep sea, trenches, bioluminescence
    accent: '#35E0C8', accent2: '#2E77B8', bg: '#02070C', panel: '#061219',
    fontHeading: 'Rajdhani', fontBody: 'Sarala',
    captionVariant: 'glow', lowerThirdVariant: 'underline',
    gradeOverlay:
      'linear-gradient(180deg, rgba(46,119,184,0.10) 0%, rgba(2,7,12,0.46) 100%)',
    visualFilter: 'saturate(0.92) contrast(1.14) brightness(0.92) hue-rotate(8deg)',
    transitionBias: 'fades', texture: 'vignette',
    layout: {captionAlign: 'left', captionY: 0.76, lowerThird: 'bl',
      overlayAnchor: 'left', watermark: 'bl', progress: 'bottom'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.7},
  },
  monsoon: {
    name: 'monsoon', // rain, rivers, climate, forests in weather
    accent: '#7FD069', accent2: '#9DB8CC', bg: '#0A1410', panel: '#101B16',
    fontHeading: 'Hind', fontBody: 'Hind',
    captionVariant: 'boxed', lowerThirdVariant: 'bar',
    gradeOverlay:
      'linear-gradient(180deg, rgba(157,184,204,0.07) 0%, rgba(10,20,16,0.32) 100%)',
    visualFilter: 'saturate(1.02) contrast(1.05) brightness(0.96)',
    transitionBias: 'fades', texture: 'grain',
    layout: {captionAlign: 'center', captionY: 0.8, lowerThird: 'tl',
      overlayAnchor: 'center', watermark: 'br', progress: 'top'},
    motion: {entry: 'rise', spring: 'settle', kenBurns: 0.85},
  },
  storm: {
    name: 'storm', // cyclones, lightning, extreme weather
    accent: '#F5D547', accent2: '#8FA8C8', bg: '#0A0E14', panel: '#101722',
    fontHeading: 'Teko', fontBody: 'Hind',
    captionVariant: 'duotone', lowerThirdVariant: 'bar',
    gradeOverlay:
      'linear-gradient(180deg, rgba(143,168,200,0.09) 0%, rgba(10,14,20,0.40) 100%)',
    visualFilter: 'saturate(0.88) contrast(1.18) brightness(0.93)',
    transitionBias: 'punches', texture: 'grain',
    layout: {captionAlign: 'center', captionY: 0.72, lowerThird: 'tl',
      overlayAnchor: 'center', watermark: 'tl', progress: 'top'},
    motion: {entry: 'pop', spring: 'snappy', kenBurns: 1.4},
  },
  glacier: {
    name: 'glacier', // ice, poles, high mountains, cold
    accent: '#9FD8F0', accent2: '#FFFFFF', bg: '#0A1218', panel: '#101A22',
    fontHeading: 'Palanquin', fontBody: 'Palanquin',
    captionVariant: 'minimal', lowerThirdVariant: 'underline',
    gradeOverlay:
      'linear-gradient(180deg, rgba(159,216,240,0.08) 0%, rgba(10,18,24,0.26) 100%)',
    visualFilter: 'saturate(0.82) contrast(1.08) brightness(1.02)',
    transitionBias: 'fades', texture: 'none',
    layout: {captionAlign: 'center', captionY: 0.8, lowerThird: 'tr',
      overlayAnchor: 'center', watermark: 'tr', progress: 'none'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.6},
  },

  // ── Earth / nature / wildlife ────────────────────────────────────────
  safari: {
    name: 'safari', // wildlife, predators, animal behaviour
    accent: '#C8A24A', accent2: '#8FA65A', bg: '#12100A', panel: '#1A1710',
    fontHeading: 'Teko', fontBody: 'Mukta',
    captionVariant: 'pop', lowerThirdVariant: 'bar',
    gradeOverlay:
      'linear-gradient(180deg, rgba(200,162,74,0.07) 0%, rgba(18,16,10,0.30) 100%)',
    visualFilter: 'saturate(1.12) contrast(1.08) sepia(0.06)',
    transitionBias: 'mixed', texture: 'grain',
    layout: {captionAlign: 'left', captionY: 0.78, lowerThird: 'tl',
      overlayAnchor: 'left', watermark: 'br', progress: 'top'},
    motion: {entry: 'pop', spring: 'settle', kenBurns: 1.05},
  },
  verdant: {
    name: 'verdant', // plants, fungi, micro-ecosystems
    accent: '#58C452', accent2: '#DCE8B0', bg: '#081208', panel: '#0E1A0E',
    fontHeading: 'Gotu', fontBody: 'Sarala',
    captionVariant: 'minimal', lowerThirdVariant: 'underline',
    gradeOverlay:
      'radial-gradient(ellipse at 50% 90%, rgba(88,196,82,0.07) 0%, rgba(8,18,8,0.34) 100%)',
    visualFilter: 'saturate(1.16) contrast(1.03) brightness(0.98)',
    transitionBias: 'fades', texture: 'halation',
    layout: {captionAlign: 'center', captionY: 0.8, lowerThird: 'tr',
      overlayAnchor: 'center', watermark: 'br', progress: 'none'},
    motion: {entry: 'rise', spring: 'calm', kenBurns: 0.75},
  },
  dune: {
    name: 'dune', // deserts, heat, extreme geography
    accent: '#E8A34C', accent2: '#D9C7A8', bg: '#170F07', panel: '#20160C',
    fontHeading: 'Khand', fontBody: 'Karma',
    captionVariant: 'outline', lowerThirdVariant: 'bar',
    gradeOverlay:
      'linear-gradient(180deg, rgba(232,163,76,0.10) 0%, rgba(23,15,7,0.32) 100%)',
    visualFilter: 'saturate(1.10) contrast(1.09) sepia(0.12)',
    transitionBias: 'slides', texture: 'grain',
    layout: {captionAlign: 'right', captionY: 0.76, lowerThird: 'bl',
      overlayAnchor: 'right', watermark: 'bl', progress: 'top'},
    motion: {entry: 'rise', spring: 'settle', kenBurns: 0.9},
  },
  ember: {
    name: 'ember', // volcanoes, fire, disasters
    accent: '#FF5A2D', accent2: '#FFC85C', bg: '#120705', panel: '#1C0C08',
    fontHeading: 'Teko', fontBody: 'PragatiNarrow',
    captionVariant: 'duotone', lowerThirdVariant: 'bar',
    gradeOverlay:
      'radial-gradient(ellipse at 50% 100%, rgba(255,90,45,0.12) 0%, rgba(18,7,5,0.40) 100%)',
    visualFilter: 'saturate(1.22) contrast(1.14) brightness(0.94)',
    transitionBias: 'punches', texture: 'grain',
    layout: {captionAlign: 'center', captionY: 0.72, lowerThird: 'tl',
      overlayAnchor: 'center', watermark: 'tl', progress: 'bottom-thick'},
    motion: {entry: 'pop', spring: 'snappy', kenBurns: 1.45},
  },

  // ── Science / body / how-things-work ─────────────────────────────────
  medical: {
    name: 'medical', // human body, brain, health science
    accent: '#35C4C8', accent2: '#FF6E6E', bg: '#071016', panel: '#0C1820',
    fontHeading: 'PalanquinDark', fontBody: 'Palanquin',
    captionVariant: 'boxed', lowerThirdVariant: 'underline',
    gradeOverlay:
      'linear-gradient(180deg, rgba(53,196,200,0.06) 0%, rgba(7,16,22,0.30) 100%)',
    visualFilter: 'saturate(0.96) contrast(1.08) brightness(0.99)',
    transitionBias: 'fades', texture: 'none',
    layout: {captionAlign: 'left', captionY: 0.74, lowerThird: 'tr',
      overlayAnchor: 'left', watermark: 'tr', progress: 'top'},
    motion: {entry: 'rise', spring: 'settle', kenBurns: 0.8},
  },
  laboratory: {
    name: 'laboratory', // experiments, scientific method, discoveries
    accent: '#4DA3FF', accent2: '#7FE08A', bg: '#0D1218', panel: '#131A22',
    fontHeading: 'MartelSans', fontBody: 'MartelSans',
    captionVariant: 'ledger', lowerThirdVariant: 'underline',
    gradeOverlay:
      'linear-gradient(180deg, rgba(77,163,255,0.05) 0%, rgba(13,18,24,0.24) 100%)',
    visualFilter: 'saturate(0.94) contrast(1.06)',
    transitionBias: 'fades', texture: 'none',
    layout: {captionAlign: 'left', captionY: 0.76, lowerThird: 'tr',
      overlayAnchor: 'left', watermark: 'br', progress: 'none'},
    motion: {entry: 'fade', spring: 'calm', kenBurns: 0.7},
  },
  blueprint: {
    name: 'blueprint', // engineering, how machines/structures work
    accent: '#6FB7FF', accent2: '#FFFFFF', bg: '#071224', panel: '#0C1B33',
    fontHeading: 'Rajdhani', fontBody: 'PragatiNarrow',
    captionVariant: 'boxed', lowerThirdVariant: 'underline',
    gradeOverlay:
      'linear-gradient(180deg, rgba(111,183,255,0.07) 0%, rgba(7,18,36,0.34) 100%)',
    visualFilter: 'saturate(0.90) contrast(1.10) hue-rotate(4deg)',
    transitionBias: 'wipes', texture: 'scanlines',
    layout: {captionAlign: 'left', captionY: 0.74, lowerThird: 'tl',
      overlayAnchor: 'left', watermark: 'tl', progress: 'top'},
    motion: {entry: 'rise', spring: 'settle', kenBurns: 0.8},
  },
  circuit: {
    name: 'circuit', // AI, computers, technology
    accent: '#3DFF8C', accent2: '#C8FFDE', bg: '#040A06', panel: '#08140C',
    fontHeading: 'AnekDevanagari', fontBody: 'AnekDevanagari',
    captionVariant: 'chip', lowerThirdVariant: 'underline',
    gradeOverlay:
      'linear-gradient(180deg, rgba(61,255,140,0.05) 0%, rgba(4,10,6,0.40) 100%)',
    visualFilter: 'saturate(0.96) contrast(1.14) brightness(0.95)',
    transitionBias: 'wipes', texture: 'scanlines', hud: true,
    layout: {captionAlign: 'left', captionY: 0.72, lowerThird: 'tr',
      overlayAnchor: 'left', watermark: 'tr', progress: 'top'},
    motion: {entry: 'slide', spring: 'snappy', kenBurns: 1.1},
  },

  // ── City / modern / dark ─────────────────────────────────────────────
  'neon-vice': {
    name: 'neon-vice', // night cities, future tech, nightlife economies
    accent: '#FF3D81', accent2: '#21D4FD', bg: '#0B0614', panel: '#140C22',
    fontHeading: 'Khand', fontBody: 'Poppins',
    captionVariant: 'glow', lowerThirdVariant: 'chip',
    gradeOverlay:
      'linear-gradient(160deg, rgba(255,61,129,0.09) 0%, rgba(33,212,253,0.06) 60%, rgba(11,6,20,0.36) 100%)',
    visualFilter: 'saturate(1.30) contrast(1.12) brightness(0.95)',
    transitionBias: 'whips', texture: 'halation',
    layout: {captionAlign: 'center', captionY: 0.74, lowerThird: 'tl',
      overlayAnchor: 'center', watermark: 'bl', progress: 'bottom-thick'},
    motion: {entry: 'slide', spring: 'snappy', kenBurns: 1.3},
  },
  metro: {
    name: 'metro', // cities, infrastructure, megaprojects
    accent: '#FF7A00', accent2: '#C8CDD4', bg: '#0D0F12', panel: '#14171B',
    fontHeading: 'Biryani', fontBody: 'PragatiNarrow',
    captionVariant: 'band', lowerThirdVariant: 'chip',
    gradeOverlay:
      'linear-gradient(180deg, rgba(200,205,212,0.05) 0%, rgba(13,15,18,0.34) 100%)',
    visualFilter: 'saturate(0.98) contrast(1.10)',
    transitionBias: 'slides', texture: 'none',
    layout: {captionAlign: 'right', captionY: 0.74, lowerThird: 'tl',
      overlayAnchor: 'right', watermark: 'tl', progress: 'bottom'},
    motion: {entry: 'slide', spring: 'snappy', kenBurns: 1.15},
  },
  rustbelt: {
    name: 'rustbelt', // industry, machines, abandoned places
    accent: '#D96C2C', accent2: '#A8B0B8', bg: '#100C0A', panel: '#181210',
    fontHeading: 'Teko', fontBody: 'Karma',
    captionVariant: 'boxed', lowerThirdVariant: 'bar',
    gradeOverlay:
      'linear-gradient(180deg, rgba(217,108,44,0.06) 0%, rgba(16,12,10,0.38) 100%)',
    visualFilter: 'saturate(0.88) contrast(1.14) sepia(0.10)',
    transitionBias: 'wipes', texture: 'grain',
    layout: {captionAlign: 'left', captionY: 0.78, lowerThird: 'bl',
      overlayAnchor: 'left', watermark: 'br', progress: 'bottom'},
    motion: {entry: 'fade', spring: 'settle', kenBurns: 0.9},
  },
  signal: {
    name: 'signal', // alerts, ongoing events, investigation urgency
    accent: '#FF2E4D', accent2: '#FFFFFF', bg: '#0E0508', panel: '#180A0F',
    fontHeading: 'Khand', fontBody: 'Hind',
    captionVariant: 'ribbon', lowerThirdVariant: 'chip',
    gradeOverlay:
      'linear-gradient(180deg, rgba(255,46,77,0.06) 0%, rgba(14,5,8,0.38) 100%)',
    visualFilter: 'saturate(1.10) contrast(1.16) brightness(0.94)',
    transitionBias: 'whips', texture: 'scanlines',
    layout: {captionAlign: 'left', captionY: 0.7, lowerThird: 'tl',
      overlayAnchor: 'left', watermark: 'tl', progress: 'bottom-thick'},
    motion: {entry: 'slide', spring: 'snappy', kenBurns: 1.35},
  },
};

export const getStyle = (name?: string): StylePack =>
  STYLE_PACKS[name ?? ''] ?? STYLE_PACKS.documentary;
