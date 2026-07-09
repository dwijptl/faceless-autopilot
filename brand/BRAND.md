# Terra Incognita — Brand Kit

**Identity:** a compass star inside a deliberately broken ring — the gap is
the *unknown* the channel explores. Deep navy space, amber discovery.

## Palette

| Token | Hex | Use |
|---|---|---|
| Navy | `#0A1428` | Backgrounds, outro, thumbnail base |
| Panel | `#132441` | Cards, gradients |
| Amber | `#FFB020` | Primary accent: captions, lower thirds, progress bar, thumbnail titles |
| Amber soft | `#FFC85C` | Secondary warm accent (editorial style) |
| Sky | `#4DA3FF` | Cool counterpoint accent |
| Text | `#F4F7FB` | All body/display text |

## Typography

**Inter** everywhere in video (loaded via `@remotion/google-fonts`):
titles/kinetic 900 uppercase tight-tracked; lower thirds 700 uppercase
wide-tracked; captions 600–800 by style pack. Static assets use DejaVu Sans
Bold (metrically close, available in CI).

## Files (regenerate anytime: `python brand/generate_brand.py`)

| File | Size | Upload to |
|---|---|---|
| `banner.png` | 2560×1440 | YouTube → Customization → Branding → Banner image |
| `avatar.png` | 800×800 | Branding → Picture |
| `yt_watermark.png` | 300×300 | Branding → Video watermark |
| `logo.png` / `logo_mark.png` | wordmark / 1024 icon | anywhere you need the logo |
| `watermark.png` | 600, white alpha | used automatically in-video (corner, ~8% opacity) |

## In-video branding (automatic, every render)

Corner watermark · amber progress bar · branded lower thirds & captions ·
4-second outro end card ("New expeditions Mon · Wed · Fri") · branded
thumbnail template. Visual style packs rotate per video (documentary →
kinetic → editorial → noir) but all draw from this palette, so the channel
stays recognizable. Tokens live in `remotion/src/styles.ts` — keep hex values
in sync with this file.
