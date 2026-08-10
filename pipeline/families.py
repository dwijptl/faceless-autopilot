"""Narrative-intent visual director — 65 universal beat families.

Every visual beat is tagged with ONE family describing what the beat does in
the STORY (never what it depicts): establishing the place, presenting
evidence, showing scale, descending, branching hypotheses, the revelation…
The family decides — before anything is generated — the beat's composition
rule, camera move, media policy (programmatic graphic / AI still / exact
stock) and the transition grammar into it.

This is deliberately NOT the ornament-led approach of other channels:
identity here is camera-led cinematic documentary realism. Parchment
textures, ornamental frames, gold filigree and painting-style prompts are
BANNED (see BANNED_STYLE) and scrubbed from prompts.

Everything in this module is deterministic and fail-open: a beat without a
valid family simply keeps the legacy stock-first behaviour.

docs/VISUAL_DIRECTOR.md holds the full design.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── global identity ────────────────────────────────────────────────────
GLOBAL_STYLE = (
    "cinematic documentary realism, volumetric light, subtle film grain, "
    "dark investigative palette, photographic detail, anamorphic framing, "
    "no text, no captions, no watermarks, no readable human faces")

BANNED_STYLE = ("parchment", "ornamental frame", "gold filigree", "mandala",
                "aura glow", "devotional painting", "sacred", "scroll border")

# camera ids the renderer implements (remotion/src/graphics.tsx FamilyCamera)
CAMERAS = ("push", "pull", "crane_down", "crane_up", "lateral", "tilt_up",
           "tilt_down", "drift", "hold", "orbit")

# transition kinds the renderer maps to presentations (Main.tsx)
TRANSITIONS = ("cut", "dissolve", "fade", "push_down", "push_up", "whip",
               "wipe", "zoom_punch", "hold_push", "match_cut")

# programmatic-graphic kinds the renderer draws for free (graphics.tsx)
PG_KINDS = ("timeline", "scale", "branch", "chart", "cutaway")
SOURCE_POLICIES = ("custom", "primary", "stock")

_PRIMARY_FAMILIES = {
    "document_focus", "photo_examine", "last_known", "legacy",
    "evidence_scan", "specimen_focus",
}
_CUSTOM_FAMILIES = {
    "establish_era", "witness_account", "human_toll", "hands_at_work",
    "reconstruct_scene", "moment_freeze", "before_after", "flashback",
    "absence", "arrival_threshold",
}


@dataclass(frozen=True)
class FamilySpec:
    key: str
    cluster: str
    fn: str                       # story function (docs + planner prompt)
    comp: str                     # composition fragment for AI prompts
    camera: str                   # camera id (CAMERAS)
    media: tuple                  # preference order over ("pg","ai","stock")
    tin: str                      # default transition-in (TRANSITIONS)
    prio: int = 3                 # AI credit priority 1 (hero) .. 5 (never)
    pg: str | None = None         # programmatic kind when media includes "pg"
    kw: tuple = field(default=()) # classifier keywords (english, lowercase)


def _f(key, cluster, fn, comp, camera, media, tin, prio=3, pg=None, kw=()):
    assert camera in CAMERAS, key
    assert tin in TRANSITIONS, key
    assert pg is None or pg in PG_KINDS, key
    return FamilySpec(key, cluster, fn, comp, camera, tuple(media), tin,
                      prio, pg, tuple(kw))


FAMILIES: dict[str, FamilySpec] = {s.key: s for s in [
    # ── A. Orientation & Place ─────────────────────────────────────────
    _f("cold_open_hook", "orientation", "arresting first image that poses the mystery",
       "one dramatic centered subject, heavy negative space, darkness at the "
       "frame edges, a single motivated light source", "push",
       ("ai",), "fade", 1, kw=("hook", "opening", "mystery begins")),
    _f("establish_place", "orientation", "show where we are",
       "wide establishing shot, low horizon, the landmark placed off-center, "
       "atmospheric haze giving depth", "lateral",
       ("stock", "ai"), "dissolve", 4, kw=("location", "region", "landscape",
       "establish", "wide shot", "village", "city", "mountain range")),
    _f("establish_era", "orientation", "ground the time period",
       "period-accurate props and dress in a mid shot, muted archival grade, "
       "faces turned away from camera", "hold",
       ("ai",), "dissolve", 3, kw=("era", "decade", "period", "1950", "1960",
       "historical", "soviet", "vintage")),
    _f("map_locate", "orientation", "pin the story on the globe",
       "top-down cartographic view, glowing route line, dark ocean tones",
       "orbit", ("pg", "stock"), "zoom_punch", 5, pg="chart",
       kw=("map", "coordinates", "located", "border", "geography")),
    _f("approach", "orientation", "move toward the subject",
       "one-point perspective path leading to the subject, foreground "
       "elements framing the way in", "push",
       ("ai", "stock"), "cut", 3, kw=("approach", "toward", "journey to",
       "getting closer", "road to", "trail")),
    _f("arrival_threshold", "orientation", "stand at the boundary or entrance",
       "doorway or edge framing, the subject visible beyond the threshold, "
       "strong light contrast between here and there", "push",
       ("ai",), "cut", 3, kw=("entrance", "gate", "doorway", "threshold",
       "boundary", "edge of")),
    _f("isolation", "orientation", "emphasize remoteness",
       "a tiny subject inside a vast empty field, extreme wide, desaturated "
       "emptiness", "pull",
       ("ai", "stock"), "dissolve", 3, kw=("remote", "isolated", "alone",
       "middle of nowhere", "wilderness", "uninhabited")),
    _f("scale_of_place", "orientation", "the environment dwarfs everything",
       "vertical composition stacking depth planes, colossal natural forms "
       "over a minuscule reference", "tilt_up",
       ("ai",), "wipe", 3, kw=("vast", "immense", "towering", "enormous landscape")),

    # ── B. Movement & Descent ──────────────────────────────────────────
    _f("descend", "movement", "go down",
       "vertical shaft or column with layered depth planes, light fading "
       "with depth", "crane_down",
       ("ai",), "push_down", 2, kw=("descend", "deeper", "down into", "below",
       "sink", "depth of", "meters down", "underground")),
    _f("ascend_return", "movement", "come back up or out",
       "vertical composition with light growing above, the way out visible",
       "crane_up", ("ai",), "push_up", 3, kw=("ascend", "climb", "surface",
       "back up", "emerge", "return")),
    _f("enter_interior", "movement", "cross into an inside space",
       "interior revealed past an aperture, cool exterior light giving way "
       "to warm interior shadow", "push",
       ("ai",), "cut", 3, kw=("inside", "interior", "within", "chamber",
       "cave mouth", "tunnel")),
    _f("traverse", "movement", "journey across terrain",
       "side-scrolling landscape strips with parallax layers", "lateral",
       ("stock", "ai"), "whip", 4, kw=("across", "traverse", "trek", "march",
       "expedition", "crossing")),
    _f("penetrate_layers", "movement", "pass through strata or levels",
       "stacked geological or structural layers with a clean cutaway edge",
       "crane_down", ("pg", "ai"), "push_down", 4, pg="cutaway",
       kw=("layers", "strata", "crust", "levels", "through the")),
    _f("follow_path", "movement", "track a route or trajectory",
       "glowing route line drawn over terrain from above", "lateral",
       ("pg", "stock"), "cut", 5, pg="chart", kw=("route", "path", "trajectory",
       "trail of", "moved from", "travelled")),
    _f("drift", "movement", "weightless ambient float",
       "suspended subject with drifting particulates, soft directionless "
       "light", "drift", ("ai",), "dissolve", 4, kw=("float", "drift",
       "weightless", "suspended", "adrift")),

    # ── C. Evidence & Investigation ────────────────────────────────────
    _f("evidence_reveal", "evidence", "present a physical artifact",
       "single artifact centered on a dark field, one hard key light, "
       "museum-grade presentation", "orbit",
       ("ai",), "cut", 2, kw=("evidence", "artifact", "object found",
       "discovered", "recovered", "clue")),
    _f("evidence_scan", "evidence", "examine across a surface or set",
       "flat-lay or evidence wall of items in ordered rows, raking light",
       "lateral", ("ai",), "cut", 3, kw=("items", "belongings", "collection",
       "scattered", "inventory", "scene of")),
    _f("document_focus", "evidence", "records and archives up close",
       "a document filling the frame under raking light, paper texture and "
       "ink detail, edges falling into shadow", "push",
       ("ai",), "cut", 3, kw=("document", "diary", "report", "records",
       "files", "logbook", "letter", "case file")),
    _f("photo_examine", "evidence", "scrutinize an archival photograph",
       "an old photograph within the frame, silver-gelatin grain, deep "
       "vignette, a region of interest catching the light", "push",
       ("ai",), "cut", 3, kw=("photograph", "photo", "last picture", "camera film",
       "negatives", "snapshot")),
    _f("specimen_focus", "evidence", "the object under study",
       "extreme macro on the specimen, razor-thin depth of field, clinical "
       "dark background", "push",
       ("ai",), "cut", 3, kw=("sample", "specimen", "fragment", "tissue",
       "material", "fabric", "trace")),
    _f("measurement", "evidence", "instruments and readings",
       "a period-accurate instrument with its scale readable, needle or "
       "readout mid-motion", "hold",
       ("pg", "ai"), "cut", 4, pg="chart", kw=("measured", "reading",
       "instrument", "recorded", "temperature of", "radiation", "level of")),
    _f("anomaly_highlight", "evidence", "the thing that does not fit",
       "an ordinary field with ONE element isolated by light while the "
       "surround falls into desaturated shadow", "push",
       ("ai",), "zoom_punch", 2, kw=("strange", "anomaly", "unusual",
       "doesn't fit", "unexplained", "odd", "impossible detail")),
    _f("detail_magnify", "evidence", "push into fine detail",
       "concentric magnification, the detail resolving into unexpected "
       "structure", "push",
       ("ai",), "zoom_punch", 3, kw=("closer", "magnified", "under the microscope",
       "zoom in", "fine detail")),
    _f("reconstruct_scene", "evidence", "recreate what happened",
       "a staged reconstruction, desaturated reenactment grade, figures "
       "faceless or seen from behind", "lateral",
       ("ai",), "dissolve", 3, kw=("that night", "what happened", "reconstruct",
       "the moment", "sequence of events", "recreate")),
    _f("trace_origin", "evidence", "follow evidence backward",
       "a receding trail of markers leading away from camera into haze",
       "pull", ("pg", "ai"), "cut", 4, pg="chart", kw=("origin", "source of",
       "traced back", "came from", "began at")),

    # ── D. Scale & Comparison ──────────────────────────────────────────
    _f("scale_comparison", "scale", "object versus a familiar reference",
       "side-by-side silhouettes with a clean measuring bar, engineering "
       "diagram clarity", "pull",
       ("pg", "ai"), "cut", 4, pg="scale", kw=("as tall as", "compared to",
       "the size of", "times bigger", "equivalent")),
    _f("human_vs_vast", "scale", "a person dwarfed by the phenomenon",
       "small human silhouette low in frame against a colossal subject, "
       "extreme scale contrast", "tilt_up",
       ("ai",), "wipe", 2, kw=("dwarfs", "tiny against", "human scale",
       "stood before", "loomed")),
    _f("macro_to_micro", "scale", "down through magnitudes",
       "nested frames descending in scale, each revealing the next level",
       "push", ("ai",), "zoom_punch", 3, kw=("smaller and smaller", "atomic",
       "microscopic", "molecular")),
    _f("micro_to_macro", "scale", "up through magnitudes",
       "nested frames ascending in scale toward the planetary", "pull",
       ("ai",), "zoom_punch", 3, kw=("bigger picture", "from above", "planet scale",
       "zoom out")),
    _f("before_after", "scale", "the same subject in two states",
       "matched framing of one subject across two eras or states", "hold",
       ("ai",), "wipe", 3, kw=("before", "after", "used to be", "became",
       "transformed", "once was")),
    _f("side_by_side", "scale", "parallel comparison",
       "split-frame with mirrored composition, both halves equally lit",
       "hold", ("pg", "ai"), "wipe", 4, pg="scale", kw=("versus", "both",
       "while the other", "in contrast", "side by side")),
    _f("superimpose", "scale", "overlay two realities",
       "a ghosted overlay of the past over the present-day plate, matched "
       "perspective", "drift",
       ("ai", "stock"), "dissolve", 3, kw=("overlay", "same spot today",
       "where it once", "ghost of")),

    # ── E. Time & Sequence ─────────────────────────────────────────────
    _f("timeline_advance", "time", "move along the chronology",
       "a horizontal chronology with event nodes lighting in order", "lateral",
       ("pg",), "cut", 5, pg="timeline", kw=("timeline", "then", "days later",
       "chronology", "sequence", "date", "february", "january", "hours passed")),
    _f("flashback", "time", "drop into the past",
       "period grade with softened frame edges, memory-like glow in the "
       "highlights", "push",
       ("ai",), "dissolve", 3, kw=("years earlier", "flashback", "back then",
       "long before", "history of")),
    _f("decay_lapse", "time", "deterioration over time",
       "one fixed framing, the subject weathering and decaying in stages",
       "hold", ("ai",), "dissolve", 3, kw=("decay", "rust", "crumble", "abandoned",
       "eroded", "faded over")),
    _f("build_lapse", "time", "accumulation or growth",
       "one fixed framing, the subject accreting and growing in stages",
       "hold", ("ai",), "dissolve", 4, kw=("grew", "built up", "accumulated",
       "constructed", "expanded")),
    _f("countdown", "time", "approach a critical moment",
       "a prominent clock, date stamp or gauge with the subject behind it",
       "push", ("pg", "ai"), "cut", 4, pg="chart", kw=("countdown", "minutes left",
       "final hours", "deadline", "clock", "ticking")),
    _f("moment_freeze", "time", "the critical instant held",
       "high-detail frozen action, particles suspended mid-air, absolute "
       "stillness", "hold",
       ("ai",), "match_cut", 2, kw=("that instant", "frozen", "the exact moment",
       "split second", "suddenly")),
    _f("era_shift", "time", "jump between periods",
       "the same location match-framed in two different eras", "hold",
       ("ai",), "match_cut", 3, kw=("today", "decades later", "modern day",
       "now the same", "centuries")),

    # ── F. Mechanism & Explanation ─────────────────────────────────────
    _f("mechanism_cutaway", "mechanism", "how it works inside",
       "technical cross-section with clean labeled zones, engineering "
       "illustration over darkness", "lateral",
       ("pg", "ai"), "wipe", 4, pg="cutaway", kw=("mechanism", "how it works",
       "inside the", "cross section", "internal")),
    _f("cause_chain", "mechanism", "one thing leads to another",
       "connected nodes with directional flow, each cause igniting the next",
       "lateral", ("pg",), "cut", 5, pg="branch", kw=("caused", "led to",
       "because", "as a result", "chain of", "triggered")),
    _f("force_visualize", "mechanism", "invisible forces made visible",
       "field lines or waves rendered over a realistic scene, energy made "
       "luminous", "drift",
       ("pg", "ai"), "wipe", 4, pg="cutaway", kw=("pressure", "waves", "force",
       "magnetic", "wind", "current", "infrasound", "vibration")),
    _f("process_cycle", "mechanism", "a repeating system",
       "circular loop layout, stages orbiting a center", "orbit",
       ("pg",), "cut", 5, pg="branch", kw=("cycle", "repeats", "loop",
       "again and again", "seasonal")),
    _f("simulation", "mechanism", "a model of what would happen",
       "wireframe hologram grade, a simulated world rendered in light",
       "drift", ("pg", "ai"), "dissolve", 4, pg="cutaway", kw=("simulation",
       "model shows", "computed", "would happen", "predicted")),
    _f("cross_section", "mechanism", "the sliced-open view",
       "a clean cut-plane through the subject revealing interior strata",
       "push", ("pg", "ai"), "wipe", 4, pg="cutaway", kw=("beneath the surface",
       "under the", "interior of", "what lies below")),
    _f("data_story", "mechanism", "a chart that carries narrative",
       "one dominant data visual on a cinematic dark field, values drawing "
       "themselves", "push",
       ("pg",), "cut", 5, pg="chart", kw=("percent", "statistics", "the numbers",
       "data shows", "graph", "rate of")),

    # ── G. Hypothesis & Tension ────────────────────────────────────────
    _f("question_pose", "hypothesis", "the open question visualized",
       "the subject engulfed by negative space, darkness holding the "
       "unanswered question", "pull",
       ("ai",), "fade", 2, kw=("why", "how could", "no one knows", "question",
       "remains unanswered", "but what")),
    _f("hypothesis_branch", "hypothesis", "competing explanations",
       "one evidence node splitting into distinct branches of possibility",
       "pull", ("pg",), "cut", 5, pg="branch", kw=("theories", "explanations",
       "one possibility", "some believe", "three reasons", "hypothesis")),
    _f("hypothesis_test", "hypothesis", "a theory tried against evidence",
       "split composition: the theory rendered on one side, the hard "
       "evidence on the other", "push",
       ("ai",), "wipe", 3, kw=("tested", "if that were true", "against the evidence",
       "would explain", "checked")),
    _f("hypothesis_collapse", "hypothesis", "a theory eliminated",
       "a branch of possibility graying out and crumbling while the rest "
       "remain lit", "lateral",
       ("pg",), "cut", 5, pg="branch", kw=("ruled out", "debunked", "cannot explain",
       "falls apart", "eliminated", "doesn't add up")),
    _f("contradiction", "hypothesis", "two facts that cannot both be true",
       "two opposing frames colliding at the center line, equal weight",
       "push", ("ai",), "zoom_punch", 2, kw=("contradiction", "yet",
       "impossible because", "makes no sense", "but the evidence")),
    _f("red_herring", "hypothesis", "the misleading clue",
       "a clue lit attractively but framed subtly off-balance, something "
       "quietly wrong", "push",
       ("ai",), "cut", 3, kw=("seemed like", "at first", "everyone assumed",
       "apparent answer", "too obvious")),
    _f("dead_end", "hypothesis", "the trail goes cold",
       "a path terminating in void or fog, momentum dying", "push",
       ("ai",), "cut", 3, kw=("trail went cold", "dead end", "no further",
       "vanished", "nothing more", "stopped there")),
    _f("suspicion_shift", "hypothesis", "attention moves to a new cause",
       "light physically sweeping from one subject to another across a dark "
       "field", "lateral",
       ("ai",), "whip", 3, kw=("but then", "attention turned", "new suspect",
       "another explanation", "shifted to")),

    # ── H. Human Element ───────────────────────────────────────────────
    _f("witness_account", "human", "the person who saw it",
       "environmental portrait with the face turned away or in shadow, the "
       "environment telling their story", "push",
       ("ai",), "dissolve", 3, kw=("witness", "survivor", "the last person",
       "recalled", "testified", "saw it")),
    _f("human_toll", "human", "the cost to people",
       "personal objects and empty spaces at intimate scale, absence heavy "
       "in the frame", "hold",
       ("ai",), "fade", 2, kw=("families", "loved ones", "the victims", "grief",
       "never came home", "lives lost")),
    _f("hands_at_work", "human", "craft and labor detail",
       "close on hands and tools mid-task, work-worn detail, warm practical "
       "light", "lateral",
       ("ai", "stock"), "cut", 4, kw=("built by hand", "craftsmen", "workers",
       "assembled", "dug", "carved")),
    _f("last_known", "human", "the final trace",
       "the last photograph, log entry or signal, timestamp weight, "
       "everything after it unknown", "push",
       ("ai",), "cut", 2, kw=("last known", "final entry", "last seen",
       "final photograph", "last signal", "final words")),
    _f("absence", "human", "the space where something was",
       "negative space where the subject should stand, a faint outline or "
       "indentation remaining", "push",
       ("ai",), "fade", 2, kw=("empty", "gone", "missing", "no trace",
       "never found", "deserted")),

    # ── I. Revelation & Resolution ─────────────────────────────────────
    _f("revelation", "revelation", "the big reveal",
       "the subject fully lit for the first time, symmetrical monumental "
       "framing", "push",
       ("ai",), "hold_push", 1, kw=("the truth", "revealed", "the answer",
       "turned out", "discovery", "finally understood")),
    _f("twist", "revelation", "reversal of understanding",
       "an earlier composition recontextualized by one new element in frame",
       "push", ("ai",), "match_cut", 1, kw=("twist", "everything changed",
       "wrong all along", "the opposite", "in fact")),
    _f("partial_answer", "revelation", "some resolution, not all",
       "the subject half-lit, half surrendered to shadow", "push",
       ("ai",), "dissolve", 3, kw=("partly", "some answers", "explains some",
       "not the whole story", "half the truth")),
    _f("lingering_question", "revelation", "the unresolved ending",
       "a vast frame with the subject receding into distance and dark",
       "pull", ("ai",), "fade", 2, kw=("still unknown", "to this day", "may never know",
       "mystery remains", "unanswered")),
    _f("legacy", "revelation", "what remains today",
       "the present-day state of the subject in a modern documentary grade",
       "drift", ("stock", "ai"), "dissolve", 4, kw=("today", "still stands",
       "remains", "legacy", "monument", "memorial")),
    _f("haunting_echo", "revelation", "the final atmospheric note",
       "a minimal near-abstract detail, almost still, sound made visible",
       "hold", ("ai",), "fade", 3, kw=("echo", "silence", "wind still", "haunting",
       "if you listen")),
]}

assert len(FAMILIES) == 65, f"expected 65 families, got {len(FAMILIES)}"


# ── domain style packs (layer 2 — styling only, never structure) ───────
@dataclass(frozen=True)
class DomainPack:
    key: str
    flavor: str          # prompt fragment appended after the composition
    kw: tuple            # topic keywords for auto-selection


DOMAIN_PACKS: dict[str, DomainPack] = {p.key: p for p in [
    DomainPack("deep_earth",
               "geological texture, mineral tones of basalt and iron oxide, "
               "heat shimmer in the depths, industrial-scientific hardware",
               ("borehole", "cave", "underground", "volcano", "geology",
                "crust", "mantle", "mine", "drilling", "earthquake")),
    DomainPack("archival_historical",
               "muted archival palette, weathered materials, cold-war era "
               "textures, snow and pine where exterior, tungsten where interior",
               ("1950", "1959", "1960", "1970", "soviet", "expedition",
                "historical", "archive", "cold war", "vintage", "hikers",
                "colony", "ancient", "ruins")),
    DomainPack("ocean",
               "deep water light attenuation, marine snow particulate, "
               "pressure-hull and sonar hardware, bioluminescent accents",
               ("ocean", "sea", "ship", "underwater", "trench", "marine",
                "wreck", "submarine", "abyss", "tide")),
    DomainPack("space",
               "hard vacuum light with no atmospheric diffusion, starfield "
               "depth, spacecraft and radio-telescope hardware",
               ("space", "signal", "planet", "orbit", "cosmic", "telescope",
                "star", "satellite", "galaxy", "asteroid")),
    DomainPack("forensic",
               "clinical case-file lighting, evidence-table neutrality, "
               "measured procedural framing",
               ("investigation", "case", "police", "forensic", "autopsy",
                "detective", "crime scene", "inquiry")),
]}


# ── transition pair grammar ────────────────────────────────────────────
# (prev_family_or_cluster, next_family_or_cluster) -> transition kind.
# "*" matches anything; python resolves most-specific first.
PAIR_GRAMMAR: dict[tuple, str] = {
    ("descend", "descend"): "continue",           # one unbroken move
    ("timeline_advance", "timeline_advance"): "continue",
    ("*", "revelation"): "hold_push",             # silence beat, then push
    ("evidence", "hypothesis_branch"): "zoom_punch",
    ("contradiction", "hypothesis_collapse"): "wipe",
    ("map_locate", "establish_place"): "zoom_punch",
    ("moment_freeze", "*"): "cut",                # exhale cut
    ("red_herring", "dead_end"): "whip",
    ("red_herring", "suspicion_shift"): "whip",
    ("era_shift", "*"): "match_cut",
    ("*", "twist"): "match_cut",
}

# transitions considered high-energy for the pacing cap
HIGH_ENERGY = {"whip", "zoom_punch", "hold_push", "match_cut"}


def get_spec(family: str | None) -> FamilySpec | None:
    return FAMILIES.get(str(family or "").strip().lower().replace("-", "_"))


def transition_for(prev_family: str | None, next_family: str | None) -> str:
    """Pair grammar lookup: exact pair > cluster pair > wildcard > default."""
    ns = get_spec(next_family)
    if ns is None:
        return "dissolve"
    ps = get_spec(prev_family)
    pk = ps.key if ps else ""
    pc = ps.cluster if ps else ""
    for a in (pk, pc, "*"):
        for b in (ns.key, ns.cluster, "*"):
            if (a, b) == ("*", "*"):
                continue
            kind = PAIR_GRAMMAR.get((a, b))
            if kind:
                return kind
    return ns.tin


def plan_scene_transitions(scenes: list[dict],
                           min_gap_seconds: float = 20.0) -> None:
    """Attach {kind} to every scene from the pair grammar, enforcing the
    high-energy pacing cap (max one energetic cut per ~min_gap_seconds).
    Mutates scenes in place; scenes without families keep legacy behaviour."""
    last_energy_at = -1e9
    clock = 0.0
    prev_family = None
    for sc in scenes:
        beats = sc.get("visual_beats") or []
        first = next((b.get("family") for b in beats if b.get("family")), None)
        last = next((b.get("family") for b in reversed(beats)
                     if b.get("family")), first)
        if first:
            kind = transition_for(prev_family, first)
            if kind == "continue":
                kind = "cut"
            if kind in HIGH_ENERGY and clock - last_energy_at < min_gap_seconds:
                kind = "dissolve" if kind == "hold_push" else "cut"
            if kind in HIGH_ENERGY:
                last_energy_at = clock
            sc["family_transition"] = kind
            sc["family"] = first
        prev_family = last or prev_family
        clock += float(sc.get("audio_duration", 0.0))


# ── deterministic classifier (fallback when the LLM omits families) ────
_WORD = re.compile(r"[a-z0-9]+")


def classify(text: str) -> str | None:
    """Keyword-score `text` (english purpose/search-terms) against families.
    Returns the best family key, or None when nothing matches (legacy path)."""
    t = " " + " ".join(_WORD.findall(str(text or "").lower())) + " "
    best, best_score = None, 0
    for spec in FAMILIES.values():
        score = sum(len(k) for k in spec.kw if f" {k} " in t or k in t)
        if score > best_score:
            best, best_score = spec.key, score
    return best


def classify_beat(beat: dict, scene: dict, scene_index: int, beat_index: int,
                  n_scenes: int) -> str | None:
    """Positional priors + keyword classification for one beat."""
    if scene_index == 0 and beat_index == 0:
        return "cold_open_hook"
    text = " ".join([str(beat.get("purpose", "")),
                     " ".join(beat.get("search_terms") or []),
                     str(scene.get("title", ""))])
    found = classify(text)
    if found:
        return found
    if str(scene.get("delivery", "")).lower() == "reveal" and beat_index == 0:
        return "revelation"
    if scene_index == n_scenes - 1:
        beats = scene.get("visual_beats") or []
        if beat_index == max(len(beats) - 1, 0):
            return "lingering_question"
    return None


def pick_domain_pack(topic: str, script: dict | None = None) -> str:
    """Choose a style pack from topic + search-term vocabulary."""
    corpus = [str(topic or "")]
    for sc in (script or {}).get("scenes", []):
        corpus += [str(t) for t in sc.get("search_terms") or []]
    t = " ".join(corpus).lower()
    best, best_score = "archival_historical", 0
    for pack in DOMAIN_PACKS.values():
        score = sum(1 for k in pack.kw if k in t)
        if score > best_score:
            best, best_score = pack.key, score
    return best


# ── prompt composition ─────────────────────────────────────────────────
def compose_prompt(subject: str, family: str | None,
                   pack_key: str | None = None) -> str:
    """Subject + family composition + domain flavor + global identity.
    Scrubs banned ornament vocabulary so the identity stays camera-led."""
    spec = get_spec(family)
    pack = DOMAIN_PACKS.get(str(pack_key or ""))
    parts = [str(subject or "").strip().rstrip(".")]
    if spec:
        parts.append(spec.comp)
    if pack:
        parts.append(pack.flavor)
    parts.append(GLOBAL_STYLE)
    prompt = ". ".join(p for p in parts if p)
    for banned in BANNED_STYLE:
        prompt = re.sub(re.escape(banned), "", prompt, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", prompt).strip()


# ── media policy / budgets ─────────────────────────────────────────────
def director_cfg(cfg: dict) -> dict:
    return (cfg or {}).get("visual_director", {}) or {}


def enabled(cfg: dict) -> bool:
    return bool(director_cfg(cfg).get("enabled", False))


def ai_still_budget(cfg: dict) -> int:
    vd = director_cfg(cfg)
    mode = str(vd.get("mode", "economy")).lower()
    modes = vd.get("modes") or {}
    fallback = {"economy": 18, "balanced": 28, "premium": 36}
    try:
        return int((modes.get(mode) or {}).get(
            "ai_stills", fallback.get(mode, 18)))
    except (TypeError, ValueError):
        return fallback.get(mode, 18)


def wants(family: str | None, medium: str) -> bool:
    spec = get_spec(family)
    return bool(spec and medium in spec.media)


def media_order(family: str | None) -> tuple:
    spec = get_spec(family)
    return spec.media if spec else ("stock",)


def source_policy(beat: dict, scene: dict | None = None) -> str:
    """Truth-first source policy for a beat, with deterministic fallback."""
    explicit = str((beat or {}).get("source_policy", "")).strip().lower()
    if explicit in SOURCE_POLICIES:
        return explicit
    family = str((beat or {}).get("family", ""))
    if str((scene or {}).get("visual_mode", "")) == "evidence":
        return "primary"
    if family in _PRIMARY_FAMILIES:
        return "primary"
    if family in _CUSTOM_FAMILIES:
        return "custom"
    return "stock"


def credit_rank(family: str | None) -> int:
    spec = get_spec(family)
    return spec.prio if spec else 5


def allocate_ai(scenes: list[dict], budget: int) -> int:
    """Grant the per-video AI-still budget to the highest-priority beats.

    Without this pre-pass a sequential scene loop would spend every credit on
    early filler beats and leave the revelation with a gradient card. Beats
    whose family PREFERS ai (media[0] == "ai") outrank ai-fallback beats of
    the same priority. Marks `ai_grant: True` on winning beats in place and
    returns the number of grants made."""
    candidates = []
    for si, sc in enumerate(scenes):
        for bi, beat in enumerate(sc.get("visual_beats") or []):
            spec = get_spec(beat.get("family"))
            policy = source_policy(beat, sc)
            beat["source_policy"] = policy
            if policy == "primary":
                continue
            custom = policy == "custom"
            if custom and (not spec or spec.media[0] != "pg"):
                prio = spec.prio if spec else 3
                candidates.append((0, prio, 0, si, bi, beat))
            elif spec and "ai" in spec.media:
                ai_first = 0 if spec.media[0] == "ai" else 1
                candidates.append((1, spec.prio, ai_first, si, bi, beat))
    candidates.sort(key=lambda c: c[:-1])
    granted = candidates[:max(int(budget), 0)]
    for *_, beat in granted:
        beat["ai_grant"] = True
    return len(granted)


def prompt_hint_lines() -> str:
    """Compact family menu for the LLM beat planner (one line per cluster)."""
    by_cluster: dict[str, list[str]] = {}
    for spec in FAMILIES.values():
        by_cluster.setdefault(spec.cluster, []).append(spec.key)
    return "\n".join(f"- {cluster}: {', '.join(keys)}"
                     for cluster, keys in by_cluster.items())
