"""Topic shape: does this promise ONE claim, or a journey of checkpoints?

Measured cause of the worst-retaining Shorts on the channel (analytics window
2026-06-26 .. 2026-07-23). `pick_topic` scored every candidate on the VISUAL
JOURNEY TEST — a long-form rubric that explicitly rewards "6+ visibly
escalating milestones" — and `run_short.py` called the same function, then
compressed the winner into a 40-55s band.

The result is in the numbers. Eight of eleven published Shorts carried a
checkpoint promise ("हर 5 मिनट", "हर 100 मीटर", "हर मिनट"); every one of them
retained under 40% of its own runtime. The three single-claim Shorts retained
58%, 104% and 185% (the last two loop — viewers replayed them).

    24s  "11,034 मीटर ... 1 घंटा — हर मिनट शरीर का क्या हाल होगा?"    15.0%
    78s  "मंगल पर पहला कदम: आपके शरीर के पास सिर्फ 90 सेकंड हैं"      11.3%
    83s  "NASA को पृथ्वी के अंदर से एक अजीब सिग्नल मिला"             185.5%
    21s  "गायब होते द्वीप: नक्शे का सबसे बड़ा रहस्य?"                104.4%

A checkpoint promise is not a bad topic — it is a LONG-FORM topic. This module
tells the two apart so each is routed to the format that can actually pay it
off, and so a title can never promise N checkpoints the runtime cannot deliver.

Pure functions, no LLM, no I/O — same contract as retention_lint.
"""
import re

SINGLE_CLAIM = "single_claim"
CHECKPOINT_JOURNEY = "checkpoint_journey"
SHAPES = (SINGLE_CLAIM, CHECKPOINT_JOURNEY)

# When a checkpoint promise is detected but its arithmetic can't be recovered
# ("मिनट दर मिनट", "step by step"), assume this many beats.
DEFAULT_BEATS = 5
MAX_BEATS = 24          # clamp: "हर 1 मिनट over 1 घंटा" is 60, which is noise
MIN_BEATS = 2

# Runtime a promise needs: a fixed setup/payoff cost plus per-checkpoint time.
# Calibrated against the two Shorts that DID pay off their promise — the 83s
# single-claim (0 beats) and the 68s alien-visitor (0 beats) — plus long-form
# Mariana Trench (279s, ~6 beats, 45.4% retention, the best long-form).
BASE_SECONDS = 14.0
SECONDS_PER_BEAT = 11.0

_NUM = r"(\d[\d,\.]*)"

# "हर 5 मिनट", "हर 100 मीटर", "हर 10,000 मीटर", "हर 1000 किमी"
_HI_STEP = re.compile(r"हर\s+" + _NUM + r"\s*(मिनट|सेकंड|घंट|मीटर|किमी|किलोमीटर|साल|चरण|कदम)")
# "हर मिनट", "हर चरण में", "हर कदम पर" — step of 1, no number
_HI_STEP_BARE = re.compile(r"हर\s+(मिनट|सेकंड|घंटे|मीटर|चरण|कदम|पड़ाव|स्टेज)")
# "every 5 minutes", "every 100 meters"
_EN_STEP = re.compile(r"every\s+" + _NUM + r"\s*(minute|second|hour|meter|metre|km|kilometer|year|step|stage)s?",
                      re.I)
_EN_STEP_BARE = re.compile(r"\b(minute by minute|step by step|second by second|"
                           r"stage by stage|every step|every minute|every stage)\b", re.I)

# Span the checkpoints run across: "1 सेकंड से 1 घंटे तक", "from 10m to 70m"
_HI_SPAN = re.compile(_NUM + r"\s*([^\s]{0,12}?)\s*से\s+" + _NUM + r"\s*([^\s]{0,12}?)\s*तक")
_EN_SPAN = re.compile(r"from\s+" + _NUM + r"\s*(\w{0,12})\s+to\s+" + _NUM + r"\s*(\w{0,12})", re.I)

# Multi-stage language that implies a journey even without arithmetic.
_JOURNEY_HINT = re.compile(
    r"(मिनट दर मिनट|कदम दर कदम|चरण दर चरण|एक-एक करके|क्रमशः|"
    r"minute by minute|step by step|blow by blow|stage by stage|"
    r"हर चरण में|हर पड़ाव|टाइमलाइन|timeline|countdown|काउंटडाउन)", re.I)

# (magnitude in the dimension's base unit, dimension). Steps and spans are
# only reconciled when they share a dimension, so "हर 100 मीटर" across
# "1 किलोमीटर" is 10 beats while "हर 5 मिनट" across "70 मीटर" is unknowable.
_UNITS = {
    "सेकंड": (1, "time"), "सेकण्ड": (1, "time"), "second": (1, "time"),
    "मिनट": (60, "time"), "minute": (60, "time"),
    "घंट": (3600, "time"), "घंटा": (3600, "time"), "घंटे": (3600, "time"),
    "घण्ट": (3600, "time"), "hour": (3600, "time"),
    "मीटर": (1, "length"), "meter": (1, "length"), "metre": (1, "length"),
    "m": (1, "length"),
    "किमी": (1000, "length"), "किलोमीटर": (1000, "length"),
    "km": (1000, "length"), "kilometer": (1000, "length"),
    "साल": (1, "epoch"), "year": (1, "epoch"),
}

# A bare magnitude anywhere in the topic ("1 घंटा", "1 किलोमीटर"). When the
# checkpoint step shares its dimension, this is the span the steps run across
# even though no "से ... तक" range was written — the failure mode that let
# "1 घंटा — हर मिनट" (60 checkpoints) read as a 5-beat topic.
_MAGNITUDE = re.compile(
    _NUM + r"\s*(घंटे|घंटा|घण्टे|घण्टा|घंट|मिनट|सेकंड|सेकण्ड|किलोमीटर|किमी|मीटर|साल|"
           r"hours?|minutes?|seconds?|kilometers?|meters?|metres?|km|years?)\b", re.I)


def _to_float(raw) -> float:
    try:
        return float(str(raw).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _unit(raw) -> tuple:
    """(magnitude, dimension) for a unit token; (0.0, "") when unrecognised."""
    u = str(raw or "").strip().lower()
    for candidate in (u, u.rstrip("s"), u.rstrip("ेाो"), u.rstrip("sेाो")):
        if candidate in _UNITS:
            mag, dim = _UNITS[candidate]
            return float(mag), dim
    return 0.0, ""


def _step_of(topic: str) -> tuple:
    """(interval size, unit magnitude, dimension, matched text) for one
    checkpoint. (0.0, 0.0, "", "") when the topic names no checkpoint at all.

    The matched text is returned so `_span_of` can exclude it: "हर 5 मिनट" must
    not also be read as a 5-minute SPAN for its own steps."""
    for rx in (_HI_STEP, _EN_STEP):
        m = rx.search(topic)
        if m:
            mag, dim = _unit(m.group(2))
            return (_to_float(m.group(1)) or 1.0), mag, dim, m.group(0)
    for rx in (_HI_STEP_BARE, _EN_STEP_BARE):
        m = rx.search(topic)
        if m:
            mag, dim = _unit(m.group(1))
            return 1.0, mag, dim, m.group(0)
    return 0.0, 0.0, "", ""


def _span_of(topic: str, step_mag: float, step_dim: str) -> float:
    """How far the checkpoints run, expressed in the STEP's own unit.
    0.0 when the topic states no span this step can be measured against."""
    for rx in (_HI_SPAN, _EN_SPAN):
        m = rx.search(topic)
        if not m:
            continue
        lo_v, (lo_mag, lo_dim) = _to_float(m.group(1)), _unit(m.group(2))
        hi_v, (hi_mag, hi_dim) = _to_float(m.group(3)), _unit(m.group(4))
        if lo_dim and lo_dim == hi_dim == step_dim and step_mag:
            return max(lo_v * lo_mag, hi_v * hi_mag) / step_mag
        if not lo_dim and not hi_dim:        # bare same-unit span ("10m to 70m")
            return max(lo_v, hi_v)
    if step_dim and step_mag:                # bare magnitude fallback
        largest = max((_to_float(v) * _unit(u)[0]
                       for v, u in _MAGNITUDE.findall(topic)
                       if _unit(u)[1] == step_dim), default=0.0)
        if largest:
            return largest / step_mag
    return 0.0


def _has_span(topic: str) -> bool:
    return bool(_HI_SPAN.search(topic) or _EN_SPAN.search(topic))


def beats(topic: str) -> int:
    """How many checkpoints the topic's own words promise. 0 = single claim."""
    t = str(topic or "")
    step, step_mag, step_dim, step_text = _step_of(t)
    if not step:
        # A traversal can be promised by a span alone ("From 10m to 70m") or
        # by stage language, with no explicit interval.
        return DEFAULT_BEATS if (_has_span(t) or _JOURNEY_HINT.search(t)) else 0
    # Measure the span across the topic MINUS the step phrase itself.
    span = _span_of(t.replace(step_text, " ", 1), step_mag, step_dim)
    n = int(round(span / step)) if span else DEFAULT_BEATS
    return max(MIN_BEATS, min(MAX_BEATS, n))


def classify(topic: str) -> str:
    return CHECKPOINT_JOURNEY if beats(topic) else SINGLE_CLAIM


def seconds_needed(topic: str) -> float:
    """Runtime the promise requires to be paid off in full."""
    return BASE_SECONDS + beats(topic) * SECONDS_PER_BEAT


def fits_in(topic: str, max_seconds: float) -> bool:
    return seconds_needed(topic) <= float(max_seconds)


def explain(topic: str) -> str:
    """One-line log string: shape, beat count, runtime the promise implies."""
    n = beats(topic)
    return (f"{classify(topic)} ({n} promised checkpoint"
            f"{'' if n == 1 else 's'}, needs ~{seconds_needed(topic):.0f}s)")


# ── prompt blocks ────────────────────────────────────────────────────────
# pick_topic scores candidates against one of these. The single-claim rubric
# deliberately INVERTS the journey test: what makes a great 6-minute topic
# ("one changing variable, 6+ escalating milestones") is exactly what kills a
# Short, because every milestone is a promise the runtime cannot keep.

_SINGLE_CLAIM_RUBRIC = """THE SINGLE-CLAIM TEST — score each candidate 1-10 on ALL of:
- one_claim: can the WHOLE topic be stated, and settled, in ONE sentence?
- jolt: is the claim surprising enough to stop a thumb inside 1 second?
- instant_stakes: is the consequence obvious without any setup or context?
- one_image: can it be carried by ONE arresting visual (not a sequence)?
- closure: does the answer FIT in under {max_seconds} seconds, completely?
- loop: after the answer lands, does the opening line become MORE interesting
  (so the viewer replays it)?
- feasibility: can stock footage + AI stills TRUTHFULLY illustrate it?
- source_confidence: are its core facts well-established and verifiable?

HARD REJECT — these are LONG-FORM topics and must not be proposed here:
- Anything promising checkpoints or stages: "हर 5 मिनट", "हर 100 मीटर",
  "मिनट दर मिनट", "step by step", "1 सेकंड से 1 घंटे तक", "हर चरण में".
- Anything whose interest depends on a JOURNEY along a changing variable
  (depth, altitude, time, temperature) with multiple milestones.
- Anything needing more than ~{max_seconds} seconds of narration to settle.
A topic that promises N checkpoints makes the viewer expect all N. In a Short
they cannot all appear, so the video reads as cut off and gets swiped away.
Measured on this channel: every checkpoint Short retained under 40%; every
single-claim Short retained over 55%. Propose ONE-CLAIM topics only."""

_JOURNEY_RUBRIC = """THE VISUAL JOURNEY TEST — score each candidate 1-10 on ALL of:
- journey: is there ONE changing variable the viewer travels along
  (a case timeline — hours missing, days of searching, clues found — or
  depth, speed, time, temperature, scale)?
- escalation: can it produce 6+ visibly escalating milestones?
- number_hook: does it contain one concrete, quotable number?
- human_first: does it lead with PEOPLE (the vanished, the witnesses, the
  searchers) rather than an object or a place? "5 लोग गायब हुए" beats "एक
  पांडुलिपि जो कोई नहीं पढ़ सका" — humans are the strongest hook.
- human_stakes: is there a consequence a viewer can feel on their own body/city?
- one_breath: can the premise be said in ONE plain-Hindi sentence, with zero
  unfamiliar proper nouns, and still force a question back?
- visual: does something VISIBLY change on screen every 30 seconds?
- thumbnail: can it be drawn as ONE dramatic image?
- feasibility: can stock footage + AI stills TRUTHFULLY illustrate it
  (no reenactments, no specific people, no news footage)?
- source_confidence: are its core facts well-established and easy to verify
  with primary sources (investigation records, scientific/government archives)?
- sequel: does it naturally open an obvious next-episode question?
A topic that is a list of facts ("types of X") must score low on journey."""


def rubric(shape: str, max_seconds: float = 90) -> str:
    """The candidate-scoring block for pick_topic, chosen by target format."""
    if shape == SINGLE_CLAIM:
        return _SINGLE_CLAIM_RUBRIC.format(max_seconds=int(max_seconds))
    return _JOURNEY_RUBRIC


def score_keys(shape: str) -> list:
    """Keys the model must return in each candidate's "scores" object."""
    if shape == SINGLE_CLAIM:
        return ["one_claim", "jolt", "instant_stakes", "one_image", "closure",
                "loop", "feasibility", "source_confidence"]
    return ["journey", "escalation", "number_hook", "human_first",
            "human_stakes", "one_breath", "visual", "thumbnail",
            "feasibility", "source_confidence", "sequel"]
