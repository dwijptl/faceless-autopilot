"""Visual director — narrative-intent family system (pipeline/families.py)."""
import families
import visual_beats


CFG = {
    "visual_director": {"enabled": True, "mode": "economy",
                        "modes": {"economy": {"ai_stills": 18},
                                  "balanced": {"ai_stills": 28},
                                  "premium": {"ai_stills": 36}}},
    "longform_quality": {"visual_beats": {"min_per_scene": 2,
                                          "max_per_scene": 12}},
    "channel": {"wpm": 130},
    "video": {"max_shot_seconds": 5},
}


# ── spec integrity ─────────────────────────────────────────────────────
def test_exactly_65_families():
    assert len(families.FAMILIES) == 65


def test_every_spec_is_complete_and_valid():
    for key, spec in families.FAMILIES.items():
        assert spec.key == key
        assert spec.cluster and spec.fn and spec.comp
        assert spec.camera in families.CAMERAS
        assert spec.tin in families.TRANSITIONS
        assert spec.media and all(m in ("pg", "ai", "stock")
                                  for m in spec.media)
        assert 1 <= spec.prio <= 5
        if "pg" in spec.media:
            assert spec.pg in families.PG_KINDS, key


def test_no_ornament_vocabulary_in_compositions():
    """The identity is camera-led — Sanatan-style ornament words are banned."""
    for spec in families.FAMILIES.values():
        low = spec.comp.lower()
        for banned in families.BANNED_STYLE:
            assert banned not in low, f"{spec.key} uses banned '{banned}'"


def test_pg_families_never_spend_ai_credits_first():
    for spec in families.FAMILIES.values():
        if spec.media and spec.media[0] == "pg":
            assert spec.prio >= 4, (
                f"{spec.key}: pg-first families must rank low for AI credits")


# ── classifier ─────────────────────────────────────────────────────────
def test_classifier_maps_story_functions():
    assert families.classify("the team descends deeper below the surface") == "descend"
    assert families.classify("three competing theories some believe") == "hypothesis_branch"
    assert families.classify("the last known photograph final entry") == "last_known"
    assert families.classify("timeline of events february date sequence") == "timeline_advance"


def test_classifier_returns_none_for_no_signal():
    assert families.classify("zzz qqq xyzzy") is None


def test_positional_priors():
    scene = {"visual_beats": [{}], "delivery": "hook", "title": ""}
    assert families.classify_beat({}, scene, 0, 0, 5) == "cold_open_hook"
    reveal = {"visual_beats": [{}], "delivery": "reveal", "title": ""}
    assert families.classify_beat({"purpose": "zzz"}, reveal, 3, 0, 5) == "revelation"


# ── transition grammar ─────────────────────────────────────────────────
def test_pair_grammar():
    assert families.transition_for("descend", "descend") == "continue"
    assert families.transition_for("establish_place", "revelation") == "hold_push"
    assert families.transition_for("evidence_reveal", "hypothesis_branch") == "zoom_punch"
    assert families.transition_for("moment_freeze", "traverse") == "cut"
    # unknown incoming family fails open to a dissolve
    assert families.transition_for("descend", "not_a_family") == "dissolve"


def test_transition_planner_caps_high_energy():
    scenes = [{"audio_duration": 5.0,
               "visual_beats": [{"family": "anomaly_highlight"}]}
              for _ in range(4)]
    scenes.insert(0, {"audio_duration": 5.0,
                      "visual_beats": [{"family": "cold_open_hook"}]})
    families.plan_scene_transitions(scenes, min_gap_seconds=20.0)
    energetic = [sc for sc in scenes
                 if sc.get("family_transition") in families.HIGH_ENERGY]
    assert len(energetic) <= 2  # 25s of runtime -> at most 2 energetic cuts


# ── prompt composition ─────────────────────────────────────────────────
def test_compose_prompt_layers_family_pack_identity():
    p = families.compose_prompt("a torn canvas tent in deep snow",
                                "evidence_reveal", "archival_historical")
    assert "torn canvas tent" in p
    assert "artifact centered" in p          # family composition
    assert "archival palette" in p           # domain pack flavor
    assert "cinematic documentary realism" in p  # global identity
    assert "no readable human faces" in p
    for banned in families.BANNED_STYLE:
        assert banned not in p.lower()


def test_domain_pack_auto_selection():
    assert families.pick_domain_pack(
        "Kola Superdeep Borehole drilling into the crust") == "deep_earth"
    assert families.pick_domain_pack(
        "The Wow! signal from deep space telescope") == "space"


# ── budgets + grants ───────────────────────────────────────────────────
def test_ai_budget_modes():
    assert families.ai_still_budget(CFG) == 18
    cfg = {"visual_director": {"enabled": True, "mode": "premium",
                               "modes": {"premium": {"ai_stills": 36}}}}
    assert families.ai_still_budget(cfg) == 36


def test_allocate_ai_prefers_hero_beats():
    scenes = [
        {"visual_beats": [{"family": "establish_place"},   # prio 4, ai-fallback
                          {"family": "hands_at_work"}]},   # prio 4
        {"visual_beats": [{"family": "revelation"},        # prio 1 -> wins
                          {"family": "descend"}]},         # prio 2 -> wins
    ]
    granted = families.allocate_ai(scenes, 2)
    assert granted == 2
    assert scenes[1]["visual_beats"][0].get("ai_grant") is True
    assert scenes[1]["visual_beats"][1].get("ai_grant") is True
    assert not scenes[0]["visual_beats"][0].get("ai_grant")


# ── planner integration (visual_beats.normalize_plan) ──────────────────
def _plan(director_on: bool):
    cfg = dict(CFG)
    if not director_on:
        cfg = {**CFG, "visual_director": {"enabled": False}}
    script = {"scenes": [{
        "n": 1, "narration": "word " * 30, "title": "The tent",
        "delivery": "hook", "search_terms": ["mountain pass"],
    }]}
    raw = {"scenes": [{"n": 1, "visual_beats": [
        {"cue": "word word word", "search_terms": ["torn tent"],
         "purpose": "the evidence artifact discovered", "family": "evidence_reveal",
         "intensity": 7,
         "graphic": {"kind": "chart", "title": "T", "unit": "km",
                     "items": [{"label": "A", "value": 3}]}},
        {"cue": "word word", "search_terms": ["snow prints"],
         "purpose": "footprints traced back to the origin"},
        {"cue": "word", "search_terms": ["dark ridge"],
         "purpose": "descending deeper below the ridge"},
    ]}]}
    return visual_beats.normalize_plan(script, raw, cfg)["scenes"][0]


def test_normalize_plan_keeps_and_classifies_families():
    scene = _plan(True)
    beats = scene["visual_beats"]
    assert beats[0]["family"] == "cold_open_hook" or beats[0]["family"] == "evidence_reveal"
    assert beats[0]["intensity"] == 3          # clamped from 7
    assert beats[0]["graphic"]["kind"] == "chart"
    assert all(b.get("family") for b in beats)  # classifier filled the rest


def test_normalize_plan_director_off_is_legacy():
    scene = _plan(False)
    for beat in scene["visual_beats"]:
        assert "family" not in beat
        assert "graphic" not in beat


def test_graphic_payload_is_bounded():
    bad = visual_beats._normalize_graphic(
        {"kind": "chart", "title": "x" * 500, "unit": "y" * 50,
         "items": [{"label": "L" * 99, "value": "nan"}] * 40})
    assert len(bad["title"]) <= 60
    assert len(bad["unit"]) <= 10
    assert len(bad["items"]) <= 6
    assert all("value" not in i or isinstance(i["value"], float)
               for i in bad["items"])
    assert visual_beats._normalize_graphic({"kind": "hologram"}) == {}
