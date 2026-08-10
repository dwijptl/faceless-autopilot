from PIL import Image, ImageDraw

import ai_images
import assets
import run
import vision_qc


def _cfg():
    return {
        "video": {"width": 640, "height": 360, "max_shot_seconds": 5},
        "ai_images": {
            "enabled": True,
            "premium_hook": {
                "enabled": True,
                "longform_only": True,
                "model": "fal-ai/flux-2-pro",
                "candidates": 3,
                "estimated_usd_per_candidate": 0.12,
                "max_usd_per_video": 0.40,
                "min_luma": 20,
                "min_contrast": 10,
                "fallback_to_standard": False,
            },
        },
        "qc": {"visual_check": True, "max_upscale": 1.25,
               "max_requests_per_video": 5},
        "llm": {"model": "test", "fallback_models": []},
    }


def _scene():
    return {
        "n": 1,
        "delivery": "hook",
        "visual_mode": "broll",
        "episode_title": "The empty village",
        "hero_prompt": "one abandoned sandstone village at night",
        "narration": "एक रात पूरा गाँव खाली हो गया।",
        "search_terms": ["abandoned Rajasthan village"],
        "visual_beats": [{
            "cue": "एक रात पूरा गाँव",
            "purpose": "pose the unexplained disappearance",
            "search_terms": ["abandoned Rajasthan village"],
            "family": "cold_open_hook",
            "duration": 3.5,
        }],
    }


def _write_candidate(path, number):
    img = Image.new("RGB", (640, 360), (80 + number * 12, 85, 95))
    draw = ImageDraw.Draw(img)
    x = 55 + number * 95
    draw.rectangle((x, 35, x + 130, 310), fill=(225, 215, 185))
    draw.ellipse((420 - number * 25, 70, 570 - number * 25, 220),
                 fill=(15, 20, 28))
    img.save(path, quality=92)


def test_premium_provider_uses_configured_model(monkeypatch, tmp_path):
    calls = []

    def fake_flux(prompt, out_path, cfg, aspect, models=None):
        calls.append(models)
        return True

    monkeypatch.setattr(ai_images, "_flux", fake_flux)
    monkeypatch.setattr(ai_images, "_gemini_image",
                        lambda *args, **kwargs: False)
    out = str(tmp_path / "hook.jpg")
    assert ai_images.generate("p", out, "gk", _cfg(), provider="premium")
    assert calls == [["fal-ai/flux-2-pro"]]


def test_hook_generates_three_and_keeps_ranked_winner(tmp_path, monkeypatch):
    calls = []

    def fake_generate(prompt, path, key, cfg, aspect="16:9 wide",
                      provider="auto"):
        calls.append((prompt, provider))
        _write_candidate(path, len(calls))
        return True

    monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.setattr(assets.ai_images, "generate", fake_generate)
    monkeypatch.setattr(assets.vision_qc, "pick_hook_still",
                        lambda *args, **kwargs: 1)
    assets.reset_episode_state()
    scene = _scene()
    out = assets.fetch_scene_assets(
        scene, 3.5, str(tmp_path), _cfg(), "pk", "gk", set(), set(), [0],
        rescue_budget=[0], director_budget=None)
    premium = [a for a in out if a.get("premium_hook")]
    assert len(premium) == 1
    assert premium[0]["path"].endswith("s01_hook_c02.jpg")
    assert premium[0]["beat_index"] == 0
    assert premium[0]["hook_candidates"] == 3
    assert len(calls) == 3
    assert all(provider == "premium" for _, provider in calls)
    assert not (tmp_path / "s01_hook_c01.jpg").exists()
    assert not (tmp_path / "s01_hook_c03.jpg").exists()


def test_hook_cost_gate_prevents_generation(tmp_path, monkeypatch):
    cfg = _cfg()
    cfg["ai_images"]["premium_hook"]["max_usd_per_video"] = 0.11
    monkeypatch.setenv("FAL_KEY", "configured")
    monkeypatch.setattr(
        assets.ai_images, "generate",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError))
    result = assets._premium_hook_asset(
        _scene(), _scene()["visual_beats"][0], str(tmp_path), cfg, "gk", set())
    assert result is None


def test_recurring_pose_does_not_replace_premium_hook(tmp_path):
    premium = tmp_path / "premium.jpg"
    pose = tmp_path / "pose.jpg"
    premium.write_bytes(b"p" * 2000)
    pose.write_bytes(b"h" * 2000)
    scenes = [
        {"n": 1, "assets": [{"path": str(premium), "kind": "image",
                               "ai": True, "premium_hook": True,
                               "beat_index": 0}],
         "visual_beats": [{}]},
        {"n": 2, "assets": [], "visual_beats": [{}]},
    ]
    run._attach_hero(scenes, {"establish": str(pose), "final": str(pose)})
    assert scenes[0]["assets"][0]["path"] == str(premium)
    assert len(scenes[0]["assets"]) == 1
    assert scenes[1]["assets"][0]["path"] == str(pose)


def test_hook_vision_judge_can_reject_every_candidate(monkeypatch):
    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [
                {"text": '{"best": 0, "reason": "invented evidence"}'}
            ]}}]}

    cfg = _cfg()
    monkeypatch.setattr(vision_qc, "_frame_jpegs_b64",
                        lambda *args: ["encoded"])
    monkeypatch.setattr(vision_qc.requests, "post",
                        lambda *args, **kwargs: Response())
    vision_qc.begin_run(cfg)
    assert vision_qc.pick_hook_still(
        [("a.jpg", "image"), ("b.jpg", "image")], "scene", "title",
        "intent", "key", cfg) == -1
