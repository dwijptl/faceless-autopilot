# Motion and sound library

The pipeline includes a zero-license-cost visual and sound-design library made
entirely from Remotion, React, SVG and synthesized WAV files. It does not fetch
template packs, icons or sound effects from third-party marketplaces.

## What is included

| Family | Variants | Use |
|---|---:|---|
| Animated stat cards | 6 | glass, split, radial, ticker, stamp, horizon |
| Kinetic titles | 6 | word-pop, wipe, stack, orbit, split, marker |
| Editorial cards | 5 | definition, quote, split, timeline, warning |
| Scene frames | 6 | corners, film, grid, scanner, focus, aperture |
| Lower thirds | 5 | rail, pill, underline, locator, index |
| Subscribe/bell CTAs | 4 | pill, stamp, minimal, orbit |

That is **32 reusable animated variants**. Every scene receives a deterministic
variant set based on the video title and style pack. A family cycles through
all its variants before repeating, so adjacent videos remain reproducible while
individual scenes do not keep showing the same card or frame.

The sound pack contains **18 synthesized cues**: three whooshes, riser, hit,
sub-hit, pop, tick, pulse, chime, bell, sparkle, glitch, beep, shutter,
page-turn, rumble and air. The pipeline maps them to scene purpose instead of
placing one generic whoosh everywhere. For example, stats receive count ticks,
maps receive a pulse, editorial cards receive pop/chime, and the CTA receives a
bell accent.

## Editorial card scripting

The script generator can now select `visual_mode: "card"` and fill:

```json
{
  "visual_mode": "card",
  "card": {
    "kicker": "FIELD NOTE",
    "headline": "यहाँ समय अलग चलता है",
    "body": "एक संक्षिप्त, स्पष्ट व्याख्या।"
  }
}
```

Long videos may use up to two editorial-card scenes; Shorts may use one. They
are intended for definitions, comparisons, warnings, quotations and timeline
beats that communicate faster than generic stock footage.

## CTA controls

`config.yaml` contains the `motion_library` controls. Disable the entire layer,
disable CTAs only, keep CTAs out of Shorts, or change the title, subtitle and
duration without touching code. The planner places one unobtrusive CTA after
the video has delivered value; it does not add spoken subscribe begging.

## Preview the complete catalog

From the `remotion` directory:

```bash
npm install
npm run gallery
```

This renders `motion-gallery.mp4`, a labeled reel containing all 32 variants.
The CI job also type-checks the components and renders representative stills
from every family. Each production run writes its chosen variants, CTA and
sound-event count into `run_summary.json` for review.
