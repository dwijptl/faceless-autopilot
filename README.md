# 🎬 Faceless Autopilot — हिन्दी edition

A fully automated faceless YouTube pipeline that runs entirely on GitHub's
cloud (nothing on your machine). Three times a week it invents a topic, writes
a **Hindi** script, narrates it in **your own cloned voice** (Sarvam AI),
downloads matching HD b-roll, burns in synced Devanagari captions, mixes
music, renders a 1080p MP4 — and publishes everything to a
**date-and-time-stamped GitHub Release**. Shorts run on the alternate days.

```
topic (Gemini, auto) ─→ Hindi script (Gemini) ─→ grounded claim review ─→ voiceover
        (Sarvam bulbul:v3, YOUR cloned voice; guarded Kokoro fallback) ─→ b-roll (Pexels API)
        ─→ captions (Sarvam STT-aligned when available, estimated fallback; Devanagari)
        ─→ render (Remotion / FFmpeg) ─→ Release "video-2026-07-10_0630" { final.mp4 · captions.srt · thumbnail.jpg · script.json }
```

**Cost per video:** everything is $0 (Gemini free tier, Pexels, GitHub Actions,
Kokoro) **except the voice**: Sarvam gives ₹100 free credit on signup, then TTS
is ~₹30 per 10,000 characters — roughly **₹15–20 per long video, ~₹2 per
short**. If Sarvam is unreachable or out of credits, the pipeline automatically
falls back to the free Kokoro Hindi voice so scheduled runs never fail.

---

## One-time setup (~15 minutes, all in the browser)

### 1. Create the repo

Already done if you're reading this on your own repo.

### 2. API keys (repo secrets)

| Secret | Where | Notes |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com → **Get API key** | Free: ~1,500 req/day — a video uses ~3 |
| `PEXELS_API_KEY` | pexels.com/api → **Get started** | Free: 200 req/hour — a video uses ~30 |
| `SARVAM_API_KEY` | dashboard.sarvam.ai → API Keys | ₹100 free credit; then ~₹30/10k chars |
| `SARVAM_SPEAKER` | dashboard.sarvam.ai → your **cloned voice ID** | Clone needs a 30–60s consented sample. Any preset (`amit`, `kavya`…) also works |
| `FAL_KEY` *(optional)* | fal.ai → Keys | Turns on **FLUX signature shots** (~$0.05/img, ~$0.20/video). Without it: free Gemini images |
| `ANTHROPIC_API_KEY` *(optional)* | console.anthropic.com | Claude writes the scripts (crisper hooks, ~$0.05/script). Without it: free Gemini |

Add each: **Settings → Secrets and variables → Actions → New repository secret**
(exact names above).

### 3. Test your voice (recommended before the first video)

**Actions → Test Voice → Run workflow.** ~1 minute later, download the
`voice-test` artifact from the run page and listen. If it fails, the log says
exactly what's wrong (key, credits, or speaker ID).

### 4. (Recommended) Add music

Follow `music/README.md` — one 5-minute batch of YouTube Audio Library tracks
lasts months. Skipping is fine; videos just render without music.

### 5. First run

**Actions → Make Video → Run workflow** (optionally force a topic — Hindi or
English both work; leave empty for auto). In ~30–60 min a release named
`video-<date>_<time>` appears under **Releases**.

Schedules (tuned for the Indian audience): long-form renders **Mon + Thu
10:30 AM IST** → review, then schedule the publish for **4–5:30 PM IST**
(viewing peaks 6–8 PM). Shorts render **Tue/Wed/Fri/Sat 10:30 AM IST** →
publish **6–8 PM IST** (scroll peaks 7–10 PM). That's 2 long + 4 shorts
≈ 26 uploads/month — shorts funnel viewers to long-form, and each long
video gets a clean 3-day browse window. Edit the cron lines in
`.github/workflows/` to change.

---

## What you get per run (your dated "folder")

Each release `video-YYYY-MM-DD_HHMM` contains:

- `final.mp4` — 1080p30, H.264, Hindi narration in your voice, Devanagari
  captions burned in, music ducked under narration
- `captions.srt` — Hindi; upload in YouTube Studio → Subtitles (language: Hindi)
- `thumbnail.jpg` — 1280×720, hook-scene frame + Hindi title text
- `script.json` — full script (title, description, tags, scenes — all Hindi)
- `quality_report.json` — semantic visual coverage, asset reuse and final
  audio/video delivery checks
- Release notes — paste-ready YouTube description + pre-upload checklist

## The language layer

- `config.yaml → channel.language: "hi-IN"` drives everything: Gemini writes
  Devanagari scripts/titles/descriptions, Sarvam speaks Hindi, captions and
  thumbnails render with Noto Sans Devanagari.
- Stock **search terms and AI image prompts stay in English** (libraries are
  indexed in English) — enforced in the prompt.
- Word budgets use `channel.wpm: 130` (Hindi documentary pace) instead of the
  English 150.
- Switch the whole channel back to English anytime: `language: "en-us"`,
  `tts.engine: "kokoro"`, `voice: "am_michael"`.

## The originality layer (anti-"generic AI channel")

- **FLUX signature shots** — with `FAL_KEY` set, each video gets up to 4
  custom AI stills (2 per short) generated to match the video's rotating
  style pack: every prompt is wrapped in that pack's photographic grammar
  (documentary 35mm / high-contrast kinetic / muted editorial / noir), so
  the AI shots look like one photographer shot the whole video.
- **Cinematic stock shaping** — every Pexels search runs first with a
  rotating modifier (`aerial`, `macro close up`, `drone`, `dramatic`…), so
  the pipeline pulls the moody professional b-roll buried in Pexels instead
  of front-page vacation clips. Raw terms remain as recall fallback.
- **Karaoke captions** — words appear as they're spoken, active word in
  brand amber, spring pop per word (documentary + kinetic packs).
- **33-variant native motion library** — six stat cards, seven kinetic-title
  treatments, five editorial cards, six scene frames, five lower thirds and
  four subscribe/bell CTAs rotate deterministically before repeating. The
  matching 18-cue sound pack is synthesized at render time, so both libraries
  are free and carry no marketplace-license dependency. See
  [`docs/MOTION_LIBRARY.md`](docs/MOTION_LIBRARY.md).
- **Human-writing rules** — banned stock phrases ("did you know", "क्या आप
  जानते हैं"…), enforced sentence rhythm, one vivid named fact per scene;
  optional Claude script engine via `ANTHROPIC_API_KEY`.

## The intelligence layer

- **Visual originality** — scenes are scripted with a `visual_mode`: stock
  b-roll, AI-generated stills (Gemini image API, ~500/day free), kinetic
  typography, or animated stat cards. `assets_used.json` guarantees no clip,
  photo, or AI prompt ever repeats across videos. Four visual style packs
  (documentary / kinetic / editorial / noir) rotate per video.
- **Sentence-level visual editing** — one additional free Gemini planning call
  divides long-form narration into concrete visual beats. Each beat carries an
  exact Hindi cue and subject-specific English stock query, so imagery changes
  with the spoken idea instead of merely rotating through scene-level footage.
- **Self-learning loop** — drop YouTube Studio CSV exports into `analytics/`
  (see its README); the weekly **Update Learnings** workflow digests them into
  `learnings.md`, which steers topic choice, hooks, pacing, length and
  thumbnail text on every subsequent video.
- **Production safety gates** — fallback narration is clearly marked and
  published only as a draft release; Hindi captions use Sarvam STT word
  timestamps when available; factual claims are checked with grounded Google
  Search before TTS; stock-video QC samples multiple points in each clip.
- **Automated delivery QC** — long-form runs verify continuous beat coverage,
  semantic bindings, excessive asset reuse, stream presence, resolution and
  final duration. It reports problems without blocking production by default.
- **Reviewer status** — every release includes `run_summary.json` and a prominent
  metadata line showing voice, caption, fact-check and draft status.
- **Terra Incognita brand kit** — `brand/` has the banner, avatar, and
  YouTube watermark to upload once in YouTube Studio → Customization; every
  video automatically carries the corner watermark, branded captions/lower
  thirds, and outro card. See `brand/BRAND.md`.

## Customizing

Everything lives in `config.yaml` (edit on GitHub, takes effect next run):
niche, tone, video length, voice settings (`tts.speed`, `temperature`,
fallback `voice`), caption style, music volume, crossfade timing. Schedule
lives in the workflow files.

## Licensing & monetization notes (important)

- **Pexels** footage/photos: free for commercial use, no attribution — monetization-safe.
- **Sarvam cloned voice**: it's your own consented voice — usable in monetized
  content under Sarvam's terms (you cloned it from your own sample).
- **Kokoro-82M** fallback voice: Apache 2.0 — commercial use explicitly allowed.
- **YouTube Audio Library** music: monetization-safe; credit CC-BY tracks in the description.
- **YouTube's "inauthentic content" policy (since July 2025)** prohibits monetizing
  mass-produced, low-effort AI content. Protect yourself: watch each video before uploading,
  fix weak scripts (re-run with a forced topic), customize titles/descriptions, and space
  uploads sensibly. The per-run checklist in the release notes exists for this reason.
  This tool is an execution engine — the editorial judgment that makes content monetizable
  is still yours.
- Deliberately **not included**: auto-upload to YouTube. Review, then upload — it's 2 minutes.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Run fails at "Run pipeline" with missing key | Check all secrets exist with exact names |
| Narration is NOT your voice | `SARVAM_API_KEY`/`SARVAM_SPEAKER` missing or out of credits — run **Test Voice** to see the exact error; check dashboard.sarvam.ai balance |
| Release is a draft with REVIEW warning | A voice fallback or configured fact-check gate requested human review; read `run_summary.json`, fix the cause, and re-run |
| Captions say estimated/mixed | Sarvam STT alignment was unavailable for one or more scenes; captions still use the safe timing estimate |
| Sarvam 422 in the log | `SARVAM_SPEAKER` doesn't match bulbul:v3 — re-copy the cloned voice ID from the dashboard |
| `Gemini call failed on all models` | Update `llm.model` in config.yaml to a current free-tier Flash model from ai.google.dev |
| Hindi text shows as boxes (tofu) | Workflow installs `fonts-noto-core` — check that apt step succeeded |
| Video too short / scenes feel empty | Raise `video.target_minutes`, or add more specific `niche` wording |
| No captions visible | `captions.enabled: true` in config.yaml |
| Scheduled run didn't start | GitHub pauses cron on repos inactive for 60 days — push any commit, or use manual runs |

## Cost control

- The run log prints `sarvam chars: N (≈ ₹X)` per video — actual spend, no surprises.
- Hard-stop option: keep only a small balance on the Sarvam account; the
  pipeline falls back to Kokoro (free) the moment credits run out.
- Force free voice anytime: `tts.engine: "kokoro"` in config.yaml.
