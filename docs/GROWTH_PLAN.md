# GROWTH_PLAN — Terra Incognita → 1M subscribers

> Strategy document, researched **2026-07-13**. Companion to `PROJECT_LOG.md`
> (system state) and `FAILURES.md` (quality registry). Every recommendation
> here maps to an actual pipeline module. Re-read after every 5 uploads.

## 0. Executive summary — the brutal truths first

1. **The pipeline is no longer the bottleneck. Publishing is.** ~50 shipped
   fixes, 3 AI reviewers converged, every actionable idea is built or
   deliberately data-gated. The channel has ~0 public uploads. Nothing in
   this document matters more than 20 uploads on cadence.
2. **Automation ceiling is real.** Kurzgesagt spends 1,200+ hours and a
   6-person research team per video. What it buys them — bespoke animation,
   year-long scripts — is not reachable by any pipeline. What IS reachable:
   the SciMyth / What If / FactTechz tier, which is systematic curation +
   simulation storytelling + packaging. That tier contains multiple
   1M–20M-subscriber Hindi channels. Aim there.
3. **The market is proven.** FactTechz: 21.4M subs (Hindi/English science
   facts). GetSetFly: multi-million. SciMyth: 1.04M with 219 videos. Hindi
   science-curiosity is a large, monetizable, under-served-in-quality niche.
4. **Retention math is the whole game.** Average YouTube retention is 23.7%;
   only 1 in 6 videos beats 50%. A payoff every 60–90s and a pattern
   interrupt in the first 5s are the two highest-leverage habits — both are
   already encoded in the script rules; the uploads will tell us if they land.
5. **Dual-format is a multiplier, not a nice-to-have.** Channels running
   Shorts + long-form grow subscribers ~3× faster; the Shorts→long funnel
   converts 0.5–2% when the related-video link is set. We already produce
   both; the funnel just needs the links.

## 1. Channel research — who wins and why

| Channel | Subs | Model (repeatable system, not one-offs) |
|---|---|---|
| FactTechz | 21.4M | High-frequency Hindi/English rapid facts; extreme pace; huge topic breadth; thumbnail = one shocking image + 2-3 words |
| GetSetFly | ~4M+ | Hindi science with personality-driven narration; strong curiosity titles; longer explainers |
| SciMyth | 1.04M | **Closest model to us**: Hindi simulation documentaries, one changing variable, HUD metrics, 13–19 min, 2-3/week |
| What If (Underknown) | 7M+ | One repeatable format: speculative premise → escalating consequences; abstract metaphor visuals; shares-driven |
| Kurzgesagt | 24.8M | Craft ceiling — bespoke animation, 1200h/video. NOT a template; steal only its research rigor + optimistic framing |
| Aperture / MelodySheep | 2–4M | Premium curation + typography + sound design + slow pacing. Proof that curation can *feel* bespoke |

**Common patterns across all of them (the repeatable system):**
- One recognizable FORMAT repeated forever, not variety (viewers subscribe
  to a feeling they can predict).
- Title = curiosity gap + number/scale + familiar anchor. Thumbnail = ONE
  subject + ≤4 words + consequence shown, question implied.
- First 30 seconds deliver the thumbnail's promise visually, then open a
  bigger question. No intros, no branding preamble.
- A visible "engine": journey, countdown, escalating variable, timeline.
- Sound design carries perceived quality more than visuals do.
- Series/playlists convert casual viewers into returning viewers; returning
  viewers, not views, are what compound into subscribers.
- Their best videos differ from their average videos mostly by TOPIC
  (bigger stakes, more universal hook) — not by production quality.

## 2. Benchmarks → our targets (hypotheses until data exists)

| Metric | Platform reality | Our target (first 20 uploads) |
|---|---|---|
| CTR | 3–4% avg, 5%+ good | ≥4% browse CTR; iterate via Test & Compare |
| 30s retention | — | ≥65% |
| Avg % viewed (6 min) | 23.7% platform avg | ≥45% |
| Shorts→long conversion | 0.5–2% | set related-link on every Short; measure |
| Cadence | — | 2 long (Mon/Thu) + 4 shorts weekly, no gaps |
| Monetization | Hindi education RPM ₹40–120; 8+ min = ~2× via mid-rolls | 6 min now → 8.5–9 min after retention proves |

## 3. Gap analysis — honest and short

**Already competitive** (do not rebuild): simulation engine (premise /
changing variable / escalating milestones / story HUD), scenario+continuity
contracts enforced at script AND vision-QC layers, hero image continuity,
sentence-level visual beats, word-synced impact graphics, 5 rotating style
packs + motion library + custom transitions, delivery-driven voice/music/
camera, grounded fact-check + failure registry, −14 LUFS mastering, chapters,
tease-chain (each video's promise becomes the next video), packaging
alternates, calm-caption hierarchy, word-budget + duration enforcement.

**Real remaining gaps:**
1. **Zero published-data feedback.** The learnings loop is built and starving.
2. **No motion in hero moments.** Stills+parallax ≈ 90% there; 1–2 true
   AI-video shots at the hook/climax would close the gap (now cheap: Wan 2.5
   $0.05/s via fal). Not yet wired.
3. **Funnel plumbing:** Shorts related-video link, end screens, playlists,
   pinned comments — manual Studio steps, not pipeline.
4. **Series identity:** formats exist implicitly (what-if simulations,
   hidden-places journeys) but aren't named/branded as series.
5. **Human taste input:** FAILURES.md captures failures; a lightweight
   "notes after watching" habit (feedback → registry) is the cheapest
   quality signal available pre-analytics.
6. **Hinglish question:** pure-Hindi narration caps RPM (₹25–80 CPM) vs
   Hinglish capturing both ad pools. Brand-level decision, test later.

## 4. Recommendations (tiered; each mapped to implementation)

### Critical (do before anything else — mostly human, ~zero cost)
| # | Action | Impact | Effort | Where |
|---|---|---|---|---|
| C1 | Publish 20 videos on cadence, zero gaps | everything | human, 10 min/video | Studio |
| C2 | Rotate GEMINI+PEXELS keys (exposed; overdue) | security | 5 min | secrets |
| C3 | Per upload: Hindi tag, SRT, chapters, synthetic disclosure, **Test & Compare with all 3 generated thumb variants**, **related-video link on every Short**, end screen → next episode | CTR+funnel | 5 min/video | Studio |
| C4 | Drop Studio CSVs into `analytics/` at day 14, then weekly | activates learning loop | 2 min/week | repo |
| C5 | After watching each render: one line per flaw into `FAILURES.md` | compounding quality | 2 min/video | repo |

### High-impact (pipeline work, small and cheap)
| # | Action | Cost | Difficulty | Notes |
|---|---|---|---|---|
| H1 | **Wan 2.5 hero-motion shots**: animate the hero still (image-to-video, 5s) for hook + climax when FAL_KEY set | ~$0.50/video | 0.5 day | extend `ai_images.py`; contract-checked like any asset |
| H2 | **Named series** in topic gate: tag each video `series: Terra Simulation / Journey Through / Earth After`; series name on thumbnail chip + playlists | $0 | prompt + Studio | returning-viewer driver |
| H3 | Shorts as **deliberate trailers**: shorts topic gate biases toward the latest long-form's most shocking fact (funnel by design, not accident) | $0 | prompt | measure conversion |
| H4 | Pinned-comment text auto-generated in release notes (question that seeds discussion) | $0 | trivial | comments = free reach in Hindi YT |

### Medium (after 10+ uploads)
- 8.5–9 min length once avg-view ≥45% at 6 min (one config line; unlocks 2× RPM via mid-rolls).
- Scene-level retention analysis: map Studio retention-graph dips to scene timestamps (chapters make this trivial); feed findings to learnings.
- Upload-time testing (16:00–17:30 IST hypothesis vs alternatives).
- Hinglish narration A/B on 2 videos (RPM + retention comparison) — brand decision follows data.

### Experimental (only if data demands)
- Veo 3.x for one cinematic signature shot ($1+/clip) if Wan quality disappoints.
- English twin channel reusing scripts (2× market, near-zero marginal cost) — only after Hindi format is proven.
- Character voice moments / dual-voice scenes.

### Avoid (deliberate no, revisit only with strong data)
- More stock providers (selection was the problem — fixed; watch for gradient-fallback frequency instead).
- Remotion Lambda / self-hosted runners (cost/risk; overnight renders are free).
- Multi-agent review bureaucracy, animatic gates, CTR-prediction models (the human 5-min review + Test & Compare native A/B do this better at n<100 uploads).
- Padding to 8 min before retention proves the 6-min format.
- Music-generation APIs (licensing murk; synth beds + YT Audio Library are clean).

## 5. Production stack verdicts (2026 research)

| Layer | Current | Verdict |
|---|---|---|
| Script | Gemini free (+ Claude opt) + critique + expansion | **Keep** — competitive |
| Voice | Sarvam bulbul:v3 cloned (₹15–20/video), Kokoro fallback | **Keep** — the differentiator |
| Stills | Gemini image free / FLUX via fal ($0.05/img) | **Keep** |
| Motion | none → | **Add Wan 2.5** i2v, $0.05/s, ~$0.50/video (H1) |
| Render | Remotion on Actions (free) | **Keep** |
| Music/SFX | synth beds + YT Audio Library | **Keep** (clean licensing) |
| Thumbnails | 3-layer branded template + brightness guard | **Keep** + native Test & Compare |
| Analytics | CSV → learnings loop | **Keep**; feed it |

**Cost per video (all-in):** long-form ₹20–90 (voice + optional FLUX $0.20 +
optional Wan $0.50); short ~₹2–10. Runtime ~60–90 min unattended.

## 6. Worked example — next episode (already tease-locked): Venus

**Topic (locked via `NEXT:` marker):** शुक्र ग्रह की सतह — जहाँ तापमान सीसा
पिघला देता है. **Series:** Terra Simulation. **Changing variable:** ALTITUDE
(km above surface, descending) or TIME SURVIVED (seconds) — pick TIME.
**Hero:** one probe/human-silhouette descending through Venus clouds
(FLUX still + Wan motion for hook). **Forbidden:** astronaut on Mars-like
red terrain, sci-fi spaceship interiors, Earth deserts posing as Venus.

**Scene skeleton (~6:15):** cold open — lead melting on the surface, "आपके
पास 47 सेकंड हैं" (0:00–0:22) → simulation rules (0:22–0:50) → cloud entry,
sulfuric acid, TIME counter starts (0:50–1:50) → pressure = 900 m ocean
depth, glass card (1:50–2:50) → mid re-hook: "सोवियत यान यहाँ 127 मिनट जीवित
रहा — कैसे?" + map/timeline of Venera (2:50–4:00) → heat mechanism, stat
card 467°C vs kitchen oven (4:00–5:00) → climax: surface, hero's final
seconds, milestone hold (5:00–5:45) → honest answer + limits (5:45–6:05) →
tease next: "लेकिन एक जगह है जहाँ बारिश हीरों की होती है…" (6:05–6:15).

**Sound plan:** ambient bed shifts hook→calm→urgent per delivery; riser into
each milestone; 0.35s silence before the 47-second reveal; SFX on counter
freezes. **Thumbnail concept:** hero silhouette against orange cloud wall,
fiery headline "शुक्र पर 47 सेकंड!", Latin text "47 SECONDS", question chip
"क्यों?". **Five titles:** (1) शुक्र ग्रह पर इंसान: सिर्फ 47 सेकंड की ज़िंदगी
(2) जहाँ बारिश एसिड की और ज़मीन 467°C — शुक्र की सतह पर एक दिन (3) सोवियत यान
शुक्र पर 127 मिनट कैसे जीवित रहा? (4) शुक्र: सौरमंडल का असली नर्क (5) अगर आप
शुक्र ग्रह पर उतर जाएँ तो क्या होगा? **Three shorts:** ① "47 सेकंड" countdown
teaser (funnel to long-form) ② Venera-13's 127 minutes ③ "शुक्र पर 1 दिन =
243 पृथ्वी दिन" loop.

## 7. 30-day roadmap

Week 1: rotate keys; render Venus; publish backlog (2 long + 4 shorts) with
full Studio checklist; set Shorts related-links; create series playlists.
Week 2: hold cadence; first CSVs into `analytics/`; run Update Learnings;
FAILURES.md entries from every watch. Week 3: ship H1 (Wan hero motion) +
H2 (series tagging); first Test & Compare results → thumbnail rule updates.
Week 4: review 4-week retention curves; pick ONE fix the data demands;
decide nothing else.

## 8. 90-day roadmap

Month 2: 16–24 more uploads; scene-level retention analysis via chapters;
raise to 8.5–9 min IF avg-view ≥45%; upload-time test; community-tab polls
seeding next topics. Month 3: Hinglish A/B (2 videos); evaluate English twin
channel; formalize best-performing series as the channel's spine; revisit
"Avoid" list strictly against data. Success criteria at day 90: ≥40 uploads,
CTR ≥4%, avg-view ≥45%, first 1,000 subscribers, learnings loop steering
topics autonomously.

## 9. What stays human — permanently

Watching every video before upload (the only real publish gate) · taste
verdicts into FAILURES.md · topic veto & forced topics · thumbnail pick among
variants · community replies · the Hinglish/English brand decisions ·
interpreting retention curves. Everything else is the machine's job.

---
*Sources: vidIQ/FluxNote CTR & retention benchmarks 2026; Kurzgesagt Medium
(research process); Underknown/What If analyses; fal.ai pricing (Wan 2.5
$0.05/s); YouTube Test & Compare docs; India RPM guides 2026; FactTechz/
GetSetFly public stats. Full links in the session log.*
