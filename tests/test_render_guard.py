"""The render guard permits only real images and videos."""

import pytest

import run


def _media(path, kind="image", beat_index=0):
    path.write_bytes(b"x" * 5000)
    return {"path": str(path), "kind": kind, "beat_index": beat_index}


def test_missing_asset_is_replaced_with_nearest_real_media(tmp_path):
    good = _media(tmp_path / "good.jpg")
    scenes = [
        {"n": 1, "assets": [good]},
        {"n": 2, "assets": [
            {"path": str(tmp_path / "missing.jpg"), "kind": "image"},
        ]},
    ]

    run._validate_scene_assets(scenes)

    replacement = scenes[1]["assets"][0]
    assert replacement["path"] == good["path"]
    assert replacement["borrowed_fallback"] is True


def test_empty_first_scene_borrows_from_future_scene_for_each_beat(tmp_path):
    future = _media(tmp_path / "future.jpg")
    scenes = [
        {"n": 1, "visual_beats": [
            {"cue": "one", "search_terms": ["ship"]},
            {"cue": "two", "search_terms": ["sea"]},
        ], "assets": []},
        {"n": 2, "assets": [future]},
    ]

    run._validate_scene_assets(scenes)

    assert {a["beat_index"] for a in scenes[0]["assets"]} == {0, 1}
    assert all(a["kind"] == "image" for a in scenes[0]["assets"])
    assert all(a["borrowed_fallback"] for a in scenes[0]["assets"])


def test_episode_wide_media_outage_stops_instead_of_creating_template():
    scenes = [{"n": 1, "visual_beats": [{"cue": "clue"}], "assets": []}]

    with pytest.raises(RuntimeError, match="No full-frame image or video"):
        run._validate_scene_assets(scenes)


def test_graphic_asset_is_dropped_and_never_reaches_manifest(tmp_path):
    real = _media(tmp_path / "real.jpg")
    scenes = [{"n": 1, "assets": [
        {"path": "old-template", "kind": "graphic", "graphic": {"kind": "chart"}},
        real,
    ]}]

    run._validate_scene_assets(scenes)

    assert scenes[0]["assets"] == [real]


def test_gradient_fallback_is_replaced_by_nearest_real_media(tmp_path):
    first = _media(tmp_path / "first.jpg", beat_index=0)
    gradient = _media(tmp_path / "s01_b01_card.jpg", beat_index=1)
    gradient["fallback"] = "gradient"
    scenes = [{"n": 1, "assets": [first, gradient]}]

    run._validate_scene_assets(scenes)

    repaired = next(a for a in scenes[0]["assets"] if a["beat_index"] == 1)
    assert repaired["path"] == first["path"]
    assert repaired["borrowed_fallback"] is True


def test_pre_render_guard_rejects_empty_gradient_and_graphic_pools():
    empty = {"fps": 30, "scenes": [{
        "n": 1, "audioDuration": 2, "assets": [], "visualBeats": [],
    }]}
    with pytest.raises(RuntimeError, match="no visual assets"):
        run._assert_render_visual_coverage(empty)

    gradient = {"fps": 30, "scenes": [{
        "n": 1, "audioDuration": 2,
        "assets": [{"path": "s01_b00_card.jpg", "kind": "image",
                    "fallback": "gradient"}],
        "visualBeats": [{"fromFrame": 0, "durationFrames": 60, "assets": []}],
    }]}
    with pytest.raises(RuntimeError, match="blank gradient"):
        run._assert_render_visual_coverage(gradient)

    graphic = {"fps": 30, "scenes": [{
        "n": 1, "audioDuration": 2,
        "assets": [{"path": "old-template", "kind": "graphic"}],
        "visualBeats": [{"fromFrame": 0, "durationFrames": 60, "assets": []}],
    }]}
    with pytest.raises(RuntimeError, match="forbidden visual kind"):
        run._assert_render_visual_coverage(graphic)


def test_borrowed_media_forces_release_review():
    assert run._render_fallbacks_require_review([{
        "assets": [{"kind": "image", "borrowed_fallback": True}],
    }]) is True
    assert run._render_fallbacks_require_review([{
        "assets": [{"kind": "image", "path": "real.jpg"}],
    }]) is False


def test_plain_number_is_synced_to_its_spoken_timestamp():
    scene = {
        "visual_mode": "stat",
        "stat": {"value": 42, "label": "उत्तर"},
        "audio_duration": 5.0,
        "word_times": [("यह", 0.1, 0.3), ("42", 1.4, 1.7)],
    }
    assert run._impact_start(scene, 3.2) == pytest.approx(1.28)
    scene["visual_mode"] = "broll"
    assert run._impact_start(scene, 3.2) == 0.0
