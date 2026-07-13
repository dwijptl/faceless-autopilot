# LONGFORM_UPGRADE_PLAN — combined best-of (Claude × ChatGPT × Gemini reviews)

> Merged **2026-07-13** from three independent analyses of the pipeline, then
> verified line-by-line against `main` (the external reviews audited a
> July-10 checkout, so several of their "gaps" were already fixed).
> Hard constraint honored throughout: **no major cost increases** — every
> adopted item is ₹0 to a few US cents per video. Companion to
> `GROWTH_PLAN.md` (strategy) and `FAILURES.md` (quality registry).

## Shared verdict across all three reviews

The bottleneck is **automated editorial judgment, not more AI generation**.
Build stricter gates around the existing foundations (semantic beats, vision
QC, motion library, simulation engine) instead of replacing anything.
All three independently converged on the same avoid-list too — that
consensus is the strongest signal in this document.

## Triage: external claims vs actual main

| Claimed gap | Status on main |
|---|---|
| "6 minutes is only a prompt" | **FIXED** — HARD RANGE 92–108% word budget + expansion pass + post-TTS duration warning (accept window ≈5:20–7:10; no padding) |
| "Tease doesn't reserve next topic" | **FIXED** — `NEXT:` queue in topics_done.txt; pick_topic honors it; TEASE-IS-A-CONTRACT rule |
| "No visual-story contract" | **HALF-FIXED** — `forbidden_visuals` (must-NOT-show) threaded scene→assets→vision QC; per-beat `must_show` missing |
| "Fact-check is advisory" | **REAL** — `config.yaml factcheck.gate: false`, 8 claims max, narration only |
| "Vision QC fails open / accepts after budget exhausted" | **REAL** — `vision_qc.py` returns True on error/exhaustion |
| "Single thumbnail concept" | **HALF-REAL** — 3 concepts generated as text, only 1 rendered |
| "Shorts independent of long-form" | **REAL** — separate topic selection, no funnel by design |
| "Analytics can't map retention to scenes" | **REAL** — no beat-timestamp map in metadata |
| "No pronunciation control, darkness/duplicate checks on scenes" | **REAL** — luma guard exists for thumbnails only |

## Adopted backlog (all cheap; ordered for implementation)

### Phase 1 — Trust gates (script/verify layer, ~₹0)

**G1. Two-tier blocking fact gate** *(ChatGPT; refined)* — extend factcheck
to cover narration + stat cards + title + thumb text + final tease (the
Venus "iron vaporizes" class). Unsupported **high-risk numeric/physical
claims → release marked `DRAFT — DO NOT PUBLISH`** in metadata; everything
else stays advisory. `factcheck.gate: "high_risk"`. Cost ~$0 (same Gemini
grounded calls, slightly larger claim set).

**G2. Claim ledger** *(ChatGPT)* — factcheck writes `claims.json`
(claim → source URL → confidence → simplification note) into the release.
Doubles as the public source-sheet habit (Kurzgesagt pattern). $0.

**G3. Vision QC fail-to-fallback** *(all three)* — on budget exhaustion or
API error, stop accepting unchecked stock; route that scene to the fallback
hierarchy instead: AI hero still → procedural diagram/card → gradient.
Renders never break; wrong footage never ships. $0, behavior change only.

**G4. Per-beat `must_show` + candidate ranking** *(ChatGPT)* — beats gain
`must_show` (we already have must-not). assets.py fetches 2–3 candidates
per beat and one vision call picks the best (semantic match, contradiction,
darkness, hero continuity) within the existing QC budget. Pennies.

### Phase 2 — Packaging & continuity (~₹0–8/video)

**G5. Render all 3 thumbnails** *(ChatGPT + GROWTH_PLAN)* — same hero image,
3 `remotion still` passes with the 3 `thumb_options` headline/question
props → `thumbnail_a/b/c.jpg` in the release → native Test & Compare gets
real variants, not text descriptions. $0 (render time only).

**G6. Hero pose set** *(Gemini + ChatGPT)* — for journey topics generate 3
poses once (establishing / in-action / final-state) from the same
`hero_prompt` + seed, mapped to hook/mid/climax beats. Kills the
scuba-diver class permanently. +1–2 images ≈ $0–0.10.

**G7. Pronunciation dictionary** *(ChatGPT)* — `brand/pronunciations.yaml`
(English scientific terms → Devanagari respelling) applied to narration
before TTS; appendable whenever a render mispronounces. $0.

**G8. Scene luma + duplicate guard** *(both)* — reuse the thumbnail
mean-luma check on chosen scene assets (too-dark → next candidate →
fallback); perceptual-hash dedup within episode and against
`assets_used.json` history. Pure PIL/ffmpeg, $0.

### Phase 3 — Editorial rhythm & feedback (~₹0)

**G9. Visual-role rotation** *(Gemini)* — each beat tagged
`experience | explanation | measurement`; scriptgen must rotate roles so no
3 consecutive beats share one (prevents stock-montage monotony); renderer
biases overlays accordingly (measurement → HUD/readout, explanation →
diagram/card, experience → full-bleed, fewer overlays). $0.

**G10. Function-based shot timing** *(both)* — per-beat `target_seconds`:
2–3s cuts in hook, 4–7s normal, 8–10s for the hero/climax shot, silence
already precedes reveals. The idea sets the cut, not a timer. $0.

**G11. Post-render contact-sheet audit** *(ChatGPT's animatic, adapted)* —
renders are free on Actions, so no pre-render gate needed; instead after
render, extract 1 frame/12s into a contact sheet + one Gemini vision pass
answering the publish-audit checklist (contradictions, darkness, hero
continuity, caption readability, leftover HUD at logo). Serious
contradiction → `DRAFT — DO NOT PUBLISH` flag in quality_report. The human
publish step stays the final gate. ~1 vision call ≈ $0.01.

**G12. Feasibility dimensions in topic gate** *(ChatGPT)* — existing
3-candidate journey scoring gains: visualizability with our asset stack,
source confidence, thumbnail one-image simplicity, sequel potential, Indian
audience relevance. Reject interesting-but-unfilmable topics before
spending. $0.

**G13. NASA adapter** *(ChatGPT)* — images-api.nasa.gov for space topics:
free, exact-entity, public-domain (keep per-asset attribution in
assets_used.json). This is *not* "more generic stock" — it's primary-source
footage for our biggest pillar. $0, ~1 day.

**G14. Shorts as derived trailers** *(all three; = GROWTH_PLAN H3)* — Shorts
topic gate biases to the latest long-form's strongest single fact, reuses
its hero/style pack, never summarizes the whole video; long-form set as the
Short's related video in Studio. $0.

**G15. Beat-timestamp map** *(ChatGPT)* — metadata gains
`beats: [{label, start, end, visual_role, asset_kind}]` so retention dips
map to exact creative choices once analytics CSVs arrive. $0 now, pays off
at day 14+.

## Rejected — unanimous or cost-violating

Full/majority AI-video generation (tens of $/video) · agent swarm · ML
retention predictor (no data) · headless Blender (weeks of maintenance) ·
ElevenLabs voice swap (Sarvam is the brand) · self-hosted image models ·
more generic stock subscriptions · human animatic checkpoint (manual publish
already IS the human gate; G11 automates the audit) · padding to 8 min ·
2 long-form/week before consistency proves · decorative HUD without real
data. GROWTH_PLAN's optional Wan hero-motion (H1) stays **deferred** under
the no-cost-increase constraint — revisit only after retention data.

## Cost impact

Phase 1–3 combined: **≈$0.02–0.15 per video worst case** (a few extra
Gemini vision/image calls inside existing budgets). Voice cost unchanged.
Runtime +5–10 min per render. Constraint met.

## Implementation order (each row ≈ one dev task)

1. G3 fail-to-fallback (smallest, highest trust win)
2. G1+G2 fact gate + claim ledger (one factcheck.py + config change)
3. G5 three rendered thumbnails
4. G7 pronunciation dictionary
5. G8 scene luma/dedup guard
6. G4 must_show + candidate ranking
7. G9+G10 visual roles + shot timing (script prompt + renderer)
8. G6 hero pose set
9. G11 contact-sheet audit
10. G12 topic feasibility dims
11. G14 shorts-as-trailers
12. G15 beat-timestamp map
13. G13 NASA adapter

Estimated total: ~6–9 sessions of pipeline work, zero new services, zero
new secrets except nothing — all runs on existing GEMINI/PEXELS/SARVAM keys.
