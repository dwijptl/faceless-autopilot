# Liquid Atlas — premium visual system for long-form + Shorts

> Companion to `docs/motion-library-v2.md`. That doc is the **component catalog**
> (families + variants). This doc is the **visual system + per-format plan**: the
> glass/"liquid atlas" direction, new ideas beyond the external brainstorm, and
> exactly how a *fully automated* pipeline builds both a 6-minute video and a
> Short from it. Status: **planned, not built.** Saved to continue later.

---

## 0. TL;DR

- The external "Living/Liquid Atlas" brainstorm is good, but it's written for a
  **human editor** choosing artful shots. This channel has **no editor** — the
  pipeline is `script_gen → motion.py → Remotion render` on GitHub Actions. So
  the real work is not "list effects," it's **make each effect selectable and
  placeable from script metadata, deterministically.** That reframe drives
  everything below.
- **Direction:** keep it 60–70% footage/maps, ~15% data/diagrams, ~10% type,
  ~5–10% glass. Glass organizes information; it never replaces the story.
- **One free technical unlock:** real optical glass refraction (`feDisplacementMap`)
  only works in Chromium on the web — and **Remotion renders in headless
  Chromium**, so we can ship true "liquid glass" that a normal website couldn't.
- **One decision you must make:** brand palette — stay amber/navy "Terra
  Incognita," or move to cyan/teal per-topic "Liquid Atlas." (See §2.)

---

## 1. Reality check — this is an automated pipeline

Everything the external plan calls "choose one hero effect per video," "add a
hand-drawn annotation here," "match-cut a bubble to Earth" assumes a person at a
timeline. Our constraints instead:

| Constraint | Consequence for the plan |
|---|---|
| No human editor | Every effect must be triggered by **script/scene metadata** + a **deterministic selector** (extends `pipeline/motion.py`). |
| Assets are Pexels stock + Gemini/FLUX stills + synth SFX | No bespoke footage. Premium comes from **treatment** (glass, maps, type, grade, sound), not new clips. Zero added cost. |
| Renders headless in Remotion/Chromium | We **can** use Chromium-only CSS/SVG (backdrop `feDisplacementMap`, `mask-image`, relative color) that production web avoids. Render-time GPU cost only, not playback. |
| Hindi/Devanagari | Every text component must keep `letterSpacing: 0` + roomy `lineHeight` (already a documented rule in `elements.tsx`). Bake into tokens. |
| 3×/week long + Shorts on alternate days | Selection must guarantee **variety across uploads** (seed off ISO week), or YouTube's "templated/inauthentic" signal bites. |

**Design principle that falls out of this:** the library is a set of
**data-driven components**, and the intelligence lives in (a) `script_gen`
emitting richer per-scene metadata and (b) `motion.py` turning that metadata into
a concrete, varied, non-repeating recipe. Build the components once; let the
metadata make every video look hand-made.

---

## 2. The one brand decision

The existing brand (`remotion/src/styles.ts`) is **amber (#FFB020) on navy
(#0A1428)**, "Terra Incognita," with 4 rotating style packs. The external plan
proposes **cyan/teal/violet "Liquid Atlas"** with per-topic accent switching.
These conflict. Three options:

- **A — Keep amber as anchor, add restrained per-topic accent (recommended).**
  Amber stays the channel signature (watermark, outro, CTA). Add a `theme`
  per video (ocean→cyan, underground→teal, space→violet, history→amber, danger→red)
  that tints **glass, glow, and map lines only** — not the whole grade. Best of
  both: recognizable + topic-appropriate. Implement as an extra field on
  `StylePack`/manifest, defaulting to amber.
- **B — Full Liquid Atlas repalette.** Switch the brand to cyan/teal. More
  "premium tech doc," but throws away existing brand equity and the amber outro.
- **C — Status quo.** Amber everywhere. Simplest, but the external plan's
  topic-mood color arc is lost.

**Recommendation: A.** It's a small addition to the existing `StylePack` system
and keeps the channel identity while unlocking the mood arc. Everything below
assumes A (amber-anchored, per-topic accent tint).

Also decide the **channel name/label**: "Terra Incognita" (current) vs "Liquid
Atlas" (external). You can keep Terra Incognita as the name and use "LIQUID
ATLAS · FILE 001"-style episode tags as a motif — no conflict.

---

## 3. The glass system (concrete Remotion build)

This is the heart of your request. Build one primitive and derive the rest.

### 3.1 `GlassSurface` primitive — the shared chrome
A single component every glass element wraps. Props: `tint` (from theme/scene),
`blur`, `radius`, `glow?`, `refraction?`. Layers, back to front:
1. **Backdrop blur** 18–28px (`backdrop-filter: blur()`), background opacity 12–18%.
2. **Optional real refraction** — an SVG `feDisplacementMap` backdrop filter
   modeling a squircle dome (Snell's law, IOR ~1.5); x-displacement in red,
   y in green, neutral 128,128 = flat. **Only enable on hero moments** (it's
   GPU-heavy and can look slightly pixelated — soften with a small blur). Safe
   because we render in Chromium.
3. **1px hairline border**, low-opacity, slightly brighter on the **top edge**
   (specular highlight) — the single detail that reads "expensive."
4. **Soft drop shadow** beneath for elevation (Material-style: shadow explains
   depth, not decoration).
5. **Inner content** (number/label/etc.), and an **optional slow sheen** — a
   thin gradient band that drifts across once on entrance.
6. **GlowPoint** — glow lives on the *active number/point/edge only*, max 2 per
   screen, and fades out when the info goes inactive.

Tokens (add to `motion-tokens.ts`): `GLASS.opacity`, `GLASS.blur`,
`GLASS.borderTop`, `GLASS.radiusLg=20`, `GLASS.radiusSm=12`, `GLASS.shadow`,
`GLOW(accent)`.

### 3.2 Glass variants (these extend `EditorialCard`/`AnimatedStatCard`)
- `glass-fact` — compact panel: kicker + number + label. The workhorse.
- `glass-metric` — big number + delta/▲▼ + unit, tiny sparkline.
- `glass-location` — place name + coordinates, attaches to a map pin.
- `glass-chapter` — full-width chapter title fragment.
- `glass-fragment` ★ — irregular angled "shard" for surprises only (asymmetry
  creates hierarchy; don't use for normal info).
- `glass-conclusion` ★ — the final-answer panel, refraction on.

### 3.3 `LiquidLens` ★★ (signature)
A moving circular/organic glass lens that reveals a *different* treatment of the
footage underneath (magnified, thermal, wireframe, or data-annotated). Built as
a masked duplicate of the background layer with the displacement filter inside
the mask. This is the channel's "you are discovering something hidden" signature.
Automatable: fires on scenes tagged `visual_mode: lens` with a `reveal` payload.

---

## 4. More unique ideas (beyond the external list)

Marked **NEW** = not in the pasted brainstorm. All buildable in Remotion with
SVG/CSS/masks + synth SFX, zero new footage.

**Glass / light**
- **NEW — Caustic shimmer:** animated SVG turbulence as faint moving caustics on
  ocean/ice glass panels (reuses the existing grain turbulence trick).
- **NEW — Chromatic rim:** 1px chromatic-aberration split on the glass edge for
  hero panels only (RGB offset). Cheap, very "optical."
- **NEW — Frosted focus:** blur the whole frame except a sharp squircle "window"
  around the subject — a glass-framed spotlight without moving the camera.
- **NEW — Condensation/ink bleed reveal:** numbers/labels "wet-bleed" in via a
  mask instead of fading — reads tactile, not templated.

**Maps / geography (extends existing `Map.tsx`)**
- **NEW — Sonar ping rings:** concentric rings emanating from a map point on the
  "map ping" SFX; great for "discovered here."
- **NEW — Bathymetric ramp:** ocean-depth color ramp fills in under a coastline.
- **NEW — Terminator sweep:** day/night line sweeps a globe for time/scale beats.
- **NEW — Advection flow field:** animated streamlines for currents/wind (SVG
  paths with dash-offset motion) — the "living map" made physical.
- **NEW — Route odometer:** distance number counts up *along* the traced route.

**Data as physical object**
- **NEW — Depth ruler:** a measurement scale pinned to the screen edge that the
  camera "descends," number climbing — for caves/oceans/underground.
- **NEW — Draining column:** salinity/level shown as liquid draining from a glass
  cylinder (the external plan hinted; here it's a concrete component).
- **NEW — Strata stack:** cross-section layers separate in 2.5D ("exploded" geology).
- **NEW — Scale-stack:** "X Burj Khalifas / X times the Ganga" as stacked
  culturally-relevant silhouettes (Hindi-audience anchored).

**Documentary / evidence**
- **NEW — Redacted→revealed:** a blacked-out word wipes away to reveal the answer
  — perfect for mystery/"disputed" beats.
- **NEW — Confidence tag:** a small `पुष्टि / अनुमान / विवादित / अज्ञात` chip on
  claims (credibility signal + anti-AI; drives real trust).
- **NEW — Specimen isolate:** darken surround + faint observation ring + 2 callout
  lines around one object (museum, not weapon-HUD).
- **NEW — Single sharp among blurred:** one real photo snaps into focus in a field
  of blurred ones — an "evidence found" beat.

**Type / transition**
- **NEW — Word-as-landscape:** "गायब" dissolves into fog, "6,000 KM" stretches
  along a river path, "शून्य" collapses to a point (semantic type, ≤2/Short, ≤6/long).
- **NEW — Match-morph transitions (automatable):** bubble→Earth, island-outline→
  map-outline, radar-circle→hurricane. Precompute a small set of shape pairs the
  selector can trigger between compatible scene tags.
- **NEW — Iris/vault open:** aperture/vault-door reveal for chapter or big reveal.

---

## 5. Unified component catalog (one library)

Merge of `motion-library-v2.md` + glass + living-map + evidence. Grouped by
family; each is a **data-driven component** with a `variant` string, so it plugs
into `MOTION_CATALOG` (tsx) + the tuples in `motion.py` and auto-appears in the
render gallery.

| Family | Components / variants |
|---|---|
| **Glass** (new) | glass-fact, glass-metric, glass-location, glass-chapter, glass-fragment★, glass-conclusion★, LiquidLens★★ |
| **Stat/data** | glass-metric, trend, donut, delta, bars-race★, gauge, spark, draining-column, depth-ruler, scale-stack + existing 6 |
| **Kinetic type** | word-pop, mask-line★, highlight-swipe★, rolodex★, redacted-reveal, word-as-landscape★, type-on + existing |
| **Editorial/evidence** | glass-fact, myth-fact★, checklist, compare-table★, confidence-tag, source, specimen-isolate★, chapter + existing |
| **Maps** (extend `Map.tsx`) | route-trace, sonar-ping, bathymetric, terminator, flow-field, route-odometer, contour-field, cross-section, satellite→micro zoom |
| **Frames/atmosphere** | coords-HUD★, compass, frosted-focus, dust/particles (topic-tied), duotone, letterbox-tc, light-sweep + existing |
| **Transitions** (new) | match-morph★★, iris/vault, whip, light-streak, shape-wipe, dip-to-black, glitch-cut (tech only) |
| **Hero/brand** | cold-open★, map-reveal★★, big-reveal★, chapter-hero★, logo-sting, mystery-glyph (recurring), end-screen |

★ signature · ★★ top signature.

---

## 6. Long-form (6-minute) plan

The pipeline already splits a script into scenes with `visual_mode`. Extend the
mode set to: `broll | map | kinetic | stat | card | glass | lens | evidence |
cutaway | scale | timeline | bento | hero`. `script_gen` tags each beat; the
selector fills variant + accent + sfx. Beat structure (each row = what fires):

| Time | Beat | Primary visual_mode | Support | Sound |
|---|---|---|---|---|
| 0:00–0:08 | Cold open (biggest claim) | hero:cold-open over dark broll | 1 glass-metric, glow | deep hit |
| 0:08–0:25 | Promise (3 visual clues) | broll + 3 quick glass-fact | mystery-glyph | soft pulse ×3 |
| 0:25–0:35 | Title sequence (<10s) | hero:map-reveal | glass-chapter "FILE 0XX" | riser + map ping |
| 0:35–1:20 | Context | broll + map:route-trace | glass-location, editorial caps | ambience |
| 1:20–2:10 | Mechanism (most informative) | cutaway (strata-stack) | depth-ruler, flow-field, labels | rumble, ui-blips |
| 2:10–3:00 | Case study (one place) | map satellite→micro | evidence: coords, timeline, source | map ping, click |
| 3:00–3:50 | Escalation/implications | broll, darker grade | bars-race★ or scale-stack | tension rise |
| 3:50–4:40 | Uncertainty (credibility) | evidence mode | confidence-tag, redacted-reveal★ | paper, restrained |
| 4:40–5:25 | Synthesis | bento (3 facts) | recurring motifs return | layered |
| 5:25–5:50 | Final reveal | hero:big-reveal + glass-conclusion★ (refraction on) | minimal else | conclusion impact |
| 5:50–6:00 | Next curiosity | broll + glass-fragment teaser | end-screen (2 slots) | swell out |

**Rhythm rule (automatable):** never place 2 complex info scenes back-to-back —
`motion.py` alternates rich / simple / info / breath. **Motif recall:** the
selector reuses one earlier component in synthesis for cohesion.

---

## 7. Shorts plan (25–40s, 1080×1920)

Grounded in `ShortMain.tsx` (fast slides/fades, `captionY≈0.62`, no outro).
Constraints: captions **+50–80% larger**, visual change on every idea (not every
second), vertical safe area (keep out of the bottom ~14% UI zone), and a loop.

| Time | Beat | visual_mode | Notes |
|---|---|---|---|
| 0:00–0:02 | Visual shock (consequence first) | broll + glass-metric "3.5%→0%" | no logo/intro; 1 low hit |
| 0:02–0:06 | Question | kinetic:word-pop / mask-line + subtle lens | one highlighted keyword |
| 0:06–0:13 | First consequence | broll + one label + one diagram | big editorial captions, no box |
| 0:13–0:20 | Mechanism (real understanding) | cutaway or before/after | animated number |
| 0:20–0:28 | Escalation (global) | map flow-field, darker grade | rising sound |
| 0:28–0:34 | Conclusion (one line) | full-frame broll + big type | strong impact, no card |
| 0:34–0:37 | Loop | match-morph back to opening image | trail sound into first frame |

**Per-Short budget (automatable):** 1 hero device + 2 supporting, ≤2 semantic-type
moments, 3–5 SFX, 6–8 caption phrases, 1 accent, 1 music bed. The selector enforces
this so Shorts never overload.

---

## 8. The automation layer (the part the external plan is missing)

This is what makes all of §3–7 actually run without an editor.

**8.1 `script_gen.py` emits richer per-scene metadata.** Extend the LLM scene
schema with: `visual_mode` (expanded set), `theme` (ocean/underground/space/
history/danger → accent), `importance` (normal/key/reveal), `data` (value, unit,
baseline, bars, coords, route), `semantic_word` (optional), `sfx_cue`, and a
video-level `recipe_seed`. Prompt the model to mark exactly one cold-open, one
big-reveal, 5–8 semantic-type beats (long) / ≤2 (short), and confidence tags on
any disputed claim.

**8.2 `motion.py` becomes a recipe engine (extends `decorate_scenes`).**
- Pick **1 hero device + 2 supporting** per video from the `theme` (a
  theme→device table), seeded by title+ISO week so consecutive uploads differ.
- Choose each component's **variant by data shape** (has `bars`→bars-race/donut;
  `baseline`→delta/compare; single value→horizon/big-reveal; `coords`→map+glass-location).
- Enforce the **variation matrix** and **no-repeat / no-two-complex-in-a-row**
  rules; attach `accent` from theme (amber fallback).

**8.3 `sfx.py` maps `sfx_cue`→synth** (already 18 sounds; add swell, thud, flip,
draw, ui-blip, sonar). One cue per key beat; never a whoosh on every cut.

**8.4 Manifest + `Root.tsx`** gain the new fields (`theme`, `data`, `cta`/`hero`/
`bumper`, per-scene `sfx`). `Main.tsx`/`ShortMain.tsx` render the mode→component
map. `MotionGallery` auto-covers every variant for CI.

---

## 9. Systems (reconciled with existing tokens)

**Colour** — amber anchor + per-theme accent (§2). Glow only on active number/
point/edge, ≤2 on screen, disappears when inactive. No saturated neon; danger =
restrained red, recovery = green, else white text on navy-glass.

**Typography** — max 2 Devanagari families: a clean sans (captions/body) + an
editorial display (titles/numbers/chapters). 3 caption levels: normal (no box),
important (accent keyword, slight scale), reveal (large, integrated, sound cue).
Always `letterSpacing:0`, roomy `lineHeight`, ≤2 lines, 3–7 words, safe margins.

**Motion presets** (in `motion-tokens.ts`): `soft` (opacity+translate, gentle
spring — captions/labels), `discovery` (blur→sharp + mask + glow pulse — evidence),
`impact` (fast scale + short motion-blur + bass, hard stop — reveals only),
`geographic` (smooth camera interp + path trace + parallax — maps). Enter 10–16f
glass / 6–10f caption; exit faster than enter; ≤2 animated properties at once.

**Sound** — 5 signature cues (discovery pulse, map ping, evidence click, deep
rise, conclusion impact) + topic ambience beds. Glass sounds clean; annotation/
archival sounds physical (paper, pencil, projector). Contrast = the identity.

---

## 10. Anti-generic ruleset (automatable checks)

Every long video must include ≥1 custom map, ≥1 diagram, ≥1 culturally-relevant
scale comparison, ≥1 specific measurement, ≥1 confidence tag, ≥1 topic-tied
transition, ≥1 breath/negative-space beat. Every element must **explain, prove,
escalate, or set atmosphere** — else the selector drops it. Hard bans: identical
caption animation every line, every fact in a card, generic blue-purple gradient
wash, particles everywhere, whoosh on every cut, repeated assets across nearby
uploads, robotic equal-emphasis narration timing.

**Per-video variation matrix** (selector output, logged for audit): 1 hero · 2
support · 1 texture family · 1 accent · 1 signature transition · 1 custom diagram
· 1 topic SFX. Two videos should never share the same row.

---

## 11. Cost reality

Still **$0 incremental**. Glass, maps, lens, cutaways, evidence, type, particles,
transitions = SVG/CSS/masks rendered in Chromium + synth SFX. One 4K stock clip
yields many shots (wide/close/push-in/blur-bg/masked-in-map/mono-evidence/
freeze-annotated). No AI-generated video. Render time rises modestly (refraction
is GPU-heavy) — gate `feDisplacementMap` to hero moments only.

---

## 12. Build roadmap (both formats)

**Phase 0 — Foundation** (from v2): `motion-tokens.ts` incl. `GLASS`/`GLOW`,
motion presets, Devanagari-safe `text()`; refactor existing components onto it;
catalog-sync test. Add `theme`→accent to `StylePack`.

**Phase 1 — Level 1 / highest ROI** (ship into scheduled videos immediately):
editorial 3-level captions, `GlassSurface` + glass-fact/metric/location/chapter,
map route-trace + location pin + sonar-ping, number/big-reveal, film grain,
5 signature SFX cues, conclusion frame, Shorts loop ending.

**Phase 2 — Signature identity:** LiquidLens★★, cutaway/strata + depth-ruler,
evidence mode (coords/source/confidence/redacted), before/after, contour/flow
fields, match-morph transitions, `script_gen` metadata + `motion.py` recipe engine.

**Phase 3 — Advanced:** satellite→micro zoom, depth parallax stacks, caustics/
chromatic rim, audio-reactive micro-elements, per-topic particle systems,
word-as-landscape semantic type, refraction on hero glass.

Then **freeze and produce**: ship several videos on the frozen system, measure
retention, keep only what earns its place.

---

## 13. Open decisions for you

1. **Palette (§2):** A (amber anchor + per-topic accent, recommended) / B (full
   Liquid Atlas cyan) / C (amber only)?
2. **Channel label:** keep "Terra Incognita" name with "LIQUID ATLAS · FILE" episode
   tags, or rebrand?
3. **Glass aggressiveness:** conservative (fact cards + location + conclusion only)
   or full (add LiquidLens + refraction heroes early)?
4. **Where to start:** I'd build Phase 1 first — it's the biggest visible jump and
   drops straight into the next scheduled render.

---

## Sources (external references incorporated)
- Liquid glass refraction via SVG `feDisplacementMap`, Chromium-only on web —
  kube.io, LogRocket, w3c/svgwg #1142 (we exploit this because Remotion renders in Chromium).
- Glassmorphism 2026 / volumetric depth, multi-layer backdrop filters, relative
  color, mask-image — timgraf.com, weblogtrips.com, setproduct.com.
- Motion-graphics 2026 trends (bold type, texture/imperfection, vertical-first) —
  sonduckfilm.com, criticatv.com.
- Apple Liquid Glass (translucency/refraction), Google Material 3 Expressive
  (spring motion, depth, elevation), kinetic-typography and data-video-transition
  practice — as cited in the prior brainstorm.
