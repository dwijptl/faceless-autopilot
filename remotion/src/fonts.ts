/** Per-pack Google-font loading.
 *
 * Every family registered here ships Devanagari glyphs (verified against
 * @remotion/google-fonts), so any pack's caption/heading font renders Hindi
 * natively instead of falling back mid-word. Fonts load lazily: a render
 * only fetches the two families its style pack asks for.
 *
 * Devanagari safety rules (learned the hard way — see learnings.md):
 * never negative letterSpacing, never per-letter animation (breaks
 * conjuncts/matras), lineHeight >= 1.2 for stacked matras.
 */

type FontModule = {
  loadFont: () => {fontFamily: string};
  getInfo: () => {fontFamily: string};
};

// Static requires so the bundler sees literal module paths.
const LOADERS: Record<string, () => FontModule> = {
  AnekDevanagari: () => require('@remotion/google-fonts/AnekDevanagari'),
  Amita: () => require('@remotion/google-fonts/Amita'),
  Baloo2: () => require('@remotion/google-fonts/Baloo2'),
  Biryani: () => require('@remotion/google-fonts/Biryani'),
  Eczar: () => require('@remotion/google-fonts/Eczar'),
  Gotu: () => require('@remotion/google-fonts/Gotu'),
  Halant: () => require('@remotion/google-fonts/Halant'),
  Hind: () => require('@remotion/google-fonts/Hind'),
  Inter: () => require('@remotion/google-fonts/Inter'),
  Kalam: () => require('@remotion/google-fonts/Kalam'),
  Karma: () => require('@remotion/google-fonts/Karma'),
  Khand: () => require('@remotion/google-fonts/Khand'),
  Laila: () => require('@remotion/google-fonts/Laila'),
  Martel: () => require('@remotion/google-fonts/Martel'),
  MartelSans: () => require('@remotion/google-fonts/MartelSans'),
  Mukta: () => require('@remotion/google-fonts/Mukta'),
  NotoSansDevanagari: () => require('@remotion/google-fonts/NotoSansDevanagari'),
  NotoSerifDevanagari: () => require('@remotion/google-fonts/NotoSerifDevanagari'),
  Palanquin: () => require('@remotion/google-fonts/Palanquin'),
  PalanquinDark: () => require('@remotion/google-fonts/PalanquinDark'),
  Poppins: () => require('@remotion/google-fonts/Poppins'),
  PragatiNarrow: () => require('@remotion/google-fonts/PragatiNarrow'),
  Rajdhani: () => require('@remotion/google-fonts/Rajdhani'),
  RozhaOne: () => require('@remotion/google-fonts/RozhaOne'),
  Sarala: () => require('@remotion/google-fonts/Sarala'),
  Teko: () => require('@remotion/google-fonts/Teko'),
  TiroDevanagariHindi: () => require('@remotion/google-fonts/TiroDevanagariHindi'),
  YatraOne: () => require('@remotion/google-fonts/YatraOne'),
};

export const FONT_MODULES = Object.keys(LOADERS);

const TAIL =
  '"Noto Sans Devanagari", -apple-system, "DejaVu Sans", sans-serif';

const cache = new Map<string, string>();

// Offline mode (REMOTION_DISABLE_REMOTE_FONTS=1): skip the Google Fonts
// network fetch and rely on system-installed families of the same name —
// keeps Studio/preview renders working without egress.
const OFFLINE =
  typeof process !== 'undefined' &&
  Boolean(process.env?.REMOTION_DISABLE_REMOTE_FONTS);

const resolveFamily = (moduleName?: string): string => {
  if (!moduleName) return '';
  const hit = cache.get(moduleName);
  if (hit !== undefined) return hit;
  let family = '';
  try {
    const loader = LOADERS[moduleName];
    if (loader) {
      const mod = loader();
      family = `"${OFFLINE ? mod.getInfo().fontFamily : mod.loadFont().fontFamily}"`;
    }
  } catch {
    family = ''; // offline/studio without network: system fallback below
  }
  cache.set(moduleName, family);
  return family;
};

/** Full CSS font stack for a registered family (Devanagari-safe tail). */
export const stackFor = (moduleName?: string): string => {
  // Always try to have Noto Sans Devanagari registered as the glyph net.
  resolveFamily('NotoSansDevanagari');
  const fam = resolveFamily(moduleName);
  return fam ? `${fam}, ${TAIL}` : TAIL;
};
