# Faceless Visual Director — Narrative-Intent System (Design v1)

A visual-directing brain for `faceless-autopilot`: every narration sentence gets a directed visual with intent decided *before* anything is generated. Same core idea as Sanatan (no undirected filler), but a different architecture, a different identity, and a much larger universal vocabulary — **65 narrative-intent families**.

---

## 1. How this is deliberately NOT the Sanatan system

| Dimension | Sanatan | Faceless |
|---|---|---|
| Identity | Ornament-led: parchment, devotional painting, gold, mandala, aura | Camera-led: cinematic documentary realism, volumetric light, film grain, dark investigative palette |
| Vocabulary | ~12 composition families bound to one domain forever | 65 **universal** narrative-intent families + swappable domain style packs |
| When intent is decided | Treatment assigned to an image after it exists | Intent decided **before** the prompt is written — prompt, composition, and camera are co-designed from the family |
| Transitions | Per-beat decorative (paper, ink, texture) | **Pair grammar**: (previous family → next family) determines the cut |
| Motion | Ken Burns-style pans over paintings | Directed camera moves: vertical cranes, parallax planes, scan pans, match cuts, dead holds |
| Graphics | Minimal, decorative | First-class media type: programmatic maps / timelines / cutaways / charts, not a fallback |
| Banned in Faceless | — | Parchment textures, ornamental frames, gold filigree, glows/auras, painting-style prompts |

The point: Sanatan decorates a sacred story; Faceless **investigates** a factual one. The system's job is to make every shot feel like a piece of an investigation, not an illustration.

---

## 2. Architecture

```
Narration sentence
   ↓
Intent classifier → exactly ONE family + intensity (1–3)
   ↓
Family spec → composition rules + camera move + media policy + transition-in
   ↓
Media resolver → AI still | programmatic graphic | exact stock | archival treatment
   ↓
Prompt builder (for AI) or graphic generator (for programmatic)
   ↓
Remotion renders the family's camera move
   ↓
Transition chosen from the pair grammar (prev family → this family)
```

**Layer 1 — 65 narrative-intent families.** Universal. Describe what the beat *does in the story*, never what it depicts. Never rewritten per topic.

**Layer 2 — domain style packs.** Thin styling layer only: palette, texture, prop vocabulary, prompt flavor. Launch packs: `deep-earth`, `archival-historical`. Later: `ocean`, `space`, `forensic`. A family + a pack fully determines the look.

---

## 3. The 65 families

Column key — **Function**: what the beat does in the story. **Composition**: framing rule fed into the prompt/graphic. **Camera**: the Remotion move. **Media**: preferred source (AI = paid still, PG = programmatic graphic, ST = exact-subject stock).

### A. Orientation & Place (8)

| # | Family | Function | Composition | Camera | Media |
|---|---|---|---|---|---|
| 1 | `cold-open-hook` | Arresting first image that poses the mystery | Centered subject, heavy negative space, darkness at edges | Slow push-in from black | AI (hero) |
| 2 | `establish-place` | Show where we are | Wide, low horizon, landmark off-center | Slow lateral drift | ST if real, else AI |
| 3 | `establish-era` | Ground the time period | Period props/dress mid-shot, muted grade | Static + micro-drift | AI (archival grade) |
| 4 | `map-locate` | Pin the story on the globe | Top-down cartographic frame, route line | Orbital zoom globe → region | PG map |
| 5 | `approach` | Move toward the subject | One-point perspective path to subject | Forward dolly | AI + parallax |
| 6 | `arrival-threshold` | Stand at the boundary/entrance | Doorway/edge framing, subject beyond | Push through the frame edge | AI |
| 7 | `isolation` | Emphasize remoteness | Tiny subject in a vast empty field | Slow pull-back | AI |
| 8 | `scale-of-place` | Environment dwarfs everything | Vertical stack of depth planes | Vertical tilt | AI |

### B. Movement & Descent (7)

| # | Family | Function | Composition | Camera | Media |
|---|---|---|---|---|---|
| 9 | `descend` | Go down | Vertical shaft/column, layered depth | Vertical crane down | AI multi-plane |
| 10 | `ascend-return` | Come back up/out | Descend mirrored, light growing above | Vertical crane up | AI multi-plane |
| 11 | `enter-interior` | Cross into an inside space | Interior revealed past an aperture | Push through opening | AI |
| 12 | `traverse` | Journey across terrain | Side-scrolling landscape strips | Lateral track | AI or ST |
| 13 | `penetrate-layers` | Pass through strata/levels | Stacked layers with cutaway edge | Continuous descent through layers | PG cutaway |
| 14 | `follow-path` | Track a route/trajectory | Route line over terrain | Camera follows the drawn path | PG map |
| 15 | `drift` | Weightless ambient float | Suspended subject, particulates | Slow 3-axis drift | AI + particles |

### C. Evidence & Investigation (10)

| # | Family | Function | Composition | Camera | Media |
|---|---|---|---|---|---|
| 16 | `evidence-reveal` | Present a physical artifact | Artifact centered on dark field, single key light | Slow orbit or push | AI |
| 17 | `evidence-scan` | Examine across a surface/set | Flat-lay or evidence wall | Scan pan L→R | AI |
| 18 | `document-focus` | Records/archives up close | Document fills frame, raking light | Rack-focus + slow push | AI (archival) |
| 19 | `photo-examine` | Scrutinize an archival photo | Photo-within-frame, grain, vignette | Zoom into one region of the photo | AI (period-photo) |
| 20 | `specimen-focus` | Object under study | Macro, shallow depth of field | Micro push | AI |
| 21 | `measurement` | Instruments and readings | Instrument + scale, live readout | Hold; needle/number animates | PG overlay on AI |
| 22 | `anomaly-highlight` | The thing that doesn't fit | Normal field; one element isolated by light | Push to anomaly, desaturate surround | AI + overlay |
| 23 | `detail-magnify` | Push into fine detail | Concentric magnification steps | Step zoom ×2 → ×10 → ×100 | AI chain |
| 24 | `reconstruct-scene` | Recreate what happened | Staged scene, desaturated "reenactment" grade | Slow lateral track | AI sequence |
| 25 | `trace-origin` | Follow evidence backward | Reverse path with receding markers | Reverse dolly | PG path over stills |

### D. Scale & Comparison (7)

| # | Family | Function | Composition | Camera | Media |
|---|---|---|---|---|---|
| 26 | `scale-comparison` | Object vs familiar reference | Side-by-side silhouettes + measure bar | Pull-back revealing the reference | PG diagram |
| 27 | `human-vs-vast` | Person dwarfed by phenomenon | Human silhouette low in frame vs colossal subject | Slow tilt up | AI |
| 28 | `macro-to-micro` | Down through magnitudes | Nested scale frames | Continuous zoom-in chain | AI chain |
| 29 | `micro-to-macro` | Up through magnitudes | Reversed nesting | Continuous zoom-out chain | AI chain |
| 30 | `before-after` | Same subject, two states | Matched framing across two eras | Hold, then wipe between states | AI pair |
| 31 | `side-by-side` | Parallel comparison | Split frame, mirrored composition | Both halves drift subtly | Mixed |
| 32 | `superimpose` | Overlay two realities | Ghost overlay on a present-day plate | Cross-opacity drift | AI + ST plate |

### E. Time & Sequence (7)

| # | Family | Function | Composition | Camera | Media |
|---|---|---|---|---|---|
| 33 | `timeline-advance` | Move along chronology | Horizontal track with event nodes | Lateral track along timeline | PG timeline |
| 34 | `flashback` | Drop into the past | Period grade, softened edges | Push through defocus | AI |
| 35 | `decay-lapse` | Deterioration over time | Fixed frame; subject degrades in steps | Static; subject morphs | AI sequence |
| 36 | `build-lapse` | Accumulation/growth | Fixed frame; subject accretes in steps | Static; subject morphs | AI sequence |
| 37 | `countdown` | Approach a critical moment | Clock/date/percentage prominent | Push-in as numbers change | PG overlay |
| 38 | `moment-freeze` | Critical instant held | High-detail frozen action, suspended particles | Dead hold | AI |
| 39 | `era-shift` | Jump between periods | Same location, two eras, match-framed | Match-cut whip | AI pair |

### F. Mechanism & Explanation (7)

| # | Family | Function | Composition | Camera | Media |
|---|---|---|---|---|---|
| 40 | `mechanism-cutaway` | How it works inside | Cross-section with labeled parts | Slow pan across the cutaway | PG cutaway |
| 41 | `cause-chain` | One thing leads to another | Nodes joined by animated arrows | Camera follows the chain | PG diagram |
| 42 | `force-visualize` | Invisible forces made visible | Field lines/waves over a realistic scene | Waves propagate through frame | PG over AI |
| 43 | `process-cycle` | A repeating system | Circular loop layout | Orbital move around the loop | PG diagram |
| 44 | `simulation` | Model of what would happen | Wireframe/hologram grade | Camera inside the sim space | PG |
| 45 | `cross-section` | Sliced-open view of anything | Cut-plane framing | Push along the cut plane | PG cutaway |
| 46 | `data-story` | A chart that carries narrative | One dominant chart, cinematic dark theme | Value-draw animation + push | PG chart |

### G. Hypothesis & Tension (8)

| # | Family | Function | Composition | Camera | Media |
|---|---|---|---|---|---|
| 47 | `question-pose` | The open question, visualized | Subject + engulfing negative space | Slow pull-back into emptiness | AI |
| 48 | `hypothesis-branch` | Competing explanations | One evidence node splitting into N branches | Pull-back revealing branches | PG diagram |
| 49 | `hypothesis-test` | A theory tried against evidence | Split: theory visual vs evidence visual | Cross-cutting push-ins | Mixed |
| 50 | `hypothesis-collapse` | A theory eliminated | Branch grays out / crumbles | Push past the dead branch | PG diagram |
| 51 | `contradiction` | Two facts that can't both be true | Two frames colliding at center | Both push toward center | AI pair |
| 52 | `red-herring` | The misleading clue | Clue lit attractively, subtly wrong | Confident push, then drift off-center | AI |
| 53 | `dead-end` | The trail goes cold | Path terminating in void/fog | Forward dolly decelerating to a stop | AI |
| 54 | `suspicion-shift` | Attention moves to a new cause | Light physically moves between subjects | Lateral light-sweep pan | AI |

### H. Human Element (5)

| # | Family | Function | Composition | Camera | Media |
|---|---|---|---|---|---|
| 55 | `witness-account` | The person who saw it | Environmental portrait, face obscured/turned (faceless channel rule) | Slow push to shoulder height | AI |
| 56 | `human-toll` | The cost to people | Personal objects, empty rooms, small scale | Static + micro-drift | AI |
| 57 | `hands-at-work` | Craft/labor detail | Close on hands and tools | Macro lateral track | AI or ST |
| 58 | `last-known` | Final trace of a person/thing | The last photo/log/signal + timestamp | Push-in, then freeze | AI + overlay |
| 59 | `absence` | The space where something was | Negative space with a silhouette hint | Slow push into emptiness | AI |

### I. Revelation & Resolution (6)

| # | Family | Function | Composition | Camera | Media |
|---|---|---|---|---|---|
| 60 | `revelation` | The big reveal | Subject fully lit for the first time, symmetrical | Held beat → strong push | AI (hero) |
| 61 | `twist` | Reversal of understanding | An earlier frame recontextualized | Re-run the earlier camera move with the new element | AI (variant of earlier beat) |
| 62 | `partial-answer` | Some resolution, not all | Subject half-lit, half in shadow | Push that stops short | AI |
| 63 | `lingering-question` | The unresolved ending | Vast frame, subject receding | Long pull-back | AI |
| 64 | `legacy` | What remains today | Present-day state, modern grade | Slow drift | ST if real, else AI |
| 65 | `haunting-echo` | Final atmospheric note | Minimal, near-abstract detail | Barely-moving hold | AI |

---

## 4. Transition pair grammar

Default rule: use the incoming family's natural entry (push, wipe, dissolve, cut). Pair overrides — where the *combination* of previous → next family changes the cut:

| From → To | Transition |
|---|---|
| `descend` → `descend` | One continuous downward move — never reset the camera |
| `timeline-advance` → `timeline-advance` | A single uninterrupted sweep |
| anything → `revelation` | ~12-frame dead hold (silence beat), then hard push |
| `evidence-*` → `hypothesis-branch` | The evidence frame shrinks into a branch node |
| `contradiction` → `hypothesis-collapse` | The collision resolves into a gray-out |
| `map-locate` → `establish-place` | Zoom continues from map straight into real terrain (map-to-terrain morph) |
| `moment-freeze` → anything | Exhale cut — motion resumes on the next shot |
| `red-herring` → `dead-end` / `suspicion-shift` | Overshoot momentum carries into the next shot |
| `era-shift` → anything | Match cut on shared shape/position |

Global caps: at most **one high-energy transition per ~20 seconds**; calm explanatory runs default to plain cuts and short dissolves. Transitions are never chosen for decoration — only the grammar picks them.

---

## 5. Media policy

- **Stock (ST)**: only when it shows the *exact real subject* — the real place, real archival footage, real equipment. Never texture filler, never "a scientist in a lab." This kills the random-clip feeling.
- **Programmatic graphics (PG)**: first-class citizens, zero API cost. All map / timeline / chart / cutaway / diagram / measurement families never spend image credits. Rendered by Remotion components + Python data prep on the runner.
- **AI stills**: economy budget 15–20 per episode. Credit priority when the budget is tight: `cold-open-hook`, `revelation`, `twist`, `human-vs-vast`, `evidence-reveal`, `descend`, `question-pose` — lower-priority families reuse crops/variants of already-generated stills.
- **AI video**: 0–2 clips max; only `cold-open-hook` and `revelation` are eligible.

Quality modes: `economy` (15–20 AI stills, no AI video), `balanced` (25–30 stills, 1 AI video), `premium` (35+, 2 AI videos). Same families and grammar in all modes — only the media resolver's budget changes.

---

## 6. Intensity

The classifier tags every beat with intensity 1–3. Intensity scales camera speed, transition energy, and sound-design weight — not the family itself. Cap: at most one intensity-3 beat per ~45 seconds, so reveals still land.

---

## 7. Semantic QC (replaces checkbox coverage)

1. **Fact match**: does the visual depict the actual stated fact — number, size, era, place? (The 23 cm borehole shown as a walkable cavern is an auto-fail.)
2. **Pack match**: the domain style pack must match the topic. No deep-earth textures in an ocean story.
3. **Anti-generic**: if the shot would fit *any* video on this topic, reject and re-prompt using the family's composition rule.
4. **Repetition guard**: the same family at most twice consecutively, except `descend`/`timeline-advance` chains.
5. **Faceless rule**: no readable human faces in AI stills (`witness-account` composes around it).

---

## 8. Implementation order in `faceless-autopilot`

1. `intent_classifier` — sentence → (family, intensity); extends the existing per-sentence planner in `script_gen.py`.
2. `families.py` — the 65 specs: composition prompt fragments, camera params, media policy, transition-in, credit priority.
3. `media_resolver` — replaces the stock-first logic in `assets.py` with the policy in §5.
4. Programmatic renderers — map, timeline, cutaway, chart, diagram Remotion components.
5. Transition pair grammar in the renderer.
6. Semantic QC rewrite in `quality_report.py` per §7.
7. A/B test — render one full episode on the chosen test topic and compare against the current pipeline's output.

---

## 9. A/B test topic

To be chosen — a deliberately *different* mystery from Kola, so the test exercises the clusters Kola never touches (Evidence, Hypothesis & Tension, Human Element) rather than re-testing descent and scale. Candidates: Dyatlov Pass, the Wow! signal, the Mary Celeste, Roanoke.

