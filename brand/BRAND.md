# सुरागनामा · Suraagnama — Brand Kit

**Identity:** an open case-file folder cut by an `S`-shaped trail, with an
amber evidence line entering the file. Deep navy archive, white paper, amber
clue. The mark reads as investigation—not paranormal horror—even at 40 px.

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

**असली केस · असली सबूत · अनसुलझे सवाल**
Banner line: **असली केस · असली सबूत · अनसुलझे सवाल**
Closing line: **फ़ाइल अभी बंद नहीं हुई।**

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

## Channel metadata

Paste `channel_description.txt` into YouTube Studio → Customization → Profile.
Every generated video description begins with the same real-case cluster and
ends with the `@suraagnama` subscribe CTA; production metadata must never fall
back to the abandoned space/science tag set.

## Files (regenerate anytime: `python brand/generate_brand.py`)

| File | Size | Upload to |
|---|---|---|
| `banner.png` | 2560×1440 | YouTube → Customization → Branding → Banner image |
| `avatar.png` | 800×800 | Branding → Picture |
| `yt_watermark.png` | 150×150 | Branding → Video watermark |
| `logo.png` / `logo_mark.png` | wordmark / 1024 icon | anywhere you need the logo |
| `watermark.png` | 600×600, transparent corners | used automatically in-video (corner) |
| `source-avatar.png` / `source-banner.png` | approved masters | inputs for deterministic regeneration |

## In-video branding (automatic, every render)

Corner watermark · amber progress bar · branded lower thirds & captions ·
long-form outro with **SURAAGNAMA** and the closing line · a compact
**SURAAGNAMA** signature on the last beat of every Short · branded thumbnail
template. The MoviePy emergency renderer carries the same corner mark and
outro. Visual style packs rotate per video (documentary →
kinetic → editorial → noir) but all draw from this palette, so the channel
stays recognizable. Tokens live in `remotion/src/styles.ts` — keep hex values
in sync with this file.
