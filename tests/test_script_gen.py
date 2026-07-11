import json

import pytest

import script_gen


@pytest.mark.parametrize("text", [
    '{"topic":"x"}',
    '```json\n{"topic":"x"}\n```',
    'Before this: {"topic":"x"} after this',
])
def test_parse_json_handles_llm_wrappers(text):
    assert script_gen._parse_json(text) == {"topic": "x"}


def test_normalize_sets_safe_defaults():
    script = {"title": "x", "scenes": [{"narration": "one", "visual_mode": "bad"}]}
    result = script_gen._normalize(script, 1)
    assert result["scenes"][0]["visual_mode"] == "broll"
    assert result["scenes"][0]["delivery"] == "hook"
    assert result["scenes"][0]["card"] == {}
    assert result["scenes"][0]["glass"]["headline"] == ""


def test_normalize_stat_keeps_rich_variants():
    stat = script_gen._normalize_stat({
        "value": "49", "suffix": "%", "label": "oxygen",
        "max": "100", "baseline": 8,
        "bars": [{"label": "A", "value": 8}, {"label": "B", "value": "49"}],
    })
    assert stat["value"] == 49
    assert stat["max"] == 100
    assert stat["baseline"] == 8
    assert stat["bars"] == [{"label": "A", "value": 8},
                            {"label": "B", "value": 49}]


@pytest.mark.parametrize("bad", [None, "NaN", "inf", "-inf", {}, []])
def test_normalize_stat_rejects_non_finite_values(bad):
    stat = script_gen._normalize_stat({"value": bad, "max": bad,
                                       "baseline": bad})
    assert stat["value"] == 0
    assert "max" not in stat
    assert "baseline" not in stat


def test_normalize_stat_needs_two_valid_bars():
    stat = script_gen._normalize_stat({
        "bars": [{"label": "only", "value": 1},
                 {"label": "bad", "value": "NaN"}],
    })
    assert "bars" not in stat


def test_normalize_glass_bounds_numbers_and_direction():
    glass = script_gen._normalize_glass({
        "headline": "समुद्र का रहस्य", "value": "11034", "delta": "-12",
        "delta_direction": "down", "coordinates": "11.3°N · 142.2°E",
    })
    assert glass["value"] == 11034
    assert glass["delta"] == -12
    assert glass["deltaDirection"] == "down"
    assert glass["coordinates"] == "11.3°N · 142.2°E"


def test_critique_preserves_structured_visual_payload(monkeypatch):
    original = script_gen._normalize({
        "title": "x", "scenes": [{"narration": "one", "visual_mode": "glass",
        "glass": {"headline": "उत्तर", "value": 42}}]}, 1)
    revised = {"title": "x", "scenes": [{"narration": "better words",
        "visual_mode": "glass", "glass": {}}]}
    monkeypatch.setattr(script_gen, "_llm", lambda *args: json.dumps(revised))
    result = script_gen._critique(original, {"llm": {"critique": True}},
                                  "key", "short", 1)
    assert result["scenes"][0]["glass"]["value"] == 42
    assert result["scenes"][0]["narration"] == "better words"
