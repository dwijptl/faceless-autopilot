/** One restrained presentation for full-frame documentary media. */

export const BRAND = {
  navy: '#0A1428',
  amber: '#FFB020',
  text: '#F4F7FB',
};

export type StylePack = {
  name: 'documentary';
  accent: string;
  bg: string;
  fontHeading: string;
  fontBody: string;
  gradeOverlay: string;
  visualFilter: string;
  motion: {kenBurns: number};
};

const DOCUMENTARY: StylePack = {
  name: 'documentary',
  accent: BRAND.amber,
  bg: '#000000',
  fontHeading: 'Mukta',
  fontBody: 'Mukta',
  gradeOverlay:
    'linear-gradient(180deg, rgba(0,0,0,0.02) 0%, rgba(0,0,0,0.10) 100%)',
  visualFilter: 'saturate(1.02) contrast(1.02)',
  motion: {kenBurns: 0.8},
};

export const getStyle = (_name?: string): StylePack => DOCUMENTARY;
