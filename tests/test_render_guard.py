"""Render guard: a manifest asset whose file vanished/corrupted must never
reach Remotion (it 404s mid-render and kills the whole video — observed on
Make Short at frame 1236, s06_*.mp4)."""
import os

import pytest

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


def test_gradient_beat_fallback_borrows_nearest_real_visual(tmp_path):
    first = tmp_path / "first.jpg"
    first.write_bytes(b"a" * 5000)
    gradient = tmp_path / "s01_b01_card.jpg"
    gradient.write_bytes(b"b" * 5000)
    later = tmp_path / "later.jpg"
    later.write_bytes(b"c" * 5000)
    scenes = [{
        "n": 1,
        "visual_mode": "broll",
        "assets": [
            {"path": str(first), "kind": "image", "beat_index": 0},
            {"path": str(gradient), "kind": "image", "beat_index": 1,
             "fallback": "gradient", "source_policy": "custom"},
            {"path": str(later), "kind": "image", "beat_index": 3},
        ],
    }]

    run._validate_scene_assets(scenes)

    repaired = next(a for a in scenes[0]["assets"]
                    if a.get("beat_index") == 1)
    assert repaired["path"] == str(first)
    assert repaired["borrowed_fallback"] is True
    assert repaired["source_policy"] == "custom"


def test_empty_first_scene_borrows_from_future_scene(tmp_path):
    future = tmp_path / "future.jpg"
    future.write_bytes(b"f" * 5000)
    scenes = [
        {"n": 1, "visual_mode": "broll", "visual_beats": [
            {"cue": "opening", "search_terms": ["ship"]},
        ], "assets": []},
        {"n": 2, "visual_mode": "broll",
         "assets": [{"path": str(future), "kind": "image",
                     "beat_index": 0}]},
    ]

    run._validate_scene_assets(scenes)

    assert scenes[0]["assets"][0]["path"] == str(future)
    assert scenes[0]["assets"][0]["beat_index"] == 0
    assert scenes[0]["assets"][0]["borrowed_fallback"] is True


def test_episode_wide_media_outage_gets_programmatic_visual_per_beat():
    scenes = [{
        "n": 1,
        "visual_mode": "broll",
        "visual_beats": [
            {"cue": "first clue", "search_terms": ["cargo"]},
            {"cue": "second clue", "search_terms": ["lifeboat"]},
        ],
        "assets": [],
    }]

    run._validate_scene_assets(scenes)

    assert {a["beat_index"] for a in scenes[0]["assets"]} == {0, 1}
    assert all(a["kind"] == "graphic" for a in scenes[0]["assets"])
    assert all(a["fallback"] == "programmatic"
               for a in scenes[0]["assets"])


def test_pre_render_guard_rejects_empty_or_gradient_visual_pool():
    empty = {"fps": 30, "scenes": [{
        "n": 1, "audioDuration": 2, "visualMode": "broll",
        "assets": [], "visualBeats": [],
    }]}
    with pytest.raises(RuntimeError, match="no visual assets"):
        run._assert_render_visual_coverage(empty)

    gradient = {"fps": 30, "scenes": [{
        "n": 1, "audioDuration": 2, "visualMode": "broll",
        "assets": [{"path": "s01_b00_card.jpg", "kind": "image",
                    "fallback": "gradient"}],
        "visualBeats": [{"fromFrame": 0, "durationFrames": 60,
                         "assets": []}],
    }]}
    with pytest.raises(RuntimeError, match="blank gradient"):
        run._assert_render_visual_coverage(gradient)


def test_pre_render_guard_accepts_complete_programmatic_fallback():
    manifest = {"fps": 30, "scenes": [{
        "n": 1, "audioDuration": 2, "visualMode": "broll",
        "assets": [{"path": "s01_b00_fallback_graphic", "kind": "graphic",
                    "fallback": "programmatic"}],
        "visualBeats": [{"fromFrame": 0, "durationFrames": 60,
                         "assets": []}],
    }]}

    run._assert_render_visual_coverage(manifest)


def test_pre_render_guard_accepts_map_as_frame_filling_visual():
    manifest = {"fps": 30, "scenes": [{
        "n": 1, "audioDuration": 2, "visualMode": "map", "assets": [],
        "visualBeats": [{"fromFrame": 0, "durationFrames": 60,
                         "assets": []}],
    }]}

    run._assert_render_visual_coverage(manifest)


def test_any_render_substitution_forces_release_review():
    assert run._render_fallbacks_require_review([{
        "assets": [{"kind": "graphic", "fallback": "programmatic"}],
    }]) is True
    assert run._render_fallbacks_require_review([{
        "assets": [{"kind": "image", "borrowed_fallback": True}],
    }]) is True
    assert run._render_fallbacks_require_review([{
        "assets": [{"kind": "image", "path": "real.jpg"}],
    }]) is False
