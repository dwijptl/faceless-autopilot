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


def test_portrait_file_selection_prefers_native_portrait():
    video = {"video_files": [
        {"width": 1920, "height": 1080, "link": "landscape"},
        {"width": 1080, "height": 1920, "link": "portrait"},
    ]}
    chosen = assets._best_video_file(video, 1080, 1920, 1.25)
    assert chosen["link"] == "portrait"


def test_portrait_file_selection_rejects_blurry_crop():
    video = {"video_files": [
        {"width": 1920, "height": 1080, "link": "landscape"},
    ]}
    assert assets._best_video_file(video, 1080, 1920, 1.25) is None


# ── gigapixel-image downscale (Make Short #22 render-crash postmortem) ────
def test_downscale_image_clamps_gigapixel(tmp_path):
    import assets
    from PIL import Image
    big = tmp_path / "nasa_orig.jpg"
    Image.new("RGB", (12740, 12750)).save(big)   # ~162 MP, crashed a render
    assets._downscale_image(str(big))
    w, h = Image.open(big).size
    assert max(w, h) == assets.MAX_IMAGE_SIDE     # clamped to 2560 longest edge
    small = tmp_path / "ok.jpg"
    Image.new("RGB", (1080, 1920)).save(small)    # within bounds -> untouched
    assets._downscale_image(str(small))
    assert Image.open(small).size == (1080, 1920)
