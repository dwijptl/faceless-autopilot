# 🎬 Faceless Autopilot

A fully automated, **$0-per-video** faceless YouTube pipeline that runs entirely on GitHub's
cloud (nothing on your machine). Three times a week it invents a topic, writes a script,
narrates it, downloads matching HD b-roll, burns in synced captions, mixes music, renders
a 1080p MP4 — and publishes everything to a **date-and-time-stamped GitHub Release**.

```
topic (Gemini, auto) ─→ script (Gemini) ─→ voiceover (Kokoro TTS, Apache 2.0)
        ─→ b-roll (Pexels API) ─→ captions (auto-synced) ─→ render (FFmpeg/MoviePy)
        ─→ Release "video-2026-07-09_0630" { final.mp4 · captions.srt · thumbnail.jpg · script.json · metadata }
```

**Every run costs $0**: Gemini API free tier (script), Pexels API (free commercial-license
footage), Kokoro-82M (open-source Apache-2.0 voice, runs on the free runner itself),
GitHub Actions (free unlimited minutes on public repos).

---

## One-time setup (~10 minutes, all in the browser)

### 1. Create the repo

1. Sign in at github.com → **New repository** → name it (e.g. `faceless-autopilot`) →
   **Public** (public = unlimited free Actions minutes; private = 2,000 min/month ≈ 4–6 videos)
   → Create.
2. Unzip the delivered `faceless-autopilot.zip`, then on your repo page: **Add file →
   Upload files** → drag **the contents** of the folder in (keep the folder structure)
   → Commit.
3. ⚠️ If the `.github/workflows/make_video.yml` file didn't upload (browsers sometimes skip
   hidden dot-folders): **Add file → Create new file**, type
   `.github/workflows/make_video.yml` as the name, paste the file's contents, commit.

### 2. Get your two free API keys (no credit card)

| Key | Where | Notes |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com → **Get API key** | Free tier: ~1,500 requests/day — a video uses ~3 |
| `PEXELS_API_KEY` | pexels.com/api → **Get started** | Free: 200 req/hour, 20k/month — a video uses ~30 |

Add both in your repo: **Settings → Secrets and variables → Actions → New repository
secret** (exact names above).

### 3. (Recommended) Add music

Follow `music/README.md` — one 5-minute batch of YouTube Audio Library tracks lasts months.
Skipping this is fine; videos just render without music.

### 4. First run

**Actions** tab → enable workflows if prompted → **Make Video → Run workflow** (optionally
type a topic; leave empty for auto). Watch the log. In ~30–60 min a release named
`video-<date>_<time>` appears under **Releases** with your finished video.

From then on it runs itself **Mon/Wed/Fri 06:30 UTC** (edit the cron line in
`.github/workflows/make_video.yml` to change).

---

## What you get per run (your dated "folder")

Each release `video-YYYY-MM-DD_HHMM` contains:

- `final.mp4` — 1080p30, H.264, captions burned in, music ducked under narration
- `captions.srt` — upload in YouTube Studio → Subtitles for proper CCs
- `thumbnail.jpg` — 1280×720, auto-generated from the hook scene + title text
- `script.json` — full script (title, description, tags, scenes)
- Release notes — paste-ready YouTube description + pre-upload checklist

## Customizing

Everything lives in `config.yaml` (edit on GitHub, takes effect next run): niche, tone,
video length, voice (`af_sarah`, `am_michael`, `bm_george`…), speaking speed, caption
style, music volume, crossfade timing. Schedule lives in the workflow file.

## Licensing & monetization notes (important)

- **Pexels** footage/photos: free for commercial use, no attribution — monetization-safe.
- **Kokoro-82M** voice: Apache 2.0 — commercial use explicitly allowed.
- **YouTube Audio Library** music: monetization-safe; credit CC-BY tracks in the description.
- **YouTube's "inauthentic content" policy (since July 2025)** prohibits monetizing
  mass-produced, low-effort AI content. Protect yourself: watch each video before uploading,
  fix weak scripts (re-run with a forced topic), customize titles/descriptions, and space
  uploads sensibly. The per-run checklist in the release notes exists for this reason.
  This tool is an execution engine — the editorial judgment that makes content monetizable
  is still yours.
- Deliberately **not included**: auto-upload to YouTube. It's technically possible
  (YouTube Data API) but uploading unreviewed AI video is exactly what gets channels
  demonetized. Review, then upload — it's 2 minutes.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Run fails at "Run pipeline" with missing key | Check both secrets exist with exact names |
| `Gemini call failed on all models` | Model names rotate: update `llm.model` in config.yaml to a current free-tier Flash model from ai.google.dev |
| Video too short / scenes feel empty | Raise `video.target_minutes`, or add more specific `niche` wording |
| Robotic-sounding voice | Try other Kokoro voices; or see "$5 upgrade" below |
| No captions visible | `captions.enabled: true` in config.yaml |
| Scheduled run didn't start | GitHub pauses cron on repos inactive for 60 days — push any commit, or use manual runs |

## Optional quality upgrades (only paid things worth it)

- **ElevenLabs Starter, $5/mo** (~$0.40/video at 3/week): swap `tts.py` for their API —
  the single biggest perceived-quality jump. The modular design makes this a one-file change.
- Everything else stays $0.
