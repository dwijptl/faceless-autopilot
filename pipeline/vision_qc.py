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
import tempfile
import time

import requests
from PIL import Image

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _frame_jpeg_b64(media_path: str, kind: str) -> str | None:
    try:
        if kind == "video":
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            tmp.close()
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", "1.5", "-i", media_path,
                 "-frames:v", "1", "-q:v", "5", tmp.name],
                check=True, timeout=60)
            img = Image.open(tmp.name).convert("RGB")
            os.unlink(tmp.name)
        else:
            img = Image.open(media_path).convert("RGB")
        img.thumbnail((512, 512))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def frame_ok(media_path: str, kind: str, scene_desc: str, search_term: str,
             api_key: str, cfg: dict) -> bool:
    """True = accept the asset. Fail-open on any problem."""
    if not cfg.get("qc", {}).get("visual_check", True) or not api_key:
        return True
    b64 = _frame_jpeg_b64(media_path, kind)
    if not b64:
        return True
    prompt = (
        "You are the visual editor of a premium nature/space documentary "
        "channel. This frame was fetched for the scene below.\n"
        f'SCENE NARRATION (Hindi): "{scene_desc[:280]}"\n'
        f'SEARCH INTENT: "{search_term}"\n'
        "ACCEPT only if the footage plausibly belongs in this documentary "
        "scene. REJECT if it is: studio/commercial/product imagery, food or "
        "beverages, offices, hands/typing, captive animals (zoo, enclosure, "
        "fences), text-heavy graphics, or clearly unrelated to the scene.\n"
        'Answer ONLY JSON: {"match": true} or {"match": false, "reason": "<5 words>"}')
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
            {"text": prompt},
        ]}],
        "generationConfig": {"response_mime_type": "application/json",
                             "temperature": 0.1},
    }
    models = [cfg["llm"].get("model", "gemini-2.5-flash")] + list(
        cfg["llm"].get("fallback_models", []))
    for model in models[:2]:
        try:
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
