"""Deterministic motion-library selection for long videos and Shorts.

Every scene receives explicit variants so renders are reproducible, but a new
video title produces a different sequence. Variants cycle before repeating
within a video, preventing the same stat card/frame/lower-third from appearing
twice in succession.
"""
import hashlib


STAT_VARIANTS = ("glass", "split", "radial", "ticker", "stamp", "horizon")
KINETIC_VARIANTS = ("word-pop", "wipe", "stack", "emphasis", "orbit", "split", "marker")
CARD_VARIANTS = ("definition", "quote", "split", "timeline", "warning")
FRAME_VARIANTS = ("corners", "film", "grid", "scanner", "focus", "aperture")
LOWER_THIRD_VARIANTS = ("rail", "pill", "underline", "locator", "index")
CTA_VARIANTS = ("pill", "stamp", "minimal", "orbit")
GLASS_VARIANTS = ("fact", "metric", "location", "chapter", "reveal")


def _offset(seed: str, family: str, size: int) -> int:
    digest = hashlib.sha256(f"{seed}:{family}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % size


def _pick_cycle(items: tuple[str, ...], seed: str, family: str, index: int) -> str:
    return items[(_offset(seed, family, len(items)) + index) % len(items)]


def _pick_glass(scene: dict, seed: str, index: int) -> str:
    """Prefer a layout that matches the data, then fall back to seeded variety."""
    data = scene.get("glass") if isinstance(scene.get("glass"), dict) else {}
    if data.get("coordinates") or data.get("location"):
        return "location"
    if str(scene.get("delivery", "")).lower() == "reveal":
        return "reveal"
    if data.get("chapter"):
        return "chapter"
    if data.get("value") is not None:
        return "metric"
    return _pick_cycle(("fact", "chapter"), seed, "glass", index)


def decorate_scenes(scenes: list[dict], seed: str) -> None:
    """Attach a complete variant set to every scene, mutating scenes in place."""
    use_index = {"stat": 0, "kinetic": 0, "card": 0, "glass": 0,
                 "lower-third": 0}
    for index, scene in enumerate(scenes):
        mode = str(scene.get("visual_mode", "broll"))
        scene["motion"] = {
            "statVariant": _pick_cycle(
                STAT_VARIANTS, seed, "stat", use_index["stat"]),
            "kineticVariant": _pick_cycle(
                KINETIC_VARIANTS, seed, "kinetic", use_index["kinetic"]),
            "cardVariant": _pick_cycle(
                CARD_VARIANTS, seed, "card", use_index["card"]),
            "frameVariant": _pick_cycle(FRAME_VARIANTS, seed, "frame", index),
            "lowerThirdVariant": _pick_cycle(
                LOWER_THIRD_VARIANTS, seed, "lower-third", use_index["lower-third"]),
            "glassVariant": _pick_glass(scene, seed, use_index["glass"]),
        }
        if mode in ("stat", "kinetic", "card", "glass"):
            use_index[mode] += 1
        if mode not in ("stat", "kinetic", "card", "glass", "map"):
            use_index["lower-third"] += 1


def plan_cta(scenes: list[dict], cfg: dict, seed: str,
             is_short: bool = False) -> dict | None:
    """Plan one unobtrusive subscribe/bell animation per video."""
    mc = cfg.get("motion_library", {})
    if not mc.get("enabled", True) or not mc.get("cta_enabled", True):
        return None
    if is_short and not mc.get("cta_in_shorts", True):
        return None
    if not scenes:
        return None

    # Long-form: late middle, after value has been delivered. Shorts: brief
    # mid-video chip so the loop ending remains clean.
    index = max(0, min(len(scenes) - 1,
                       int(len(scenes) * (0.58 if is_short else 0.68))))
    scene = scenes[index]
    scene_start = float(scene.get("start", 0.0))
    scene_duration = float(scene.get("audio_duration", 3.0))
    duration = float(mc.get("cta_short_seconds", 1.8) if is_short
                     else mc.get("cta_seconds", 3.2))
    local_start = min(max(scene_duration * 0.30, 0.25),
                      max(scene_duration - duration - 0.2, 0.25))
    return {
        "start": round(scene_start + local_start, 3),
        "duration": round(min(duration, max(scene_duration - local_start, 1.0)), 3),
        "variant": _pick_cycle(CTA_VARIANTS, seed, "cta", 0),
        "title": str(mc.get("cta_title", "सब्सक्राइब करें")),
        "subtitle": str(mc.get("cta_subtitle", "नई खोजें हर हफ्ते")),
        "compact": bool(is_short),
    }
