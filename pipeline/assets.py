"""Stage 2 — per-scene asset sourcing from Pexels (free API, commercial-safe).

Order per scene: HD stock video -> stock photo (Ken Burns later) -> generated
gradient card. The pipeline can therefore never fail for lack of footage.
"""
import os
import time

import requests
from PIL import Image, ImageDraw

VIDEO_API = "https://api.pexels.com/videos/search"
PHOTO_API = "https://api.pexels.com/v1/search"


def _get(url: str, params: dict, api_key: str) -> dict:
    for attempt in range(3):
        r = requests.get(url, params=params, headers={"Authorization": api_key}, timeout=60)
        if r.status_code == 429:
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Pexels rate limit persisted for {url}")


def _download(url: str, path: str) -> str:
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return path


def _best_video_file(video: dict, want_w: int) -> dict | None:
    """Pick the smallest file that is still >= target width (bandwidth-friendly)."""
    files = [f for f in video.get("video_files", []) if f.get("width")]
    if not files:
        return None
    geq = sorted((f for f in files if f["width"] >= want_w), key=lambda f: f["width"])
    return geq[0] if geq else max(files, key=lambda f: f["width"])


def _gradient_card(path: str, w: int, h: int, seed: int) -> str:
    """Last-resort visual: a dark cinematic gradient (never fails, always licensed)."""
    palettes = [((12, 18, 34), (36, 62, 110)), ((20, 12, 30), (88, 44, 108)),
                ((8, 24, 24), (24, 84, 78)), ((26, 16, 8), (110, 66, 26))]
    top, bottom = palettes[seed % len(palettes)]
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    img.save(path, quality=90)
    return path


def fetch_scene_assets(scene: dict, need_seconds: float, outdir: str, cfg: dict,
                       api_key: str, used_ids: set) -> list[dict]:
    """Return [{path, kind: video|image, duration(optional)}] covering need_seconds."""
    os.makedirs(outdir, exist_ok=True)
    w = cfg["video"]["width"]
    assets, covered = [], 0.0
    max_clips = max(2, int(need_seconds // cfg["video"]["max_shot_seconds"]) + 1)

    for term in scene["search_terms"]:
        if covered >= need_seconds or len(assets) >= max_clips:
            break
        try:
            data = _get(VIDEO_API, {"query": term, "per_page": 10,
                                    "orientation": "landscape"}, api_key)
        except Exception as e:
            print(f"[assets] video search failed for '{term}': {e}")
            continue
        for vid in data.get("videos", []):
            if covered >= need_seconds or len(assets) >= max_clips:
                break
            if vid["id"] in used_ids or vid.get("duration", 0) < 4:
                continue
            vf = _best_video_file(vid, w)
            if not vf:
                continue
            path = os.path.join(outdir, f"s{scene['n']:02d}_{vid['id']}.mp4")
            try:
                _download(vf["link"], path)
            except Exception as e:
                print(f"[assets] download failed ({vid['id']}): {e}")
                continue
            used_ids.add(vid["id"])
            dur = min(vid.get("duration", 8), cfg["video"]["max_shot_seconds"] * 2)
            assets.append({"path": path, "kind": "video"})
            covered += dur
            print(f"[assets] scene {scene['n']}: video {vid['id']} ({term})")

    if covered < need_seconds:  # photo fallback -> Ken Burns in render
        for term in scene["search_terms"]:
            if covered >= need_seconds:
                break
            try:
                data = _get(PHOTO_API, {"query": term, "per_page": 5,
                                        "orientation": "landscape", "size": "large"}, api_key)
            except Exception as e:
                print(f"[assets] photo search failed for '{term}': {e}")
                continue
            for ph in data.get("photos", []):
                key = f"p{ph['id']}"
                if key in used_ids:
                    continue
                path = os.path.join(outdir, f"s{scene['n']:02d}_{key}.jpg")
                try:
                    _download(ph["src"]["large2x"], path)
                except Exception:
                    continue
                used_ids.add(key)
                assets.append({"path": path, "kind": "image"})
                covered += 6
                print(f"[assets] scene {scene['n']}: photo {ph['id']} ({term})")
                break

    if not assets:  # absolute fallback
        path = os.path.join(outdir, f"s{scene['n']:02d}_card.jpg")
        _gradient_card(path, w, cfg["video"]["height"], scene["n"])
        assets.append({"path": path, "kind": "image"})
        print(f"[assets] scene {scene['n']}: gradient card fallback")
    return assets
