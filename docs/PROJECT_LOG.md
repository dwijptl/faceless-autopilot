# PROJECT LOG — Terra Incognita / faceless-autopilot

> Session tracker for humans and AI assistants (Claude, Codex). Read this
> before changing anything. Last updated: **2026-07-12** (Claude session).

## What this is

Fully automated faceless YouTube channel **Terra Incognita** (Hindi / हिन्दी):
science + geography "what if / hidden worlds" documentaries. GitHub Actions
renders everything in the cloud; the owner reviews each release and uploads
manually (auto-publish deliberately excluded for YouTube policy safety).

- Long-form 16:9 ~6 min — `Make Video` (Mon + Thu 10:30 IST)
- Shorts 9:16 ~25s — `Make Short` (Tue/Wed/Fri/Sat 10:30 IST)
- `Update Learnings` (Sun) — digests `analytics/` CSVs → `learnings.md`
- `Test Voice` — 1-min Sarvam voice check artifact
- `CI` — Python + Remotion checks on every push (**must stay green**)

**Cost/video:** ~₹15–20 long-form, ~₹2 short (Sarvam TTS) — everything else
free tier (Gemini, Pexels, Kokoro fallback, GitHub Actions public repo).
Optional: FAL_KEY (FLUX signature stills), ANTHROPIC_API_KEY (Claude scripts).

## Architecture (one line each)

`pipeline/run.py` orchestrates: topic (journey-scored) → Hindi script
(Claude/Gemini + critique pass + visual beats) → grounded fact-check → Sarvam
cloned voice (Kokoro fallback, reveal-pause pad) → STT word alignment →
map render → assets (FLUX/Gemini AI + Pexels, never-repeat `assets_used.json`,
vision QC) → hero attach → captions → motion/SFX/music-automation plan →
manifest (`props.json`) → Remotion render (MoviePy fallback) → −14 LUFS
mastering → quality report → thumbnail → release files (`metadata.md`,
`run_summary.json`, chapters, title/thumb alternates). `run_short.py` =
vertical variant. Remotion (`remotion/src/`): `Main`/`ShortMain`/`Thumb`
compositions; `motion-library` (33 variants) + `glass` + `Map` + `hud` +
`transitions` + `elements`; 5 style packs in `styles.ts` (documentary,
kinetic, editorial, noir, telemetry) rotating per video.

## Changelog

**Jul 9 — Foundation (Claude).** Repo created via browser; base pipeline
(Gemini script, Kokoro TTS, Pexels, MoviePy→Remotion, Releases delivery);
first video same day. Remotion motion-design layer; visual originality
(visual_modes, style packs, asset log); learnings loop; Terra Incognita brand
kit (`brand/`, generator script); Shorts pipeline.

**Jul 10–12 — Hindi edition + reliability (owner + Codex).** Sarvam bulbul:v3
cloned voice + STT caption alignment + Devanagari fonts; IST schedules;
grounded fact-check with hedging; draft-gating on voice fallback;
`quality_report` + `vision_qc` + `run_summary.json`; motion library + synth
SFX + music automation (delivery-driven); smoked-glass scenes; map scenes;
sentence-level visual beats; FLUX signature shots; karaoke captions; CI +
Test Voice workflows. Production: 3 long-form + 6 shorts released.

**Jul 12 — Retention passes (Claude, all CI-green).**
1. Review fixes: overlay graphics capped to ~5s impact windows (fade + un-dim
   + caption un-compact); NARRATIVE SPINE + 60/20/20 pacing rules; telemetry
   HUD style pack; long-form captions +15%.
2. Word-synced impact timing: `_impact_start()` matches Sarvam word timestamps
   so stat/kinetic/card/glass overlays enter on the spoken keyword
   (`impactStart` in manifest).
3. Custom transitions (`transitions.tsx`): zoomPunch + blurWhip (4-dir),
   mixed into per-pack `pickTransition` (long + shorts).
4. Long-form pass: delivery-driven camera (`CameraRig`: reveal push-in,
   urgent 15Hz jitter); `ParallaxKenBurns` for AI stills; YouTube chapters
   block in metadata; chapter tick marks on progress bar.
5. **Simulation engine:** script schema gains `premise`, `changing_variable`,
   per-scene escalating `milestone` {value,label,unit}, `hero_prompt`,
   `title_options`(5) + `thumb_options`(3); topic selection = 3 candidates
   scored on the visual-journey test; `MetricReadout` HUD interpolates the
   story metric continuously (all packs); hero still pinned to hook/reveal/
   payoff beats; scale-anchoring rule (Indian comparisons); 0.35s pre-reveal
   silence pad.

## Conventions for future sessions (IMPORTANT)

- **Fetch current files before editing** — multiple AIs work here. Use
  `raw.githubusercontent.com/<owner>/<repo>/<COMMIT_SHA>/path` (the `/main/`
  CDN path serves stale content). Never edit from a stale local copy.
- Every change: syntax-check (py_compile / esbuild), push, **verify CI green**
  (`actions?query=is:failure`).
- Fail-open philosophy: new features must degrade gracefully, never block a
  scheduled render.
- **Never** add self-hosted runners or patch-applying "publisher" workflows to
  this public repo (6 secrets exposed to workflow context).
- New manifest fields: read with `(x as any)` casts in TSX to keep CI's tsc
  happy without touching `Root.tsx` types.

## Pending — owner actions (in priority order)

1. **Rotate GEMINI + PEXELS keys** (exposed in a chat on Jul 9) and update
   repo secrets. Overdue.
2. Render a fresh long-form (`Make Video`) — nothing published yet uses the
   Jul 12 passes; judge the whole stack in one watch.
3. Publish backlog on cadence; per upload: Hindi language tag, SRT, chapters
   pasted, synthetic-content disclosure, brand assets on channel.
4. After ~2 weeks of uploads: drop Studio CSVs into `analytics/`.
5. Tune to taste (all one-liners): transition intensity (`transitions.tsx`
   constants), overlay window (`longform_quality.overlay_seconds`), HUD
   position, caption size.

## Deferred (data-gated — do NOT build yet)

8.5–9 min length for mid-rolls (after retention proves at 6 min; one config
line / learnings override) · thumbnail A/B via Studio Test & Compare ·
stateful multi-scene map journeys · voice upgrades · Remotion Lambda ·
more AI video generation · storyboard pre-render gate. Rule of thumb: next
upgrade should be chosen by retention curves, not brainstorming.
