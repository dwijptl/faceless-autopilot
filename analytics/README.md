# Analytics drop-in (the channel's memory)

The pipeline can't see YouTube on its own (no upload integration by design).
Feed it performance data whenever you like — 2 minutes, no schedule required:

1. Open **YouTube Studio → Analytics → Advanced mode**.
2. Pick a useful view (e.g. per-video table with CTR, impressions, average
   view duration; or a retention report) and a date range.
3. **Export → CSV**, then upload the CSV file(s) into this folder via
   GitHub's web UI (**Add file → Upload files**).
4. Done. Every Sunday (or when you manually run the **Update Learnings**
   workflow in the Actions tab), Gemini digests everything here into
   `learnings.md`.

`learnings.md` is injected into topic selection and script writing, and its
`overrides:` block auto-tunes video length and scene count within safe bounds.

Tips: replace old CSVs with fresh ones occasionally (the digest reads
everything in this folder); include at least one per-video table so the model
can connect titles ↔ performance.

## Beat-level retention join (the strongest signal)

Every render commits its beat map to `analytics/beats/<stamp>.json` — scene
timestamps with narrative role, visual mode and delivery. Pair it with the
video's actual retention curve and the weekly digest learns exactly WHICH
kind of scene loses viewers:

1. In Studio open the video → **Analytics → Engagement → Audience retention**.
2. **Advanced mode → Export current view → CSV**.
3. Save it in `analytics/retention/` named after the run stamp — the part
   after `video-` in the release tag. Release `video-2026-07-20_0830` →
   `analytics/retention/2026-07-20_0830.csv`.

The join is deterministic (no AI guessing): per-scene audience drop per
minute, aggregated by narrative role / visual mode / delivery once at least
5 videos share a pattern. Results land in `analytics/retention_summary.json`
and feed the digest prompt.
