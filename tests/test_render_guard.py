"""Render guard: a manifest asset whose file vanished/corrupted must never
reach Remotion (it 404s mid-render and kills the whole video — observed on
Make Short at frame 1236, s06_*.mp4)."""
import os

import run


def test_missing_asset_dropped_and_neighbor_borrowed(tmp_path):
    good = tmp_path / "good.mp4"
    good.write_bytes(b"x" * 5000)
    scenes = [
        {"n": 1, "visual_mode": "broll",
         "assets": [{"path": str(good), "kind": "video"}]},
        {"n": 2, "visual_mode": "broll",
         "assets": [{"path": str(tmp_path / "vanished.mp4"), "kind": "video"}]},
    ]
    run._validate_scene_assets(scenes)
    assert scenes[1]["assets"], "scene 2 must not render from nothing"
    assert scenes[1]["assets"][0]["path"] == str(good)


def test_zero_byte_asset_treated_as_missing(tmp_path):
    empty = tmp_path / "trunc.mp4"
    empty.write_bytes(b"")               # truncated download
    scenes = [{"n": 1, "visual_mode": "map",
               "assets": [{"path": str(empty), "kind": "video"}]}]
    run._validate_scene_assets(scenes)
    assert scenes[0]["assets"] == []     # map scene has no neighbor to borrow
