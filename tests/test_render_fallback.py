"""The emergency MoviePy renderer must never create a visual template."""

import random

import pytest

render = pytest.importorskip("render")

CFG = {"video": {"width": 1920, "height": 1080, "max_shot_seconds": 5}}


def test_empty_assets_fail_clearly():
    with pytest.raises(RuntimeError, match="real image or video"):
        render._scene_visual([], 3.0, CFG, random.Random(42))


def test_non_empty_image_uses_full_frame_media(tmp_path, monkeypatch):
    calls = {"ken_burns": 0}

    def fake_ken_burns(path, duration, w, h, zoom_in):
        calls["ken_burns"] += 1
        import numpy as np
        from moviepy import ImageClip
        return ImageClip(np.zeros((h, w, 3), "uint8")).with_duration(duration)

    monkeypatch.setattr(render, "_ken_burns", fake_ken_burns)
    assets = [{"path": str(tmp_path / "a.png"), "kind": "image"}]
    visual = render._scene_visual(assets, 3.0, CFG, random.Random(1))
    try:
        assert calls["ken_burns"] >= 1
    finally:
        visual.close()


def test_graphic_kind_is_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="Unsupported visual kind"):
        render._scene_visual(
            [{"path": str(tmp_path / "old"), "kind": "graphic"}],
            1.0, CFG, random.Random(1))
