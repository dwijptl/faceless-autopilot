# CASE FILE pivot — 2026-08

The channel converts from mixed science/what-if explainers to ONE identity:
**real-case investigation mysteries in Hindi** — one documented, unexplained
case per episode, told evidence-first, like a detective walking the viewer
through the file. This document is the strategy of record; the executable
parts live in `config.yaml` (niche, band), `topics_queue.txt` (the slate),
and `pipeline/script_gen.py` (`_case_rules()`).

## Why (from the 2026-07 analytics window + niche research)

The channel's 28-day export showed 782 views, 214 unique viewers, 2,505
impressions, 3.99% CTR, 5 subscribers — and the number that decided the
pivot: **183 new viewers, 8 returning, 0 regular**. Nobody knew what the
channel *was*, so nobody came back. Topic scatter (space, deep sea, what-if,
geology, anomalies) meant every upload restarted from zero.

Niche research (2026-08-03) found the Hindi "mystery" space is owned by
horror storytelling (Khooni Monday ~6.4M), paranormal listicles (Unknown
Mysteries Hindi ~5M, Mysterious World Hindi ~2.8M) and crime narration — but
the **evidence-first case-file format** (MrBallen / LEMMiNO in English) has
no dominant Hindi-native owner, while Hindi articles on these exact cases
(Lallantop, TV9 on Dyatlov) prove the demand. Indian cases (Roopkund,
Stoneman, Jatinga) are nearly untouched in this format and cannot be taken
by English creators adding Hindi dub tracks.

## The funnel, in fix-order

1. **Packaging (CTR)** — the current bottleneck. Dyatlov (2026-08-02) got
   423 impressions in a day and converted 1.18%. Titles sell the premise in
   plain Hindi (never a proper noun as the hook); thumbnails keep the
   channel's clean documentary look, NOT the niche's horror-coded red/black
   clutter — distinct-in-feed beats loud-in-feed.
2. **First 45 seconds** — cold open contract: the impossible human moment
   first; names, places, dates only after the viewer cares.
3. **Detective engine** — clue → theory → problem every scene; the viewer's
   best guess flips ≥3 times; the case never feels solved until the final
   10%; the ending honestly names what remains unexplained.
4. **Length last** — see promotion rule.

## Duration policy

Band is **8–12 minutes** (config `video:`). Viewers currently watch 1:30–2:20
of long-forms; minutes watched, not percentage, is what transfers to longer
videos, so 15–20 min now would render as ~15–20% average-viewed and poison
browse. **Promotion rule:** raise the band to 12–15 (then 15–20) only after
3 consecutive uploads hold average view duration above ~4.5 minutes with a
gradual (not cliff-shaped) retention curve. The analytics override bounds in
`pipeline/analytics.py` track the active band — move them together.

## The slate

`topics_queue.txt` holds the ordered 8-case slate (global/Indian mix).
Long-form runs execute the queue before inventing topics; Shorts keep
auto-picking single-claim CASE TEASERS around it (funnel to long-form).
Cases already shipped before the queue existed: Dyatlov Pass,
Hinterkaifeck, Yuba County Five.

## Evaluation — after the 8-video slate, judge ONLY these

- **CTR** on each video's first 300+ impressions (target: stable 4–6%)
- **Average view duration in minutes** (target: climbing toward 4+)
- **Returning viewers** (must move off ~8/month)
- **Suggested-traffic share** climbing

Views are noise at this impression volume. If CTR stays under ~3% across 4+
uploads, repackage (thumbnail/title) before questioning the niche — and
repackage old uploads (Dyatlov first) rather than deleting them.

## Standing to-dos outside this repo

- Unlist the off-niche "india us tariff" video; curate channel-page rows to
  mystery content only.
- Repackage the Dyatlov upload (new thumbnail, tighter title) — free CTR
  retest on a video YouTube already showed 423 times.
- Upload the brand kit refresh if the banner/tagline change (config
  `brand.tagline` now carries the case-file promise).
