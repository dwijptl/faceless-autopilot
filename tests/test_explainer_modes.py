import copy

import retention_lint
import script_gen


def test_normalize_compare_bounds_and_camelcase():
    c = script_gen._normalize_compare({
        "value": "11034", "unit": "मीटर", "label": "गहराई",
        "anchor_label": "बुर्ज ख़लीफ़ा", "anchor_value": 828,
        "anchor_unit": "मीटर"})
    assert c["value"] == 11034
    assert c["anchorLabel"] == "बुर्ज ख़लीफ़ा"
    assert c["anchorValue"] == 828
    # invalid anchors collapse to {}
    assert script_gen._normalize_compare({"value": 5, "anchor_value": 0}) == {}
    assert script_gen._normalize_compare({"value": "NaN"}) == {}


def test_normalize_causal_needs_two_steps():
    assert script_gen._normalize_causal({"steps": ["only one"]}) == {}
    c = script_gen._normalize_causal(
        {"headline": "h", "steps": ["A", "B", "C", "", "D", "E", "F", "G"]})
    assert c["steps"] == ["A", "B", "C", "D", "E", "F"]  # capped at 6


def test_normalize_evidence_confidence_whitelist():
    e = script_gen._normalize_evidence(
        {"source": "NASA 2023", "confidence": "पुष्टि"})
    assert e["confidence"] == "पुष्टि"
    e2 = script_gen._normalize_evidence(
        {"source": "NASA", "confidence": "definitely true bro"})
    assert e2["confidence"] == ""
    assert script_gen._normalize_evidence({"confidence": "पुष्टि"}) == {}


def test_invalid_payload_degrades_mode_to_broll():
    script = {"title": "t", "scenes": [
        {"narration": "one two three", "visual_mode": "scale"},   # no compare
        {"narration": "one two three", "visual_mode": "causal"},  # no steps
        {"narration": "one two three", "visual_mode": "evidence",
         "evidence": {"source": "Nature Geoscience 2024",
                      "confidence": "अनुमान"}},
    ]}
    out = script_gen._normalize(script, 1)
    assert out["scenes"][0]["visual_mode"] == "broll"
    assert out["scenes"][1]["visual_mode"] == "broll"
    assert out["scenes"][2]["visual_mode"] == "evidence"


def test_lint_checks_compare_value_spoken():
    scenes = []
    for i in range(6):
        scenes.append({"n": i + 1,
                       "narration": f"दृश्य {i + 1} की अलग कहानी यहाँ चलती है "
                                    * 4,
                       "narrative_role": "", "reward": {"strength": 0.8},
                       "question_out": "क्यों?"})
    scenes[2]["compare"] = {"value": 828, "anchorLabel": "x",
                            "anchorValue": 1}
    script = {"title": "t", "scenes": scenes, "retention_plan": {}}
    codes = {v["code"] for v in
             retention_lint.lint(copy.deepcopy(script),
                                 {"retention": {}})["violations"]}
    assert "claim_display_mismatch" in codes
    scenes[2]["narration"] += " यह 828 मीटर ऊंचा है"
    codes2 = {v["code"] for v in
              retention_lint.lint(script, {"retention": {}})["violations"]}
    assert "claim_display_mismatch" not in codes2
