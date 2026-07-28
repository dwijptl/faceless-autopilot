# CHANNEL_OPTIMIZATION_PLAN — the packaging sprint

> Operating plan, written **2026-07-28** from the first real publishing window
> (18 uploads, Jul 10–27) plus a live Studio pull of the newest long-form's
> first 22 hours. Companion to `docs/GROWTH_PLAN.md` (strategy, pre-data) and
> `learnings.md` (auto-digest). Where GROWTH_PLAN said "hypotheses until data
> exists" — this is the first data. Re-read after every 5 uploads; retire
> whatever the next analytics window contradicts.

## 0. What the first window actually said

Snapshot (channel, 28 days): 652 views · 10.6 watch-hours · 5 subscribers.

Newest long-form — `12,262 मीटर नीचे चट्टानें बहने लगीं — रूस को खुदाई रोकनी पड़ी`
(Kola descent, published Jul 27), first 22h:

| Metric | Value | Read |
|---|---|---|
| Impressions | 922 | best day-1 reach of any upload (rank 1 of 6) |
| CTR | **2.9%** | below the ≥4% GROWTH_PLAN floor |
| Views / unique | 28 / 18 | — |
| AVD | 2:17 | ~37% of runtime — mid |
| Traffic | 85.7% suggested · 7.1% browse · 3.6% channel · 3.6% notif | the channel lives in suggested slots |
| Impression curve | flat after hour ~7-8 | YouTube stopped the test when CTR stayed <3% |

The referrer split is the sharpest signal the channel has produced yet.
Viewers who clicked from **engineering / deep-earth / ship placements**
(जहाज क्यों नहीं डूबता, Landing Gear, समुद्री द्वीप, Venera-class content)
watched **5:26–5:46**. Viewers from **generic mystery-clickbait placements**
(कैलाश रहस्य, कुलधरा, Khatarnak island) bounced in **:01–:30**.
Same video, same hook — the difference is who the packaging attracted.

**Identity, confirmed by data: this is a science-engineering-curiosity
channel, not a broad "रहस्य" channel.** The niche paragraph in `config.yaml`
already says this; the topic gate and the packaging now have to act on it.

## 1. Diagnosis — ranked by leverage

1. **CTR is the binding constraint.** The pipeline's retention machinery
(visual beats, retention lint, hero shots) never gets an audience when the
thumbnail test dies at 2.9%. The channel's own history proves the ceiling
is real: धरती के नीचे की नदियाँ pulled **4.2%** on 143 impressions and
Mariana pulled **13.6%** on 44 — both from the same descent family.
2. **Distribution is ~100% suggested.** Browse won't arrive until CTR and
watch-history accumulate. So every packaging decision should be scored
against one question: *does this win a suggested slot next to Hindi
science-documentary content?*
3. **Long-form converts; Shorts loop.** 4 of 5 lifetime subscribers came from
ONE long-form (धरती के नीचे की नदियाँ). The 185%/104% looping Shorts
produced ≤1. Shorts are reach; long-form is the channel. The funnel links
between them (C3 in GROWTH_PLAN) are still manual and still missing.
4. **The winning topic family is now obvious.** Descent/extreme-place with a
running human-stakes variable: Mariana (best long-form AVD 45%), Kola
(best day-1 reach), NASA-signal (185% short). The losers are equally
consistent: abstract cosmology long-forms — White Hole AVD 18.5%, Venus
surface 20.5%, the 6:39 signal remake 4 views.
5. **Impressions are still tiny.** Sub-1k per video means every CTR number
above carries wide error bars. The fixes below are cheap and reversible;
treat them as the next experiment, not settled law.

## 2. The "best possible video" profile

What the pipeline should aim every long-form at, until data moves:

- **Topic:** family (1) EARTH'S EXTREMES — a real, named place or machine +
a descent/exposure premise + a running variable (depth, temperature,
seconds survived) + a hard human consequence. Real anchors (Kola, Mariana,
Venera, Challenger Deep) beat abstractions: they carry search entities and
suggested-adjacency for free.
- **Length:** 5:00–6:30 (learnings override already targets 5). No 8-min
padding until AVD ≥45% at this length (GROWTH_PLAN medium tier, unchanged).
- **Title:** claim or number form — `[संख्या+इकाई] + [जगह/मशीन] + [असंभव परिणाम]`.
The Kola title is the house formula. Question-form titles go to what-if
topics only. (`TITLE_FORMS` rotation in `script_gen.py` stays — this is a
weighting, not a lockout; see A2.)
- **Thumbnail:** ONE subject, ≤4 words, consequence visible. The 2.9% test
was lost here, not in the script.
- **Structure:** everything `retention.…` already enforces — hook ≤3.8s
visual changes, reveal at 55–85%, re-hooks at 25/50/75%, engine variable
alive till 75% — plus hero motion on hook + climax (`hero_shots`, live).
- **Series chip:** named series on thumbnail + playlist (H2, still unshipped
in Studio) — returning viewers are what compound 5 subs into 1,000.

## 3. Actions

### A. Machine-facing — small, this week, all reversible

| # | Change | Where | Why |
|---|---|---|---|
| A1 | Weight topic selection: next **8 long-forms** from the descent/extreme-place family; ≤1 abstract-cosmos topic per 8 | niche wording in `config.yaml` + next `learnings.md` digest | family (1) wins on every metric the channel has |
| A2 | Weight title forms `claim`/`number` for descent topics (rotation intact for variety policy) | `script_gen.py` TITLE_FORMS pick | Kola/Mariana titles are the proven pattern |
| A3 | Tighten long-form `thumb_text` from "3-5 keywords" to **2-4**, one number mandatory | long-form prompt in `script_gen.py` (shorts already say 2-4) | thumbnail text is the CTR lever at 1280×720 phone size |
| A4 | Seed suggested adjacency: description + tags name the real anchor entities (English + Hindi: "Kola Superdeep Borehole", "मारियाना ट्रेंच"…) | description block, `script_gen.py` | 99.7% of impressions come from recommendations; entities steer WHICH ones |
| A5 | Feed this window's packaging rules into the next **Update Learnings** run (drop fresh Studio CSVs incl. the Kola video into `analytics/`, run the workflow) | `analytics/` + Actions | `learnings.md` is what the prompts actually read — this doc is not injected |

### B. Human — per upload, ~10 min (unchanged from GROWTH_PLAN C3, still the
highest-ROI list in the repo; none of it has happened yet)

Test & Compare with all 3 thumbnail variants · related-video link on every
Short · end screen → next episode · series playlists · pinned comment ·
SRT upload · chapters check · one FAILURES.md line after watching.

### C. Deliberately NOT now (data-gated, same as GROWTH_PLAN)

8.5–9 min length (needs AVD ≥45% first) · Hinglish A/B (needs stable CTR
baseline) · English twin channel · any new production spend beyond the
existing hero-shot budget. The production stack is not the bottleneck —
don't touch it.

## 4. Targets for the next 10 uploads

| Metric | Now | Target | Source of truth |
|---|---|---|---|
| Long-form CTR | 2.9% (last), 7.5% window avg on tiny n | **≥4%** sustained at ≥500 impressions | Studio → Reach |
| Impression plateau | ~900/video | one video pushed past 2,000 | Reach curve keeps climbing after hour 8 |
| AVD at ~6 min | 37% (last) | **≥45%** (Mariana already did it) | Engagement |
| Subs per long-form | 0.28 avg | **≥1** | per-video card |
| Shorts→long conversion | unmeasured | measured (needs B-list links first) | Shorts related-link analytics |
| Cadence | gaps | 2 long + 4 Shorts/week, zero gaps | Uploads list |

Weekly: export per-video Table + Chart CSVs into `analytics/`, plus the
retention CSV for every long-form into `analytics/retention/<stamp>.csv` —
the beat-level join is the strongest signal this repo can compute and it is
still starving.

## 5. Review rule

After 5 more uploads, re-pull: CTR trend, referrer retention split, and
whether descent-family dominance survives contact with more impressions.
Whatever this document got wrong, `learnings.md` overwrites it — that is the
design. The one permanent line: **packaging is tested in suggested slots
next to Hindi science content; win there or don't get watched.**
