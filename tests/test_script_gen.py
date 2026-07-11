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
