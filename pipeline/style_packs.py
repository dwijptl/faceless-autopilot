"""Single restrained photographic direction for every video."""

import json
import os


PACKS = {
    "documentary": {
        "base": "documentary",
        "wrapper": (
            "restrained factual documentary photography, natural light, "
            "realistic materials, accurate location detail, full-frame composition"
        ),
        "camera": "slow restrained documentary push-in",
    },
}

PACING = {"documentary": {"pace": 1.0, "chunk": 1.0}}


def base_for(_name: str) -> str:
    return "documentary"


def wrapper_for(_name: str) -> str:
    return PACKS["documentary"]["wrapper"]


def camera_for(_name: str) -> str:
    return PACKS["documentary"]["camera"]


def select(_topic: str, history: list[str] | None = None) -> str:
    return "documentary"


def select_and_log(topic: str, _description: str, root: str,
                   is_short: bool = False) -> str:
    name = select(topic)
    record_use(name, root, is_short=is_short)
    return name


def history_path(root: str, is_short: bool = False) -> str:
    filename = "style_history_shorts.json" if is_short else "style_history.json"
    return os.path.join(root, filename)


def recent_styles(path: str, n: int = 3) -> list[str]:
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
        return [str(x) for x in raw][-n:]
    except (OSError, ValueError, TypeError):
        return []


def record_style(path: str, name: str) -> None:
    history = recent_styles(path, n=20)
    history.append("documentary" if name != "documentary" else name)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(history[-20:], handle)


def record_use(name: str, root: str, is_short: bool = False) -> None:
    record_style(history_path(root, is_short), name)


def render_jitter(_seed: str) -> dict:
    """Compatibility helper with no visual-style variation."""
    return {"xfade_mul": 1.0, "max_shot_mul": 1.0, "overlay_mul": 1.0,
            "caption_y_off": 0.0, "watermark_off": 0.0}


def apply_pacing(_cfg: dict, _name: str, is_short: bool = False) -> None:
    return None


def frames_for(_name: str) -> tuple:
    return ()


def lower_thirds_for(_name: str) -> tuple:
    return ()
