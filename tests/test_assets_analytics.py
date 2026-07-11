import json

import analytics
import assets


def test_usage_log_is_bounded_and_defaults(tmp_path):
    path = tmp_path / "used.json"
    assets.save_usage_log(str(path), {"pexels": list(range(5000)), "prompts": list(range(5000))})
    data = json.loads(path.read_text())
    assert len(data["pexels"]) == len(data["prompts"]) == 4000
    assert len(set(data["pexels"])) == 4000
    assert assets.load_usage_log(str(tmp_path / "missing.json")) == {"pexels": [], "prompts": []}


def test_analytics_override_clamps_values():
    data = analytics.parse_overrides("```yaml\noverrides:\n  target_minutes: 99\n  tts_speed: 0\n  scenes_max: 99\n```")
    assert data == {"target_minutes": 12, "tts_speed": .85, "scenes_max": 14}
