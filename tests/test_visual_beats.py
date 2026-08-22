import visual_beats
import run


def _cfg():
    return {
        "channel": {"wpm": 120},
        "longform_quality": {"visual_beats": {
            "hook_max_seconds": 3.5, "max_seconds": 6,
            "min_per_scene": 2, "max_per_scene": 12,
        }},
    }


def test_target_count_is_faster_for_hook():
    scene = {"narration": " ".join(f"शब्द{i}" for i in range(48))}
    assert visual_beats.target_beat_count(scene, _cfg(), 0) > \
        visual_beats.target_beat_count(scene, _cfg(), 1)


def test_source_policy_is_preserved_and_premium_hook_is_custom():
    cfg = _cfg()
    cfg["visual_director"] = {"enabled": True}
    cfg["ai_images"] = {"premium_hook": {"enabled": True}}
    script = {"scenes": [{"n": 1, "delivery": "hook",
                           "narration": "word " * 30,
                           "search_terms": ["Kuldhara"]}]}
    raw = {"scenes": [{"n": 1, "visual_beats": [
        {"cue": "word word", "search_terms": ["Kuldhara"],
         "purpose": "real village", "family": "establish_place",
         "source_policy": "primary"},
        {"cue": "word word", "search_terms": ["desert"],
         "purpose": "environment", "family": "isolation",
         "source_policy": "stock"},
    ]}]}
    result = visual_beats.normalize_plan(script, raw, cfg)
    beats = result["scenes"][0]["visual_beats"]
    assert beats[0]["source_policy"] == "custom"
    assert beats[1]["source_policy"] == "stock"


def test_normalize_plan_falls_back_when_model_returns_too_few_beats():
    script = {"scenes": [{"n": 1, "title": "गुरुत्व", "narration":
                           "अगर गुरुत्वाकर्षण अचानक दोगुना हो जाए तो हर कदम भारी होगा",
                           "search_terms": ["heavy gravity walking"]}]}
    raw = {"scenes": [{"n": 1, "visual_beats": []}]}
    result = visual_beats.normalize_plan(script, raw, _cfg())
    assert len(result["scenes"][0]["visual_beats"]) >= 2
    assert result["scenes"][0]["visual_beats"][0]["search_terms"]


def test_cues_map_to_contiguous_full_scene_timing():
    scene = {
        "narration": "अगर गुरुत्वाकर्षण दोगुना हो जाए हड्डियां दबेंगी और इमारतें झुकेंगी",
        "audio_duration": 9.0,
        "visual_beats": [
            {"cue": "अगर गुरुत्वाकर्षण", "search_terms": ["gravity person"]},
            {"cue": "हड्डियां दबेंगी", "search_terms": ["human skeleton"]},
            {"cue": "इमारतें झुकेंगी", "search_terms": ["building collapse"]},
        ],
    }
    beats = visual_beats.time_scene(scene)
    assert beats[0]["start"] == 0
    assert beats[0]["start"] + beats[0]["duration"] == beats[1]["start"]
    assert abs(beats[-1]["start"] + beats[-1]["duration"] - 9.0) < 0.01
    assert beats[1]["start"] > beats[0]["start"]


def test_manifest_quantizes_shared_boundaries_without_blank_frames():
    scene = {
        "audio_duration": 5.0,
        "assets": [],
        "visual_beats": [
            {"start": 0.0, "duration": 1.01},
            {"start": 1.01, "duration": 2.01},
            {"start": 3.02, "duration": 1.98},
        ],
    }
    beats = run._visual_beat_manifest(scene, 30)

    assert beats[0]["fromFrame"] == 0
    assert all(
        left["fromFrame"] + left["durationFrames"] == right["fromFrame"]
        for left, right in zip(beats, beats[1:])
    )
    assert beats[-1]["fromFrame"] + beats[-1]["durationFrames"] == 150
