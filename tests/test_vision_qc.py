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
