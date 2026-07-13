import visual_beats


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

