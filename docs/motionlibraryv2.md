# Motion Library v2 — a reusable "house-style" system for million-sub, non-generic videos

> Brainstorm + phased build plan. Status: **planned, not yet built.** Captured so
> we can continue later. The current library (33 variants, wired end-to-end) is
> the foundation this extends — nothing here throws that away.

## Context

The channel (Terra Incognita, Hindi faceless-autopilot) already ships a real,
wired-up motion library — this is **not** a greenfield. Today:

- **`remotion/src/motion-library.tsx`** — 6 families / **33 variants**:
  `AnimatedStatCard` · `KineticTitle` · `EditorialCard` · `SceneFrame` ·
  `AnimatedLowerThird` · `SubscribeBell`(CTA), plus a `MotionGallery`
  composition that render-tests every variant in CI.
- **`pipeline/motion.py`** — `decorate_scenes()` deterministically assigns one
  variant per family to each scene (seeded by title, cycles so nothing repeats
  back-to-back); `plan_cta()` places one subscribe moment.
- **`pipeline/sfx.py`** — 18 synthesized SFX auto-paired to scene modes.
- **Wiring**: LLM `script_gen` picks `visual_mode` (broll|kinetic|stat|card|map)
  → `motion.py` decorates → `Root.tsx` `Manifest` → `Main.tsx`/`ShortMain.tsx`.

**Why this change:** to read as a "million-sub" channel rather than "generic AI
output," the library needs (1) far more variety so a viewer never sees the same
card twice in a video *or across a week*, (2) a small set of **signature "hero"
moments** that are recognizably *this* channel, and (3) a **locked design-token
+ timing system** so all of it feels drawn by one hand. This plan brainstorms
the full catalog, then sequences the build (foundation → families → hero → sound).

Scope chosen: **balanced** (breadth of variants + signature depth + consistency
system) and **list + phased build plan**.

---

## What actually separates "million-sub" from "generic AI" (design principles)

These are the rules every new element must obey. They double as an audit of
where the current library still risks looking templated.

1. **One motion grammar.** Every entrance uses the *same* spring vocabulary
   (a small set of named presets), the same enter/hold/exit rhythm, the same
   easing. Generic-AI look = every element animating slightly differently.
   → *Fix:* a `motion-tokens.ts` with `SPRING.snap/settle/drift`, `TIMING`,
   `EASE`, and a `useEnter()` hook. Refactor existing components onto it.
2. **A spacing + elevation scale, not magic numbers.** Current components use ad
   hoc `48*s`, `.90` opacities, bespoke shadows. Tokenize radius/space/shadow so
   every card shares proportions.
3. **Restraint + one focal point per beat.** Hero number OR headline, never a
   busy dashboard. Animate *in*, then hold still (let the viewer read).
4. **Deliberate imperfection = human.** Slight rotation on stamps, hand-drawn
   marker underline, off-grid tape — already hinted (`stamp`, `marker`); push it
   into a consistent "field-notes" motif.
5. **Signature repeatable motifs.** A coordinate/compass HUD, the amber accent
   sweep, a map-morph reveal — recurring so the channel is recognizable in 2s.
6. **Motion matched to meaning (semantic selection).** A comparison stat should
   pick the compare layout; a single big number the horizon layout. Today
   selection is purely cyclic → upgrade `decorate_scenes` to read the data
   shape.
7. **Devanagari-safe by construction.** `letterSpacing: 0`, roomy `lineHeight`,
   no negative tracking on Hindi runs — already a documented constraint in
   `elements.tsx`; bake it into the tokens/hook so new variants can't regress.
8. **Sound is not optional.** Every visual beat gets a paired SFX; silence on a
   stat pop is the fastest "AI slideshow" tell.

---

## The reuse contract (how any new element becomes library, not a one-off)

Every item below ships through the **same 5-step pattern** — this is what makes
it a library instead of scattered components:

1. Add the variant string to `MOTION_CATALOG` in `motion-library.tsx` **and** the
   matching tuple in `pipeline/motion.py` (kept in sync by a test — see below).
2. Implement the variant as a branch in its family component, built **only** from
   `motion-tokens.ts` primitives (no new magic numbers).
3. It then **auto-appears** in `MotionGallery` (CI render-tests it) and is
   **auto-assigned** by `decorate_scenes()` — zero extra wiring.
4. Pair it with an SFX in `sfx.py plan_events()`.
5. Add/extend a golden sample in the gallery's `galleryStat`-style fixtures so
   the render exercises real data.

New families (Transitions, Hero, Bumper) add one component + one catalog key +
one gallery section, then follow the same contract.

---

## Foundation (build FIRST) — the consistency spine

**`remotion/src/motion-tokens.ts`** (new) — single source of truth:
- `SPRING = { snap, settle, drift, wobble }` (named spring configs)
- `TIMING = { enter: 8, hold, exitLead }` frame constants
- `EASE`, `SPACE` (4/8/12…), `RADIUS`, `SHADOW.sm/md/lg`, `GLOW(accent)`
- `useEnter(delay?)` / `useExit()` hooks returning progress + transform
- `Stagger` helper for per-word / per-item delays
- `text(size, weight)` helper enforcing Devanagari-safe spacing/lineHeight
- `panel(style)` helper → the shared glass/gradient card chrome

Then **refactor** `AnimatedStatCard`, `KineticTitle`, `EditorialCard`,
`AnimatedLowerThird`, `SubscribeBell`, and the older `elements.tsx` pieces onto
these tokens. No visual overhaul — just unify the vocabulary so v2 additions
inherit it. (`useScale` already exists in `motion-library.tsx`; fold it in.)

---

## The catalog expansion — the LIST

Target: **33 → ~85 variants** across the existing 6 families + **3 new families**
(Transitions, Hero moments, Bumper/brand). ★ = signature/hero (higher craft).

### 1. Stat / data cards — `AnimatedStatCard` (6 → 15)
Existing: glass, split, radial, ticker, stamp, horizon.
New:
- `trend` — animated line/area graph that draws left→right, end-dot pulses ★
- `donut` — multi-segment donut with animated arcs + legend
- `delta` — big number with ▲/▼ change chip and colored movement
- `bars-race` — horizontal bars that grow + reorder (ranked leaderboard) ★
- `pictograph` — icon/tally grid filling to represent a count
- `gauge` — speedometer needle sweeping to value
- `spark` — big number with an inline sparkline underneath
- `map-stat` — value pinned to a location dot (ties into map motif) ★
- `progress-cluster` — 2–3 mini progress rings side by side

### 2. Kinetic typography — `KineticTitle` (7 → 17)
Existing: word-pop, wipe, stack, emphasis, orbit, split, marker.
New:
- `type-on` — typewriter reveal with blinking caret (Devanagari-cluster safe)
- `mask-line` — each line rises out from behind a masked baseline ★
- `highlight-swipe` — accent marker swipes under the keyword as it lands ★
- `rolodex` — the number/keyword flips like a split-flap board ★
- `word-swap` — a word cycles through 2–3 synonyms then settles
- `tracking-in` — letters converge from wide tracking (Latin-only guard)
- `scale-punch` — keyword slams in oversized then settles to baseline
- `line-scroll` — multi-line vertical scroll for a short quote
- `glitch-in` — brief RGB-split settle (pairs with `glitch` SFX)
- `underline-draw` — hand-drawn underline strokes on after landing

### 3. Editorial cards — `EditorialCard` (5 → 13)
Existing: definition, quote, split, timeline, warning.
New:
- `myth-fact` — two-column "❌ Myth / ✔ Fact" reveal ★
- `checklist` — steps/bullets checking in one by one
- `compare-table` — 2–3 row / 2 col mini comparison table ★
- `did-you-know` — kicker + punchy fact, field-note styling
- `chapter` — full-bleed chapter divider ("भाग 02 · …") ★
- `source` — citation/source card (builds trust, anti-AI signal)
- `map-note` — annotation pinned to a location (map motif)
- `pull-stat` — headline with an inline callout number

### 4. Scene frames / overlays — `SceneFrame` (6 → 14)
Existing: corners, film, grid, scanner, focus, aperture.
New:
- `coords` — coordinate/lat-long HUD in a corner (recurring motif) ★
- `compass` — subtle rotating compass rose ★
- `duotone` — accent duotone grade wash (per style pack)
- `dust` — slow drifting particles / depth haze
- `letterbox-tc` — cinematic bars + timecode/scene index
- `blueprint` — faint blueprint/old-map paper texture
- `radar` — sweeping radar line (pairs with `scanner`)
- `parallax` — 2-layer parallax drift on the b-roll

### 5. Lower thirds / locators — `AnimatedLowerThird` (5 → 10)
Existing: rail, pill, underline, locator, index.
New:
- `geo` — place name + coordinates (motif tie-in) ★
- `ticker` — bottom news-style scrolling strip
- `name-role` — two-line name / role attribution
- `datetag` — "तब · अब" / year tag for timeline beats
- `bracket` — corner bracket label that draws in

### 6. CTA / brand — `SubscribeBell` + CTA (4 → 8)
Existing: pill, stamp, minimal, orbit.
New:
- `combo` — like + subscribe + bell trio with sequential pops
- `arrow-nudge` — animated arrow pointing to the real subscribe button
- `chapters-bar` — thin top progress bar segmented by chapter
- `endscreen` — outro with two "next video" slots + subscribe ★

### 7. ★ NEW family: Transitions — `transitions.tsx` (0 → 8)
The single biggest generic-AI tell is plain fade/slide cuts. Add custom
Remotion `TransitionPresentation`s, biased per style pack (extend `pickTransition`):
- `whip` — whip-pan with directional motion blur ★
- `light-streak` — accent light-streak wipe (reuses `LightLeak` look) ★
- `shape-wipe` — circle/logo-mask reveal
- `film-burn` — quick warm burn/flash between scenes
- `zoom-punch` — push-in cut on a beat
- `glitch-cut` — RGB-split hard cut (pairs with `glitch` SFX)
- `page-turn` — for editorial/field-note beats
- `map-morph` — zoom/morph through a map between two places ★★ (signature)

### 8. ★ NEW family: Hero / signature moments — `hero.tsx` (0 → 5)
The "only-this-channel" differentiators, used sparingly (1–2 per video):
- `cold-open` — 1.5s title sting over first b-roll, accent sweep + logo ★
- `map-reveal` — spatial "fly to the location" opener (builds on `Map.tsx`) ★★
- `big-reveal` — the signature number/answer reveal (payoff beat) ★
- `chapter-hero` — animated chapter title card between acts ★
- `quote-hero` — full-screen pull-quote moment with grain + slow push

### 9. ★ NEW family: Brand bumper — `bumper.tsx` (0 → 2)
- `logo-sting` — 0.8s animated logo/watermark bumper (intro + reuse in outro) ★
- `bug-pulse` — the corner watermark subtly pulses on beats (channel bug)

### 10. Sound design pairing — `pipeline/sfx.py`
Every new visual gets an existing SFX; add ~5 synths to cover new beats:
- `swell` (hero reveals), `thud` (chapter cards), `flip` (rolodex),
  `draw` (underline/marker strokes), `ui-blip` (checklist/table rows).
Extend `plan_events()` so each new `visual_mode`/variant triggers its pair.

---

## Consistency mechanisms (so the library can't drift)

- **Catalog-sync test** (`tests/`): assert `MOTION_CATALOG` (parsed from
  `motion-library.tsx`) == the tuples in `motion.py` == the SFX pairings. A
  missing/renamed variant fails CI instead of shipping a blank scene.
- **Tokens as the only source** for spring/timing/space/shadow — lint/review
  rule: new variants import from `motion-tokens.ts`, no fresh magic numbers.
- **Semantic selection** upgrade in `decorate_scenes()`: choose stat/card
  variant from the data shape (has `bars` → bars-race/donut; has `baseline` →
  delta/compare; single value → horizon/big-reveal) instead of pure cycling.
- **Per-video variety budget**: track used variants in `decorate_scenes` (it
  already cycles) and extend to avoid repeats across the whole video, and
  optionally seed off the ISO week so consecutive uploads differ.
- **Style-pack awareness**: hero/transition families read `style.transitionBias`
  and `accent` so each of the 4 packs (documentary/kinetic/editorial/noir) keeps
  its distinct feel.

---

## Phased build plan

**Phase 0 — Foundation (unblocks everything).**
`motion-tokens.ts` + `useEnter/useExit/Stagger/text/panel`; refactor the 6
existing components onto it. Add the catalog-sync test. No new variants yet —
prove the gallery + CI still render green.

**Phase 1 — Breadth across existing families.**
Add the new Stat, Kinetic, Card, Frame, Lower-third, CTA variants (§1–6). Each
follows the 5-step reuse contract; gallery auto-covers them. Pair SFX as you go.

**Phase 2 — Transitions family (§7).**
`transitions.tsx` custom presentations; extend `pickTransition` in `Main.tsx`
and `ShortMain.tsx` with per-pack bias. Add a gallery/preview strip.

**Phase 3 — Hero + Bumper (§8–9) — the signature layer.**
`hero.tsx`, `bumper.tsx`; add `visual_mode` values (`hero`, `chapter`) and a
`bumper` manifest slot; teach `script_gen` to mark 1 cold-open + optional
chapter beats; place a logo sting at the top of `Main.tsx`.

**Phase 4 — Sound + semantic selection (§10, consistency §).**
New SFX synths + `plan_events` pairings; upgrade `decorate_scenes` to
data-shape-aware selection and cross-video variety.

**Phase 5 — Polish pass.**
Timing/scale review of every variant at 1080p + Shorts 1080×1920; Devanagari
overflow checks; trim anything that reads generic.

Rough end state: **~85 variants across 9 families**, one token system, a catalog
that can't silently drift, and 5–7 signature moments that make the channel
recognizable.

---

## Verification

- **Remotion**: `cd remotion && npm ci && npx tsc --noEmit` then
  `npx remotion render MotionGallery` — the gallery auto-includes every new
  variant, so a broken/blank variant shows up in the render. This is already the
  CI job on `main`, so keep it green.
- **Python**: `pytest tests/` including the new catalog-sync test and
  `motion.py`/`sfx.py` unit tests (variant assignment is deterministic → easy to
  assert).
- **End-to-end smoke**: render one long `Main` and one `Short` from a real
  manifest and eyeball a stat scene, a kinetic scene, a card scene, a hero beat,
  and one transition — confirm SFX line up and Hindi text doesn't clip.
- Extend the existing motion-gallery CI check to also render a short-format
  (1080×1920) gallery pass so portrait scaling regressions are caught.

## Critical files
- New: `remotion/src/motion-tokens.ts`, `remotion/src/transitions.tsx`,
  `remotion/src/hero.tsx`, `remotion/src/bumper.tsx`, `tests/test_motion.py`
  (catalog-sync + selection).
- Edit: `remotion/src/motion-library.tsx` (variants + `MOTION_CATALOG` +
  gallery), `remotion/src/Main.tsx` & `ShortMain.tsx` (transitions, hero, bumper,
  frame wiring), `remotion/src/Root.tsx` (`Manifest` slots: `bumper`, `hero`,
  chapter), `pipeline/motion.py` (catalog tuples, semantic selection, variety),
  `pipeline/sfx.py` (new synths + pairings), `pipeline/script_gen.py`
  (mark cold-open/chapter beats), `config.yaml` (`motion_library` toggles).
