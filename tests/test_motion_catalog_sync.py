import pathlib
import re

import motion
import sfx


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _tsx_catalog() -> dict[str, tuple[str, ...]]:
    source = (ROOT / "remotion" / "src" / "motion-library.tsx").read_text(
        encoding="utf-8")
    result = {}
    for key in ("stats", "kinetic", "cards", "frames", "lowerThirds", "ctas", "glass"):
        match = re.search(rf"\b{key}:\s*\[([^\]]*)\]", source)
        assert match, f"missing renderer catalog family: {key}"
        result[key] = tuple(re.findall(r"'([^']+)'", match.group(1)))
    return result


def test_renderer_and_pipeline_catalogs_stay_in_sync():
    catalog = _tsx_catalog()
    assert catalog == {
        "stats": motion.STAT_VARIANTS,
        "kinetic": motion.KINETIC_VARIANTS,
        "cards": motion.CARD_VARIANTS,
        "frames": motion.FRAME_VARIANTS,
        "lowerThirds": motion.LOWER_THIRD_VARIANTS,
        "ctas": motion.CTA_VARIANTS,
        "glass": motion.GLASS_VARIANTS,
    }


def test_every_glass_variant_has_a_sound_pairing():
    assert set(sfx.GLASS_SFX) == set(motion.GLASS_VARIANTS)
    assert set(sfx.GLASS_SFX.values()) <= set(sfx.SOUND_CATALOG)
