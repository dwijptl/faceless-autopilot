import os

import motion
import sfx


def _scenes(count=8):
    modes = ["broll", "stat", "kinetic", "map", "glass", "broll", "stat", "kinetic"]
    return [{"n": i + 1, "start": i * 4.0, "audio_duration": 4.2,
             "visual_mode": modes[i % len(modes)]} for i in range(count)]


def test_motion_variants_cycle_before_repeating():
    scenes = _scenes()
    motion.decorate_scenes(scenes, "video-title:documentary")
    assert len({s["motion"]["frameVariant"] for s in scenes[:6]}) == 6
    assert all(set(s["motion"]) == {"statVariant", "kineticVariant", "cardVariant",
                                    "frameVariant", "lowerThirdVariant", "glassVariant"}
               for s in scenes)

    for mode, key, count in (
        ("stat", "statVariant", len(motion.STAT_VARIANTS)),
        ("kinetic", "kineticVariant", len(motion.KINETIC_VARIANTS)),
        ("card", "cardVariant", len(motion.CARD_VARIANTS)),
    ):
        family_scenes = [{"n": i + 1, "visual_mode": mode} for i in range(count)]
        motion.decorate_scenes(family_scenes, "video-title:documentary")
        assert len({s["motion"][key] for s in family_scenes}) == count


def test_variant_counters_ignore_unrelated_scenes():
    scenes = [{"n": 1, "visual_mode": "stat"}]
    scenes.extend({"n": i + 2, "visual_mode": "broll"} for i in range(6))
    scenes.append({"n": 8, "visual_mode": "stat"})
    motion.decorate_scenes(scenes, "spaced-stats")
    assert scenes[0]["motion"]["statVariant"] != scenes[-1]["motion"]["statVariant"]


def test_glass_selection_matches_scene_data():
    scenes = [
        {"visual_mode": "glass", "glass": {"location": "x", "coordinates": "1N"}},
        {"visual_mode": "glass", "glass": {"value": 42}},
        {"visual_mode": "glass", "glass": {"chapter": "भाग 2"}},
        {"visual_mode": "glass", "delivery": "reveal", "glass": {"headline": "x"}},
    ]
    motion.decorate_scenes(scenes, "semantic-glass")
    assert [s["motion"]["glassVariant"] for s in scenes] == [
        "location", "metric", "chapter", "reveal"]


def test_cta_is_planned_inside_a_scene_for_both_formats():
    scenes = _scenes()
    cfg = {"motion_library": {"enabled": True, "cta_enabled": True,
                              "cta_in_shorts": True}}
    long_cta = motion.plan_cta(scenes, cfg, "long", is_short=False)
    short_cta = motion.plan_cta(scenes, cfg, "short", is_short=True)
    assert long_cta and short_cta
    assert long_cta["variant"] in motion.CTA_VARIANTS
    assert short_cta["compact"] is True
    assert 0 <= long_cta["start"] < scenes[-1]["start"] + scenes[-1]["audio_duration"]


def test_sound_pack_is_complete_and_events_use_scene_roles(tmp_path):
    pack = sfx.build_pack(str(tmp_path))
    assert set(pack) == set(sfx.SOUND_CATALOG)
    assert all(os.path.getsize(tmp_path / filename) > 500
               for filename in pack.values())

    scenes = _scenes(5)
    cfg = {"sfx": {"enabled": True, "volume": .5},
           "render": {"style_pack": "kinetic"}}
    cta = {"start": 8.0}
    events = sfx.plan_events(scenes, cfg, str(tmp_path), cta)
    used = {event["path"] for event in events}
    for expected in ("sfx_bell.wav", "sfx_tick.wav", "sfx_pulse.wav",
                     "sfx_sparkle.wav", "sfx_glitch.wav", "sfx_ui_blip.wav"):
        assert expected in used
