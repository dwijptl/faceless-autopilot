"""Topic shape gate — the fix for the channel's sub-40% Shorts retention.

Every published-topic case below is a real title from topics_done_shorts.txt,
annotated with the retention it actually achieved in the 2026-06-26..07-23
analytics window. They are regression anchors: if the classifier stops sorting
them the way the data did, the gate has drifted.
"""
import pytest

import script_gen
import topic_shape as ts


# (topic, measured retention %) — real published Shorts
CHECKPOINT_SHORTS = [
    ("11,034 मीटर की गहराई पर 1 घंटा: आपके शरीर के साथ हर मिनट क्या होगा?", 15.0),
    ("मंगल ग्रह की सतह पर 1 सेकंड से 1 घंटे तक: −60°C की धूल भरी हवा और "
     "0.6% वायुमंडलीय दबाव में हर 5 मिनट आपके शरीर के साथ क्या होगा?", 11.3),
    ("शुक्र ग्रह पर 1 सेकंड से 1 घंटे तक: 467°C की सतह पर हर 5 मिनट में "
     "आपके शरीर के साथ क्या होगा?", 20.5),
    ("शुक्र की सतह पर 1 किलोमीटर चलने में 417 दिन: हर 100 मीटर पर दबाव, "
     "गर्मी और हवा आपको कैसे रोकती है?", 32.7),
    ("समुद्र तल से 8,848 मीटर ऊपर: माउंट एवरेस्ट की चोटी पर 1 घंटे में "
     "आपके फेफड़ों और मस्तिष्क के साथ हर 10 मिनट क्या होगा?", 35.2),
]

SINGLE_CLAIM_SHORTS = [
    ("NASA Ko Earth Ke Andar Se Signal Mila", 185.5),
    ("गायब होते द्वीप: पृथ्वी के सबसे रहस्यमयी ठिकाने", 104.4),
    ("हमारे सौरमंडल में आया वो रहस्यमयी मेहमान जो किसी दूसरे तारे से आया था", 58.6),
]


@pytest.mark.parametrize("topic,retention", CHECKPOINT_SHORTS)
def test_checkpoint_topics_are_detected(topic, retention):
    assert ts.classify(topic) == ts.CHECKPOINT_JOURNEY
    assert ts.beats(topic) >= 2
    assert retention < 40  # every one of these fell under the retention floor


@pytest.mark.parametrize("topic,retention", SINGLE_CLAIM_SHORTS)
def test_single_claim_topics_are_detected(topic, retention):
    assert ts.classify(topic) == ts.SINGLE_CLAIM
    assert ts.beats(topic) == 0
    assert retention > 55  # every one of these cleared the floor comfortably


def test_checkpoint_topics_are_barred_from_shorts():
    """Shape is the gate, not the arithmetic: a checkpoint topic is wrong for
    a Short even where the beat math happens to land under the band."""
    for topic, _ in CHECKPOINT_SHORTS:
        assert ts.classify(topic) != ts.SINGLE_CLAIM, topic


def test_topics_with_heavy_stated_arithmetic_overflow_the_band():
    """Where the topic states enough checkpoints, the overflow is measurable
    on runtime alone — no shape judgement needed.

    Note the arithmetic gate is the WEAKER of the two: the Everest topic works
    out to 6 beats (~80s) and would squeak inside a 90s band. It is barred
    anyway, by shape — which is why shape is checked first."""
    heavy = [t for t, _ in CHECKPOINT_SHORTS if ts.beats(t) >= 8]
    assert len(heavy) >= 3, "expected several topics with heavy stated spans"
    for topic in heavy:
        assert not ts.fits_in(topic, 90), f"{topic} -> {ts.explain(topic)}"


def test_length_units_reconcile_across_scales():
    """"1 किलोमीटर" walked in "हर 100 मीटर" steps is 10 checkpoints, not a
    default guess — the Venus topic that shipped at 32.7%."""
    topic = ("शुक्र की सतह पर 1 किलोमीटर चलने में 417 दिन: हर 100 मीटर पर "
             "दबाव, गर्मी और हवा आपको कैसे रोकती है?")
    assert ts.beats(topic) == 10
    assert not ts.fits_in(topic, 90)


def test_mismatched_dimensions_do_not_reconcile():
    """A time step against a length span is unknowable — fall back, don't
    invent arithmetic."""
    assert ts.beats("70 मीटर नीचे: हर 5 मिनट क्या होगा?") == ts.DEFAULT_BEATS


def test_single_claim_topics_fit_a_short():
    for topic, _ in SINGLE_CLAIM_SHORTS:
        assert ts.fits_in(topic, 90), topic


def test_beats_uses_span_over_step_when_both_are_stated():
    # "1 सेकंड से 1 घंटे तक" spanning "हर 5 मिनट" = 60min / 5min = 12 beats
    topic = "मंगल पर 1 सेकंड से 1 घंटे तक: हर 5 मिनट क्या होगा?"
    assert ts.beats(topic) == 12
    assert ts.seconds_needed(topic) > 120


def test_bare_journey_hint_counts_without_arithmetic():
    assert ts.beats("मिनट दर मिनट: क्या होता है") == ts.DEFAULT_BEATS
    assert ts.classify("step by step guide to the trench") == ts.CHECKPOINT_JOURNEY


def test_beats_are_clamped():
    # "हर 1 मिनट" across "1 घंटा" is 60 raw; clamped so runtime math stays sane
    assert ts.beats("1 मिनट से 1 घंटे तक हर 1 मिनट") <= ts.MAX_BEATS


def test_english_and_hinglish_checkpoints():
    assert ts.classify("What happens every 10 meters as you descend") == \
        ts.CHECKPOINT_JOURNEY
    assert ts.classify("From 10m to 70m: what floods first") == \
        ts.CHECKPOINT_JOURNEY


def test_rubrics_differ_and_name_their_own_score_keys():
    single = ts.rubric(ts.SINGLE_CLAIM, 90)
    journey = ts.rubric(ts.CHECKPOINT_JOURNEY)
    assert single != journey
    assert "SINGLE-CLAIM TEST" in single and "90 seconds" in single
    assert "VISUAL JOURNEY TEST" in journey
    for key in ts.score_keys(ts.SINGLE_CLAIM):
        assert key in single
    for key in ts.score_keys(ts.CHECKPOINT_JOURNEY):
        assert key in journey


def test_score_template_matches_the_active_rubric():
    tmpl = script_gen._score_template(ts.SINGLE_CLAIM)
    assert '"one_claim": 0' in tmpl and '"journey"' not in tmpl
    assert '"journey": 0' in script_gen._score_template("any")


# ── pick_topic shape gate ────────────────────────────────────────────────

CFG = {"channel": {"niche": "science", "audience": "hindi", "language": "hi-in"}}


@pytest.fixture
def no_forced_topic(monkeypatch):
    monkeypatch.delenv("FORCED_TOPIC", raising=False)


def _reply(*topics):
    import json
    return json.dumps({"candidates": [{"topic": t, "total": 9 - i}
                                      for i, t in enumerate(topics)],
                       "topic": topics[0]}, ensure_ascii=False)


def test_shape_gate_prefers_a_fitting_candidate_over_the_models_pick(
        monkeypatch, tmp_path, no_forced_topic):
    """The model ranked the checkpoint topic first; the gate takes the
    single-claim one instead of burning a retry."""
    monkeypatch.setattr(script_gen, "_llm", lambda *a, **k: _reply(
        "1 सेकंड से 1 घंटे तक: हर 5 मिनट क्या होगा?",
        "समुद्र के नीचे मिला वो दरवाज़ा जो खुलता ही नहीं"))
    got = script_gen.pick_topic(CFG, "key", str(tmp_path / "done.txt"),
                                shape=ts.SINGLE_CLAIM, max_seconds=90)
    assert got == "समुद्र के नीचे मिला वो दरवाज़ा जो खुलता ही नहीं"


def test_shape_gate_reprompts_when_every_candidate_is_wrong_shaped(
        monkeypatch, tmp_path, no_forced_topic):
    calls = []

    def fake_llm(prompt, *a, **k):
        calls.append(prompt)
        if len(calls) == 1:
            return _reply("हर 5 मिनट: शरीर का क्या होगा?",
                          "हर 100 मीटर पर क्या बदलता है")
        return _reply("धरती के अंदर से आया वो सिग्नल")

    monkeypatch.setattr(script_gen, "_llm", fake_llm)
    got = script_gen.pick_topic(CFG, "key", str(tmp_path / "done.txt"),
                                shape=ts.SINGLE_CLAIM, max_seconds=90)
    assert got == "धरती के अंदर से आया वो सिग्नल"
    assert len(calls) == 2
    assert "REJECTED" in calls[1]        # the retry tells the model why


def test_shape_gate_raises_rather_than_shipping_a_wrong_shaped_topic(
        monkeypatch, tmp_path, no_forced_topic):
    monkeypatch.setattr(script_gen, "_llm",
                        lambda *a, **k: _reply("हर 5 मिनट: क्या होगा?"))
    with pytest.raises(RuntimeError, match="single_claim"):
        script_gen.pick_topic(CFG, "key", str(tmp_path / "done.txt"),
                              shape=ts.SINGLE_CLAIM, max_seconds=90)


def test_long_form_keeps_the_models_pick_unfiltered(
        monkeypatch, tmp_path, no_forced_topic):
    """shape="any" must behave exactly as before this gate existed."""
    journey = "1 सेकंड से 1 घंटे तक: हर 5 मिनट क्या होगा?"
    monkeypatch.setattr(script_gen, "_llm", lambda *a, **k: _reply(journey))
    assert script_gen.pick_topic(CFG, "key", str(tmp_path / "done.txt")) == journey


def test_cross_format_history_reaches_the_prompt(
        monkeypatch, tmp_path, no_forced_topic):
    """A Short must see long-form topics, or the two formats ship twins."""
    seen = {}

    def fake_llm(prompt, *a, **k):
        seen["prompt"] = prompt
        return _reply("धरती के अंदर से आया वो सिग्नल")

    monkeypatch.setattr(script_gen, "_llm", fake_llm)
    script_gen.pick_topic(CFG, "key", str(tmp_path / "done.txt"),
                          shape=ts.SINGLE_CLAIM,
                          also_done=["NASA को पृथ्वी के अंदर से सिग्नल मिला"],
                          max_seconds=90)
    assert "NASA को पृथ्वी के अंदर से सिग्नल मिला" in seen["prompt"]
