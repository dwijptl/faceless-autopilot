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
