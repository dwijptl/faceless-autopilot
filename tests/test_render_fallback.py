"""Regression: the MoviePy fallback renderer must not divide by zero when a
scene arrives with no assets.

Map scenes intentionally return an empty asset list from
assets.fetch_scene_assets (Remotion's MapZoom draws its own background). When
Remotion fails and run.py falls back to render.render, _scene_visual used to do
`assets[i % len(assets)]` on that empty list and crash with:

    ZeroDivisionError: integer modulo by zero
"""
import random

import pytest

render = pytest.importorskip("render")

CFG = {"video": {"width": 1920, "height": 1080, "max_shot_seconds": 5}}


def test_empty_assets_does_not_divide_by_zero():
    # Before the fix this raised ZeroDivisionError.
    visual = render._scene_visual([], 3.0, CFG, random.Random(42))
    try:
        assert visual.duration == pytest.approx(3.0)
        assert visual.w == CFG["video"]["width"]
        assert visual.h == CFG["video"]["height"]
    finally:
        visual.close()


def test_fallback_gradient_frame_shape_and_dtype():
    frame = render._gradient_frame(320, 180, seed=7)
    assert frame.shape == (180, 320, 3)   # (h, w, 3)
    assert frame.dtype.name == "uint8"


def test_non_empty_assets_still_uses_assets(tmp_path, monkeypatch):
    # A populated scene must NOT take the fallback path.
    calls = {"fallback": 0, "ken_burns": 0}
    monkeypatch.setattr(render, "_fallback_visual",
                        lambda *a, **k: calls.__setitem__("fallback", calls["fallback"] + 1))

    def fake_ken_burns(path, duration, w, h, zoom_in):
        calls["ken_burns"] += 1
        # Return a real, cheap clip so concatenation/duration logic runs.
        import numpy as np
        from moviepy import ImageClip
        return ImageClip(np.zeros((h, w, 3), "uint8")).with_duration(duration)

    monkeypatch.setattr(render, "_ken_burns", fake_ken_burns)
    assets = [{"path": str(tmp_path / "a.png"), "kind": "image"}]
    visual = render._scene_visual(assets, 3.0, CFG, random.Random(1))
    try:
        assert calls["fallback"] == 0
        assert calls["ken_burns"] >= 1
    finally:
        visual.close()
