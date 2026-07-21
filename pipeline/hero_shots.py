"""Animated hero shots — Kling image-to-video via the fal queue API.

Animates the FLUX still of the hook's first beat and the reveal scene so the
two moments that decide retention move like footage instead of a Ken Burns
pan. The source still stays in the timeline, so a QC rejection costs nothing:
the beat simply ships the image it already had (docs/HERO_SHOTS_SPEC.md).

Fail-open everywhere. Hard cost gate: `hero_shots.max_usd_per_video`.
"""
import base64
import io
import json
import os
import re
import subprocess
import time

import requests

QUEUE_RUN = "https://queue.fal.run/{model}"
PRICE_PER_SECOND_USD = 0.07          # Kling 2.6 Pro i2v, audio off (fal.ai)
POLL_SECONDS = 10
TIMEOUT_SECONDS = 480                # 8 min per generation, then give up

# i2v models can't do talking faces, hands, readable text or precise
# mechanisms — if the beat is about those, the still is the better shot.
SKIP_RE = re.compile(
    r"face|चेहरा|hand|हाथ|text|लिख|अक्षर|diagram|आरेख|chart|चार्ट|graph",
    re.IGNORECASE)

# Per-style-pack camera grammar lives in style_packs.PACKS (one camera
# move per pack — matches ai_images wrappers).
import style_packs

NEGATIVE = ("text, watermark, morphing, warping, extra limbs, "
            "distorted faces, objects appearing from nowhere, flickering")

_spent_usd = 0.0                     # cost telemetry (module-global, per run)
_accepted = 0
_retries = 0


def begin_run() -> None:
    """Reset per-video telemetry (mirror of vision_qc.begin_run)."""
    global _spent_usd, _accepted, _retries
    _spent_usd, _accepted, _retries = 0.0, 0, 0


def should_skip(cue: str) -> bool:
    """True when the beat needs things i2v reliably breaks."""
    return bool(SKIP_RE.search(cue or ""))


def motion_prompt(cue: str, cfg: dict) -> str:
    pack = str(cfg.get("render", {}).get("style_pack", "documentary"))
    camera = style_packs.camera_for(pack)
    return (f"{(cue or '').strip()}. {camera}, slow cinematic movement, "
            "consistent lighting, no new objects entering frame")


def _still_data_uri(path: str) -> str | None:
    """Re-encode the still to JPEG q85 — keeps the request body small."""
    try:
        from PIL import Image
        buf = io.BytesIO()
        Image.open(path).convert("RGB").save(buf, "JPEG", quality=85)
        raw = buf.getvalue()
    except Exception:
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError:
            return None
    if not raw:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()


def _clip_ok(path: str, seconds: int) -> bool:
    try:
        if os.path.getsize(path) < 200_000:
            return False
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60, check=True)
        return float(json.loads(out.stdout)["format"]["duration"]) >= seconds - 0.5
    except Exception:
        return True  # probe hiccup — trust the download


def _download(url: str, out_path: str) -> bool:
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return os.path.getsize(out_path) > 0


def _run_queue(model: str, body: dict, out_path: str, key: str,
               seconds: int) -> bool:
    """Submit to the fal queue, poll, download. One model, one attempt."""
    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    r = requests.post(QUEUE_RUN.format(model=model), json=body,
                      headers=headers, timeout=120)
    if r.status_code in (401, 403):
        print(f"[hero] fal auth failed — check FAL_KEY: {r.text[:200]}")
        return False
    r.raise_for_status()
    job = r.json()
    status_url = job.get("status_url")
    response_url = job.get("response_url")
    if not status_url or not response_url:
        return False
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        s = requests.get(status_url, headers=headers, timeout=60)
        s.raise_for_status()
        status = (s.json().get("status") or "").upper()
        if status == "COMPLETED":
            res = requests.get(response_url, headers=headers, timeout=120)
            res.raise_for_status()
            video = (res.json().get("video") or {})
            url = video.get("url")
            return bool(url) and _download(url, out_path) \
                and _clip_ok(out_path, seconds)
        if status in ("FAILED", "ERROR", "CANCELLED"):
            print(f"[hero] fal job {status.lower()} ({model})")
            return False
        time.sleep(POLL_SECONDS)
    print(f"[hero] fal job timed out after {TIMEOUT_SECONDS}s ({model})")
    return False


def animate(still_path: str, prompt: str, out_path: str, cfg: dict,
            seconds: int = 5, extra_negative: str = "") -> bool:
    """Image-to-video for one still. False = caller keeps the still."""
    global _spent_usd, _accepted
    hcfg = cfg.get("hero_shots", {})
    if not hcfg.get("enabled", False):
        return False
    key = os.environ.get("FAL_KEY", "").strip()
    if not key or not still_path or not os.path.exists(still_path):
        return False
    cost = PRICE_PER_SECOND_USD * seconds
    ceiling = float(hcfg.get("max_usd_per_video", 1.20))
    if _spent_usd + cost > ceiling:
        print(f"[hero] cost gate: ${_spent_usd + cost:.2f} would exceed "
              f"${ceiling:.2f} — keeping the still")
        return False
    data_uri = _still_data_uri(still_path)
    if not data_uri:
        return False
    negative = NEGATIVE + (", " + extra_negative if extra_negative else "")
    body = {"prompt": prompt, "image_url": data_uri,
            "duration": str(int(seconds)), "negative_prompt": negative}
    models = [hcfg.get("model", "fal-ai/kling-video/v2.6/pro/image-to-video"),
              hcfg.get("fallback_model",
                       "fal-ai/kling-video/v2.5-turbo/pro/image-to-video")]
    for model in models:
        try:
            _spent_usd += cost  # generations bill whether or not we keep them
            if _run_queue(model, body, out_path, key, seconds):
                _accepted += 1
                print(f"[hero] {model}: {prompt[:60]}...")
                return True
        except (requests.RequestException, KeyError, ValueError,
                json.JSONDecodeError) as e:
            print(f"[hero] fal {model} failed: {e}")
    return False


def note_retry() -> None:
    global _retries
    _retries += 1


def metrics() -> dict:
    return {"hero_shots": _accepted, "hero_retries": _retries,
            "hero_spend_usd": round(_spent_usd, 2)}


def usage_summary() -> str:
    if _spent_usd <= 0:
        return "hero shots: 0 ($0)"
    return (f"hero shots: {_accepted} (+{_retries} retry) "
            f"≈ ${_spent_usd:.2f}")


def select_targets(scenes: list, max_n: int = 2) -> list:
    """(scene, beat_index) for the hook's first beat and the reveal scene.
    Deterministic — mirrors run.py's _attach_hero/_pad_reveal_pause lookups."""
    targets = []
    if scenes:
        targets.append((scenes[0], 0))
    reveal = next((sc for sc in scenes[1:]
                   if sc.get("delivery") == "reveal"), None)
    if reveal is not None:
        targets.append((reveal, 0))
    return targets[:max(0, int(max_n))]
