"""Semantic long-form visual beat planning and narration-relative timing.

The script model supplies ordered, concrete visual intentions.  This module
keeps that data bounded and maps each cue to the corresponding place in the
finished narration without requiring another paid alignment service.
"""
from __future__ import annotations

import math
import unicodedata


def _tokens(text: str) -> list[str]:
    tokens = []
    for raw in str(text or "").split():
        token = "".join(ch for ch in raw if unicodedata.category(ch)[0] in "LNM"
                        or ch in "’'-").strip("’'-").casefold()
        if token:
            tokens.append(token)
    return tokens


def target_beat_count(scene: dict, cfg: dict, scene_index: int = 0) -> int:
    """Return enough beats to hold the configured visual-change ceiling."""
    quality = cfg.get("longform_quality", {}).get("visual_beats", {})
    wpm = max(float(cfg.get("channel", {}).get("wpm", 130)), 60.0)
    normal_default = float(cfg.get("video", {}).get("max_shot_seconds", 5.0))
    ceiling = float(quality.get(
        "hook_max_seconds" if scene_index == 0 else "max_seconds",
        3.8 if scene_index == 0 else normal_default,
    ))
    words = max(len(_tokens(scene.get("narration", ""))), 1)
    count = math.ceil(words / max(wpm / 60.0 * ceiling, 1.0))
    return max(int(quality.get("min_per_scene", 2)),
               min(int(quality.get("max_per_scene", 12)), count))


def _fallback_beats(scene: dict, count: int) -> list[dict]:
    words = str(scene.get("narration", "")).split()
    terms = [str(t).strip() for t in scene.get("search_terms", []) if str(t).strip()]
    if not terms:
        terms = [str(scene.get("title", "documentary landscape")).strip()]
    beats = []
    for i in range(count):
        at = min(int(i * len(words) / max(count, 1)), max(len(words) - 1, 0))
        cue = " ".join(words[at:at + 6]).strip()
        beats.append({
            "cue": cue,
            "search_terms": [terms[i % len(terms)]],
            "purpose": "fallback visual continuity",
        })
    return beats


def normalize_plan(script: dict, raw_plan: dict | None, cfg: dict) -> dict:
    """Attach a safe beat list to every scene; malformed plans fail open."""
    planned = {}
    if isinstance(raw_plan, dict) and isinstance(raw_plan.get("scenes"), list):
        for item in raw_plan["scenes"]:
            if isinstance(item, dict):
                try:
                    planned[int(item.get("n"))] = item.get("visual_beats", [])
                except (TypeError, ValueError):
                    pass

    for index, scene in enumerate(script.get("scenes", [])):
        target = target_beat_count(scene, cfg, index)
        candidates = planned.get(int(scene.get("n", index + 1)), [])
        clean = []
        for item in candidates if isinstance(candidates, list) else []:
            if not isinstance(item, dict):
                continue
            cue = str(item.get("cue", "")).strip()
            terms = item.get("search_terms", item.get("search_term", []))
            if isinstance(terms, str):
                terms = [terms]
            terms = [str(t).strip() for t in (terms or []) if str(t).strip()][:3]
            if not cue or not terms:
                continue
            clean.append({
                "cue": cue[:140],
                "search_terms": terms,
                "purpose": str(item.get("purpose", ""))[:100],
            })

        # A short model response is worse than a deterministic complete plan.
        if len(clean) < max(2, target - 1):
            clean = _fallback_beats(scene, target)
        elif len(clean) > target + 1:
            clean = clean[:target + 1]
        scene["visual_beats"] = clean
    return script


def _find_subsequence(words: list[str], cue: list[str], after: int) -> int | None:
    if not cue:
        return None
    for i in range(max(after, 0), max(len(words) - len(cue) + 1, 0)):
        if words[i:i + len(cue)] == cue:
            return i
    return None


def time_scene(scene: dict) -> list[dict]:
    """Map ordered cue phrases to relative seconds across rendered narration."""
    beats = scene.get("visual_beats") or []
    if not beats:
        return []
    words = _tokens(scene.get("narration", ""))
    duration = max(float(scene.get("audio_duration", 0.0)), 0.1)
    starts: list[int] = []
    cursor = 0
    for index, beat in enumerate(beats):
        found = _find_subsequence(words, _tokens(beat.get("cue", "")), cursor)
        if found is None:
            found = round(index * len(words) / max(len(beats), 1))
        found = max(cursor, min(found, max(len(words) - 1, 0)))
        starts.append(found)
        cursor = min(found + 1, len(words))
    if starts:
        starts[0] = 0

    timed = []
    for index, beat in enumerate(beats):
        start = duration * starts[index] / max(len(words), 1)
        end_word = starts[index + 1] if index + 1 < len(starts) else len(words)
        end = duration * end_word / max(len(words), 1)
        if index + 1 == len(beats):
            end = duration
        timed.append({**beat, "start": round(start, 3),
                      "duration": round(max(end - start, 0.1), 3)})

    # Eliminate rounding gaps and guarantee exact scene coverage.
    for index in range(1, len(timed)):
        previous_end = timed[index - 1]["start"] + timed[index - 1]["duration"]
        timed[index]["start"] = round(previous_end, 3)
    timed[-1]["duration"] = round(max(duration - timed[-1]["start"], 0.1), 3)
    scene["visual_beats"] = timed
    return timed


def planner_payload(script: dict, cfg: dict) -> list[dict]:
    """Compact scene data for the free visual-planning model call."""
    return [{
        "n": scene.get("n", index + 1),
        "narration": scene.get("narration", ""),
        "scene_search_terms": scene.get("search_terms", []),
        "target_beats": target_beat_count(scene, cfg, index),
    } for index, scene in enumerate(script.get("scenes", []))]
