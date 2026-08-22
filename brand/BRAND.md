# सुरागनामा · Suraagnama — Brand Kit

**Identity:** a compass star inside a deliberately broken ring — the gap is
the clue the file is still missing. Deep navy archive, amber evidence.

**The name:** सुराग (*clue*) + -नामा, the Indo-Persian suffix for a written
record — रोज़नामा, बयाननामा, इक़रारनामा. "The record of clues": a case file in
one Indian word, in a documentary register rather than a horror one. Handle
`@suraagnama` (verified free 2026-08-22 — availability was checked by fetching
the handle directly; web search does NOT surface small channels and returns
clean for names that are already taken).

**Never brand on the bare word सुराग.** It belongs to SAB Network's *Suraag
Special* and Doordarshan's *Suraag – The Clue*. The full token is what's
distinct, and it's what the channel owns.

## Promise

**असली केस। असली सबूत। बिना जवाब के सवाल।**
Banner line: **हर फ़ाइल में एक सवाल बाकी है।**
Closing line: **फ़ाइल बंद हो गई — सुराग अब भी बाकी है।**

The channel name never opens an episode. The cold-open contract
(docs/CASE_FILE_PIVOT.md) puts the impossible human moment first; names,
places and dates only after the viewer cares. Branding lives on the outro.

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
4-second outro end card ("नई फ़ाइल — सोम · गुरु") · branded
thumbnail template. Visual style packs rotate per video (documentary →
kinetic → editorial → noir) but all draw from this palette, so the channel
stays recognizable. Tokens live in `remotion/src/styles.ts` — keep hex values
in sync with this file.
