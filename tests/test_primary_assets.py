from PIL import Image

import assets


def _cfg():
    return {
        "video": {"width": 640, "height": 360, "max_shot_seconds": 5},
        "qc": {"visual_check": True, "max_upscale": 1.25,
               "max_requests_per_video": 10},
        "llm": {"model": "test", "fallback_models": []},
        "visual_director": {"enabled": True},
        "ai_images": {"enabled": True},
    }


def test_commons_asset_keeps_machine_readable_credit(tmp_path, monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"query": {"pages": [{
                "pageid": 123,
                "title": "File:Kuldhara street.jpg",
                "imageinfo": [{
                    "mime": "image/jpeg",
                    "thumburl": "https://upload.wikimedia.org/kuldhara.jpg",
                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:Kuldhara_street.jpg",
                    "extmetadata": {
                        "Artist": {"value": "<b>A. Photographer</b>"},
                        "LicenseShortName": {"value": "CC BY-SA 4.0"},
                        "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                    },
                }],
            }]}}

    monkeypatch.setattr(assets.requests, "get", lambda *a, **kw: Response())

    def download(url, path):
        Image.new("RGB", (640, 360), (190, 145, 90)).save(path)
        return path

    monkeypatch.setattr(assets, "_download", download)
    monkeypatch.setattr(assets, "_visual_ok", lambda *a, **kw: True)
    monkeypatch.setattr(assets.vision_qc, "frame_ok", lambda *a, **kw: True)
    scene = {"n": 2, "search_terms": ["Kuldhara Rajasthan"],
             "narration": "कुलधरा की असली गलियाँ", "forbidden_visuals": []}
    used = set()
    result = assets._commons_asset(scene, str(tmp_path), used, _cfg(), "gk")

    assert result["source"] == "wikimedia"
    assert result["attribution"]["artist"] == "A. Photographer"
    assert result["attribution"]["license"] == "CC BY-SA 4.0"
    assert "w123" in used


def test_primary_beat_uses_commons_before_generic_stock(tmp_path, monkeypatch):
    cfg = _cfg()
    scene = {
        "n": 4,
        "visual_mode": "evidence",
        "search_terms": ["Kuldhara Rajasthan"],
        "visual_beats": [{
            "cue": "कुलधरा की असली गली",
            "purpose": "show the named location",
            "duration": 4,
            "search_terms": ["Kuldhara Rajasthan"],
            "family": "document_focus",
            "source_policy": "primary",
        }],
    }
    authentic = tmp_path / "kuldhara.jpg"
    Image.new("RGB", (640, 360), (180, 130, 70)).save(authentic)
    monkeypatch.setattr(
        assets, "_commons_asset",
        lambda *a, **kw: {"path": str(authentic), "kind": "image",
                          "source": "wikimedia", "attribution": {"title": "Kuldhara"}})
    monkeypatch.setattr(assets, "_nasa_relevant", lambda terms: False)
    monkeypatch.setattr(
        assets, "_stock_videos",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("stock must not run")))
    monkeypatch.setattr(
        assets.ai_images, "generate",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("AI must not run")))

    result = assets.fetch_scene_assets(
        scene, 4, str(tmp_path), cfg, "pk", "gk", set(), set(), [0],
        rescue_budget=[4], director_budget=[4])

    assert result[0]["source"] == "wikimedia"
    assert result[0]["source_policy"] == "primary"
