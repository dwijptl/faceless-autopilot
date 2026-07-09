"""AI image generation via Gemini image models (free tier: ~500 req/day).

Used for scenes where stock footage can't express the visual. Any failure
returns False and the caller falls back to stock — the pipeline never blocks
on this module.
"""
import base64
import json
import os
import time

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

STYLE_SUFFIX = (
    " Cinematic documentary still, photorealistic, dramatic natural light, "
    "{aspect} composition, high detail, no text, no watermarks, no borders."
)


def generate(prompt: str, out_path: str, api_key: str, cfg: dict,
             aspect: str = "16:9 wide") -> bool:
    aicfg = cfg.get("ai_images", {})
    if not aicfg.get("enabled", True):
        return False
    models = [aicfg.get("model", "gemini-2.5-flash-image")] + list(
        aicfg.get("fallback_models", []))

    suffix = STYLE_SUFFIX.format(aspect=aspect)
    body = {
        "contents": [{"parts": [{"text": prompt.strip() + suffix}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    for model in models:
        url = f"{API_BASE}/{model}:generateContent?key={api_key}"
        for attempt in range(2):
            try:
                r = requests.post(url, json=body, timeout=180)
                if r.status_code == 429:
                    time.sleep(25 * (attempt + 1))
                    continue
                if r.status_code in (400, 404):
                    break  # model gone/renamed -> next model
                r.raise_for_status()
                data = r.json()
                parts = data["candidates"][0]["content"]["parts"]
                for p in parts:
                    inline = p.get("inlineData") or p.get("inline_data")
                    if inline and inline.get("data"):
                        with open(out_path, "wb") as f:
                            f.write(base64.b64decode(inline["data"]))
                        if os.path.getsize(out_path) > 20_000:
                            print(f"[ai-img] generated via {model}: {prompt[:60]}...")
                            return True
                break  # no image part -> next model
            except (requests.RequestException, KeyError, IndexError,
                    json.JSONDecodeError) as e:
                print(f"[ai-img] {model} attempt {attempt + 1} failed: {e}")
                time.sleep(5)
    print("[ai-img] all models failed — falling back to stock")
    return False
