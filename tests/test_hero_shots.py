import json
import os

import assets
import hero_shots


CFG = {"hero_shots": {"enabled": True, "max_per_video": 2, "seconds": 5,
                      "max_retries": 1, "max_usd_per_video": 1.20,
                      "model": "fal-ai/kling-video/v2.6/pro/image-to-video",
                      "fallback_model": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video"},
       "render": {"style_pack": "documentary"}}


def _still(tmp_path):
    p = tmp_path / "still.png"
    p.write_bytes(b"x" * 1000)
    return str(p)


def test_animate_false_without_fal_key(tmp_path, monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    hero_shots.begin_run()
    assert not hero_shots.animate(_still(tmp_path), "p",
                                  str(tmp_path / "o.mp4"), CFG)
    assert hero_shots.usage_summary() == "hero shots: 0 ($0)"


def test_animate_false_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "k")
    hero_shots.begin_run()
    assert not hero_shots.animate(_still(tmp_path), "p",
                                  str(tmp_path / "o.mp4"),
                                  {"hero_shots": {"enabled": False}})


def test_queue_flow_submits_polls_downloads(tmp_path, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "k")
    hero_shots.begin_run()
    calls = {"post": [], "get": []}

    class _R:
        def __init__(self, payload):
            self.payload = payload
            self.status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return self.payload
        def iter_content(self, chunk_size):
            yield b"v" * 300_000
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_post(url, json=None, headers=None, timeout=None):
        calls["post"].append((url, json))
        return _R({"status_url": "https://q/st", "response_url": "https://q/re"})

    def fake_get(url, headers=None, timeout=None, stream=False):
        calls["get"].append(url)
        if url == "https://q/st":
            return _R({"status": "COMPLETED"})
        if url == "https://q/re":
            return _R({"video": {"url": "https://q/v.mp4"}})
        return _R({})

    monkeypatch.setattr(hero_shots.requests, "post", fake_post)
    monkeypatch.setattr(hero_shots.requests, "get", fake_get)
    monkeypatch.setattr(hero_shots, "_still_data_uri",
                        lambda p: "data:image/jpeg;base64,eA==")
    monkeypatch.setattr(hero_shots, "_clip_ok", lambda p, s: True)
    out = str(tmp_path / "o.mp4")
    assert hero_shots.animate(_still(tmp_path), "prompt", out, CFG, seconds=5)
    url, body = calls["post"][0]
    assert url.endswith("kling-video/v2.6/pro/image-to-video")
    assert body["duration"] == "5"
    assert body["image_url"].startswith("data:image/jpeg;base64,")
    assert os.path.getsize(out) > 200_000
    assert "1" in hero_shots.usage_summary()


def test_cost_gate_refuses_over_ceiling(tmp_path, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "k")
    hero_shots.begin_run()
    hero_shots._spent_usd = 1.10  # two shots + retry already billed
    called = []
    monkeypatch.setattr(hero_shots.requests, "post",
                        lambda *a, **kw: called.append(1))
    assert not hero_shots.animate(_still(tmp_path), "p",
                                  str(tmp_path / "o.mp4"), CFG, seconds=5)
    assert not called  # no request was ever started


def test_keyword_skip_hindi_and_english():
    assert hero_shots.should_skip("close-up of the diver's face")
    assert hero_shots.should_skip("स्क्रीन पर अक्षर उभरते हैं")
    assert not hero_shots.should_skip("pressure crushes the hull in darkness")


def test_select_targets_hook_and_reveal():
    scenes = [{"n": 1, "delivery": "hook"}, {"n": 2, "delivery": "calm"},
              {"n": 3, "delivery": "reveal"}, {"n": 4, "delivery": "calm"}]
    t = hero_shots.select_targets(scenes, 2)
    assert [(sc["n"], bi) for sc, bi in t] == [(1, 0), (3, 0)]
    assert [(sc["n"], bi) for sc, bi in
            hero_shots.select_targets(scenes[:2], 2)] == [(1, 0)]  # no reveal
    assert len(hero_shots.select_targets(scenes, 1)) == 1


def test_motion_prompt_uses_style_pack():
    p = hero_shots.motion_prompt("metal creaks", {"render": {"style_pack": "noir"}})
    assert p.startswith("metal creaks.")
    assert "creeping zoom" in p


def test_usage_summary_reports_spend():
    hero_shots.begin_run()
    hero_shots._spent_usd, hero_shots._accepted = 0.70, 2
    hero_shots.note_retry()
    assert hero_shots.usage_summary() == "hero shots: 2 (+1 retry) ≈ $0.70"
    assert hero_shots.metrics() == {"hero_shots": 2, "hero_retries": 1,
                                    "hero_spend_usd": 0.70}


def test_rescue_still_after_stock_failure(tmp_path, monkeypatch):
    cfg = {"video": {"width": 640, "height": 360, "max_shot_seconds": 5},
           "ai_images": {"enabled": True}}
    scene = {"n": 3, "visual_mode": "broll", "search_terms": ["x"],
             "visual_beats": [{"cue": "दबाव बढ़ता है", "purpose": "escalate",
                               "duration": 4, "search_terms": ["pressure"]}]}
    monkeypatch.setattr(assets, "_stock_videos",
                        lambda *a, **kw: ([], 0.0))
    monkeypatch.setattr(assets, "_stock_photo", lambda *a, **kw: None)
    monkeypatch.setattr(assets, "_nasa_relevant", lambda terms: False)

    def fake_generate(prompt, path, key, c, aspect="16:9 wide"):
        assert "दबाव बढ़ता है" in prompt and "escalate" in prompt
        open(path, "wb").write(b"i" * 30_000)
        return True
    monkeypatch.setattr(assets.ai_images, "generate", fake_generate)

    budget = [2]
    out = assets.fetch_scene_assets(scene, 4.0, str(tmp_path), cfg, "pk", "gk",
                                    set(), set(), [0], rescue_budget=budget)
    assert budget == [1]
    assert any(a.get("ai") and a["path"].endswith("_rescue.png") for a in out)


def test_no_rescue_without_budget(tmp_path, monkeypatch):
    cfg = {"video": {"width": 640, "height": 360, "max_shot_seconds": 5},
           "ai_images": {"enabled": True}}
    scene = {"n": 3, "visual_mode": "broll", "search_terms": ["x"],
             "visual_beats": [{"cue": "c", "purpose": "p", "duration": 4,
                               "search_terms": ["t"]}]}
    monkeypatch.setattr(assets, "_stock_videos", lambda *a, **kw: ([], 0.0))
    monkeypatch.setattr(assets, "_stock_photo", lambda *a, **kw: None)
    monkeypatch.setattr(assets, "_nasa_relevant", lambda terms: False)
    monkeypatch.setattr(assets.ai_images, "generate",
                        lambda *a, **kw: (_ for _ in ()).throw(AssertionError))
    out = assets.fetch_scene_assets(scene, 4.0, str(tmp_path), cfg, "pk", "gk",
                                    set(), set(), [0], rescue_budget=[0])
    assert out and out[0]["path"].endswith("_card.jpg")  # gradient fallback
