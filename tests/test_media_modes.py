import script_gen


def test_template_modes_are_removed_from_generated_scripts():
    for mode in ("kinetic", "card", "glass", "scale", "causal"):
        script = {"title": "t", "scenes": [{
            "narration": "one two three", "visual_mode": mode,
            "kinetic_text": "title", "card": {"headline": "x"},
            "glass": {"headline": "x"}, "compare": {"value": 1},
            "causal": {"steps": ["A", "B"]},
        }]}
        scene = script_gen._normalize(script, 1)["scenes"][0]
        assert scene["visual_mode"] == "broll"
        for field in ("kinetic_text", "card", "glass", "compare", "causal"):
            assert field not in scene


def test_evidence_is_a_media_instruction_with_a_real_source():
    script = {"title": "t", "scenes": [{
        "narration": "one two three", "visual_mode": "evidence",
        "evidence": {"source": "NASA 2023", "confidence": "पुष्टि"},
    }]}
    scene = script_gen._normalize(script, 1)["scenes"][0]
    assert scene["visual_mode"] == "evidence"
    assert scene["evidence"]["source"] == "NASA 2023"


def test_invalid_stat_degrades_to_full_frame_media():
    script = {"title": "t", "scenes": [{
        "narration": "one two three", "visual_mode": "stat",
        "stat": {"value": "NaN", "label": "bad"},
    }]}
    scene = script_gen._normalize(script, 1)["scenes"][0]
    assert scene["visual_mode"] == "broll"
    assert scene["stat"] == {}
