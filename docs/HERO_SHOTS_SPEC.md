# HERO_SHOTS_SPEC.md — Animated hero shots + rescue stills

Drop into `docs/`. Target: `dwijptl/faceless-autopilot`. Budget ceiling: **C$3.50/video hard, ~C$2.40 typical.**

## 1. Goal

Two upgrades, both wired to existing infrastructure:

1. **Hero shots** — animate the FLUX still of (a) the hook's first beat and (b) the reveal scene via Kling 2.6 Pro image-to-video on fal ($0.07/s, audio off). The source still stays in the timeline, so QC rejection costs nothing — the fallback already exists.
2. **Rescue stills** — when a beat's stock video fails or is QC-rejected, generate a targeted FLUX still from the beat cue instead of degrading to stock photo → gradient card. This replaces "6 extra images" with "up to 6 images exactly where stock is weakest" — the failure point FAILURES.md already identifies (contradicting stock is the top failure source).

Everything fails open. No renderer changes needed for 5s heroes: a Kling mp4 is `{"path": ..., "kind": "video"}` — the render path already plays videos.

## 2. config.yaml additions

```yaml
hero_shots:
  enabled: true            # requires FAL_KEY; silently off without it
  model: "fal-ai/kling-video/v2.6/pro/image-to-video"
  fallback_model: "fal-ai/kling-video/v2.5-turbo/pro/image-to-video"
  max_per_video: 2         # hook + reveal
  seconds: 5               # fits max_shot_seconds: 5 — no renderer change
  max_retries: 1           # ONE regenerate after QC reject, then keep the still
  audio: false             # sfx.py + mastering own the soundtrack
  in_shorts: false         # long-form only for now
  max_usd_per_video: 1.20  # hard cost gate: 2 shots + 1 retry + margin

ai_images:
  # ... existing keys unchanged ...
  rescue_budget: 6         # extra FLUX stills for beats whose stock failed/rejected
```

## 3. New module: `pipeline/hero_shots.py`

Mirror the structure/conventions of `ai_images.py` (fail-open, print-prefixed logs, cost telemetry like `tts.usage_summary()`).

```python
def animate(still_path: str, motion_prompt: str, out_path: str,
            cfg: dict, seconds: int = 5) -> bool
def usage_summary() -> str     # "hero shots: 2 (+1 retry) ≈ $1.05"
```

### fal call (queue API — video gen takes minutes; don't use sync fal.run)

1. `POST https://queue.fal.run/{model}` with header `Authorization: Key {FAL_KEY}`:
   ```json
   {"prompt": "<motion_prompt>",
    "image_url": "data:image/jpeg;base64,<still>",
    "duration": "5",
    "negative_prompt": "text, watermark, morphing, warping, extra limbs, distorted faces"}
   ```
   Base64 data-URI works for the source still (re-encode PNG→JPEG q85 first; keep payload well under fal's request limit).
2. Poll `status_url` from the response every 10s, timeout 8 min. On timeout/error → return `False` (still is used, run continues).
3. Download `video.url` from the result; accept only if size > 200 KB and `ffprobe` duration ≥ seconds − 0.5.
4. Track spend in module global (like `_sarvam_chars`): `$0.07 × seconds` per accepted OR rejected generation (you pay either way). Refuse to start a generation that would exceed `max_usd_per_video`.

### Motion prompt construction

From the beat that owns the still: `f"{beat_cue}. {CAMERA[style_pack]}, slow cinematic movement, consistent lighting, no new objects entering frame"` where

```python
CAMERA = {
  "documentary": "slow push-in, drifting atmospheric haze",
  "kinetic":     "dynamic parallax slide, hard light shifting",
  "editorial":   "measured lateral dolly, soft light",
  "noir":        "creeping zoom, fog rolling through frame",
}
```

Never prompt for: faces talking, hands, readable text, precise mechanisms. If the beat cue mentions these (keyword check: `face|hand|text|diagram|chart|अक्षर`), skip the hero and keep the still.

## 4. Placement — deterministic, from existing scene data

- **Hero 1 (hook):** scene `0` (script_gen forces `delivery: "hook"` on scene 1), beat 0. This beat runs ≤ `hook_max_seconds: 3.8` — trim the 5s clip in-timeline (renderer already trims stock clips to beat length).
- **Hero 2 (reveal):** first scene with `delivery == "reveal"` — same lookup as `run.py:132` (`_pin_recurring_hero`) and the reveal-pause logic at `run.py:345`. Use its first beat.
- If no reveal scene exists (shouldn't happen; script_gen enforces one) → generate only hero 1.

Both heroes require a FLUX still for their beat. If the scene already produced `s{NN}_ai.png`, animate that. If not, generate one (counted against `rescue_budget`, not `max_per_video_flux`).

## 5. QC gate — reuse `vision_qc.frame_ok`, zero new cost

```python
ok = vision_qc.frame_ok(
    clip_path, "video",
    scene_desc=beat_cue,
    search_term="cinematic hero shot",
    api_key=gemini_key, cfg=cfg,
    forbidden=["warped or morphing objects", "garbled or fake text",
               "broken anatomy, extra limbs", "objects appearing from nowhere",
               "flickering or strobing"],
    source="generated")
```

`frame_ok` already samples 3 frames (20/50/80%) — exactly where i2v artifacts appear (they compound toward the end of the clip). On reject: 1 retry with the same still and `negative_prompt` extended with the QC failure reason; on second reject: keep the still, log `[hero] rejected twice — shipping still`.

## 6. Rescue stills — `assets.py` integration

In `fetch_scene_assets`, in the beat loop (`assets.py:434-470`), the current fallback is stock video → stock photo → gradient card. Insert one step:

```
stock video failed/QC-rejected
  → if rescue_budget > 0 and beat has a cue:
      ai_images.generate(beat_cue_as_prompt, s{NN}_b{II}_rescue.png, ...)
  → stock photo
  → gradient card
```

Pass `rescue_budget` the same way as `ai_budget` (single-element mutable list from `run.py:407`). Prompt = `f"{beat.cue}. {beat.purpose}"` — the narration binding IS the image brief; this is what `semantic_coverage` measures, so rescued beats directly raise the `render_qc` score.

## 7. run.py integration (after the asset loop, before render)

```
1. hook_beat  = scene 0, beat 0
2. reveal_beat = first delivery=="reveal" scene, beat 0
3. for each: ensure FLUX still → hero_shots.animate() → vision_qc gate
   → on success: replace that beat's asset entry with
     {"path": clip, "kind": "video", "ai": True, "hero": True, "beat_index": i}
4. print(hero_shots.usage_summary())  # next to the sarvam line
5. add hero stats to quality_report metrics: {"hero_shots": n, "hero_retries": r}
```

## 8. Cost ledger (per long-form video)

| Item | USD | CAD (~1.37) |
|---|---|---|
| Existing base (Sarvam ₹15–20 + Claude $0.05 + 4 FLUX $0.10) | ~$0.40 | ~$0.55 |
| Hero 1 + Hero 2 (2 × 5s × $0.07/s) | $0.70 | $0.96 |
| 1 retry (worst case) | $0.35 | $0.48 |
| Rescue stills (worst case 6 × $0.025) | $0.15 | $0.21 |
| **Typical** (no retry, ~3 rescues) | **~$1.25** | **~$1.71** |
| **Worst case** (capped by config) | **~$1.60** | **~$2.20** |

Hard caps: `hero_shots.max_usd_per_video`, `rescue_budget`, `max_retries`. A runaway loop cannot exceed ~C$2.30 over base → ceiling ~C$2.90, under the C$3.50 line.

## 9. Tests — `tests/test_hero_shots.py`

Follow existing test conventions (fixtures in `tests/fixtures/`):

1. `animate()` returns False without FAL_KEY — pipeline unaffected.
2. Queue flow: request → poll → download (mock requests; assert data-URI payload + duration "5").
3. Cost gate: third generation refused when `max_usd_per_video` would be exceeded.
4. QC reject → exactly one retry → still kept on second reject (asset list unchanged).
5. Placement: hook beat 0 + reveal beat selected; no reveal → 1 hero only.
6. Keyword skip: beat cue containing "face"/"text" produces no hero.
7. Rescue still triggers only after stock failure and decrements `rescue_budget`.
8. `usage_summary()` renders spend correctly.

## 10. Rollout

1. Ship with `hero_shots.enabled: false` → enable on one manual `workflow_dispatch` run.
2. Watch `quality_report.json` + run-log `usage_summary` lines for 3–4 videos.
3. Then enable on schedule. Keep `render_qc.gate: false` until hero-era runs are clean.
4. v2 (optional, later): 10s reveal hero ($0.70) — needs a per-beat `duration` override past `max_shot_seconds` in `visual_beats.target_beat_count` + renderer beat trim; not worth it until 5s heroes prove retention lift in YouTube analytics (compare avg-view-duration on hero vs pre-hero videos, `analytics/`).
```
