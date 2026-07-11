"""Pre-render visual QC — kills the "AI slop" class of errors.

Before a downloaded stock clip/photo is accepted, one frame goes to Gemini
vision (free tier) with the scene's narration: does this footage plausibly
illustrate it for a nature/space documentary? Rejects studio, commercial,
product, zoo-enclosure and metaphor shots that keyword search sneaks in.

FAIL-OPEN by design: any error/timeout accepts the asset — QC must never
block a scheduled run.
"""
import base64
import io
import json
import os
import re
import subprocess
import time

import requests
from PIL import Image

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_requests_remaining: int | None = None


def begin_run(cfg: dict) -> None:
    """Reset the per-video vision budget so QC cannot consume a free tier."""
    global _requests_remaining
    _requests_remaining = max(0, int(cfg.get("qc", {}).get("max_requests_per_video", 20)))


def _duration(path: str) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, check=True, timeout=30)
        return float(result.stdout.strip())
    except Exception:
        return None


def _frame_jpegs_b64(media_path: str, kind: str, frames: int) -> list[str]:
    try:
        if kind == "video":
            duration = _duration(media_path)
            if not duration:
                return []
            # 20/50/80% avoids both opening slates and end cards.
            positions = [duration * (i + 1) / (frames + 1)
                         for i in range(max(1, frames))]
            images = []
            for pos in positions:
                result = subprocess.run(
                    ["ffmpeg", "-v", "error", "-ss", f"{pos:.3f}", "-i", media_path,
                     "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"],
                    check=True, timeout=60, capture_output=True)
                images.append(Image.open(io.BytesIO(result.stdout)).convert("RGB"))
        else:
            images = [Image.open(media_path).convert("RGB")]
        encoded = []
        for img in images:
            img.thumbnail((512, 512))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            encoded.append(base64.b64encode(buf.getvalue()).decode())
        return encoded
    except Exception:
        return []


def frame_ok(media_path: str, kind: str, scene_desc: str, search_term: str,
             api_key: str, cfg: dict) -> bool:
    """True = accept the asset. Fail-open on any problem."""
    global _requests_remaining
    if not cfg.get("qc", {}).get("visual_check", True) or not api_key:
        return True
    if _requests_remaining is None:
        begin_run(cfg)
    if _requests_remaining <= 0:
        print("[qc] budget exhausted; accepting without vision check")
        return True
    images = _frame_jpegs_b64(media_path, kind, int(cfg.get("qc", {}).get("frames", 3)))
    if not images:
        return True
    prompt = (
        "You are the visual editor of a premium nature/space documentary "
        "channel. These frames were fetched for the scene below.\n"
        f'SCENE NARRATION (Hindi): "{scene_desc[:280]}"\n'
        f'SEARCH INTENT: "{search_term}"\n'
        "ACCEPT only if the footage plausibly belongs in this documentary "
        "scene. REJECT if it is: studio/commercial/product imagery, food or "
        "beverages, offices, hands/typing, captive animals (zoo, enclosure, "
        "fences), text-heavy graphics, or clearly unrelated to the scene.\n"
        'Answer ONLY JSON: {"match": true} or {"match": false, "reason": "<5 words>"}')
    parts = [{"inline_data": {"mime_type": "image/jpeg", "data": image}}
             for image in images]
    parts.append({"text": prompt})
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"response_mime_type": "application/json",
                             "temperature": 0.1},
    }
    models = [cfg["llm"].get("model", "gemini-2.5-flash")] + list(
        cfg["llm"].get("fallback_models", []))
    for model in models[:2]:
        try:
            _requests_remaining -= 1
            r = requests.post(f"{API_BASE}/{model}:generateContent?key={api_key}",
                              json=body, timeout=45)
            if r.status_code == 429:
                time.sleep(10)
                continue
            if r.status_code in (400, 404):
                continue
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = re.sub(r"^```(json)?|```$", "", text.strip(),
                          flags=re.MULTILINE).strip()
            verdict = json.loads(text)
            if verdict.get("match") is False:
                print(f"[qc] REJECTED ({verdict.get('reason', '?')}): "
                      f"{os.path.basename(media_path)}")
                return False
            return True
        except Exception:
            return True  # fail-open
    return True
