import vision_qc


class _Response:
    status_code = 200
    def raise_for_status(self):
        return None
    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": '{"match": false, "reason": "zoo"}'}]}}]}


def test_multi_frame_qc_rejects_bad_asset(monkeypatch):
    monkeypatch.setattr(vision_qc, "_frame_jpegs_b64", lambda *args: ["a", "b", "c"])
    monkeypatch.setattr(vision_qc.requests, "post", lambda *args, **kwargs: _Response())
    cfg = {"qc": {"visual_check": True, "frames": 3, "max_requests_per_video": 2},
           "llm": {"model": "test", "fallback_models": []}}
    vision_qc.begin_run(cfg)
    assert not vision_qc.frame_ok("x.mp4", "video", "scene", "term", "key", cfg)


def test_qc_fails_open_when_disabled():
    assert vision_qc.frame_ok("x", "video", "scene", "term", "", {"qc": {"visual_check": False}})


def test_uninspectable_stock_fails_closed(monkeypatch):
    monkeypatch.setattr(vision_qc, "_frame_jpegs_b64", lambda *args: [])
    cfg = {"qc": {"visual_check": True, "max_requests_per_video": 2},
           "llm": {"model": "test", "fallback_models": []}}
    vision_qc.begin_run(cfg)
    assert not vision_qc.frame_ok(
        "broken.mp4", "video", "scene", "term", "key", cfg,
        source="stock")
    assert vision_qc.frame_ok(
        "generated.png", "image", "scene", "term", "key", cfg,
        source="generated")


def test_stock_provider_error_fails_closed(monkeypatch):
    monkeypatch.setattr(vision_qc, "_frame_jpegs_b64", lambda *args: ["frame"])
    monkeypatch.setattr(
        vision_qc.requests, "post",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("provider down")))
    cfg = {"qc": {"visual_check": True, "max_requests_per_video": 2},
           "llm": {"model": "test", "fallback_models": []}}
    vision_qc.begin_run(cfg)
    assert not vision_qc.frame_ok(
        "stock.jpg", "image", "scene", "term", "key", cfg,
        source="stock")
