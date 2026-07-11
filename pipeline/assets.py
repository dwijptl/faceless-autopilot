"""Per-scene asset sourcing with visual originality rules.

Priority per scene (by visual_mode from the script):
  ai_image  -> FLUX (fal.ai) or Gemini image gen -> stock fallback
  kinetic / stat / card / glass -> one background asset (stock or AI) — overlays drawn in Remotion
  broll     -> Pexels video -> Pexels photo -> gradient card

CINEMATIC QUERY SHAPING: raw search terms pull generic vacation-stock. Every
term is first searched with a rotating cinematic modifier ("aerial", "macro",
"drone"…) so results skew toward the moody, professional b-roll buried in
Pexels; the raw term follows as a recall fallback.

A persistent usage log (assets_used.json, committed back to the repo) makes
sure no Pexels clip/photo or AI prompt ever repeats across videos.
"""
import hashlib
import json
import os
import time

import requests
from PIL import Image, ImageDraw

import ai_images
import vision_qc

VIDEO_API = "https://api.pexels.com/videos/search"
PHOTO_API = "https://api.pexels.com/v1/search"

# rotating cinematic modifiers — deterministic per scene, so variety across
# scenes but reproducible runs
CINEMATIC_MODIFIERS = ["aerial", "cinematic", "drone", "macro close up",
                       "dramatic", "slow motion"]


def _shaped_queries(terms: list, scene_n: int) -> list[str]:
    """['volcano'] -> ['volcano aerial', 'volcano', ...] — shaped first,
    raw second so we still find footage for rare subjects."""
    out = []
    for i, term in enumerate(terms):
        mod = CINEMATIC_MODIFIERS[(scene_n + i) % len(CINEMATIC_MODIFIERS)]
        out.append(f"{term} {mod}")
        out.append(term)
    return out


# ── persistent usage log ───────────────────────────────────────────────
def load_usage_log(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            log = json.load(f)
        log.setdefault("pexels", [])
        log.setdefault("prompts", [])
        return log
    except Exception:
        return {"pexels": [], "prompts": []}


def save_usage_log(path: str, log: dict) -> None:
    # keep the file bounded (~4000 most recent entries each)
    log["pexels"] = list(dict.fromkeys(log["pexels"]))[-4000:]
    log["prompts"] = list(dict.fromkeys(log["prompts"]))[-4000:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=0)


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
    files = [f for f in video.get("video_files", []) if f.get("width")]
    if not files:
        return None
    geq = sorted((f for f in files if f["width"] >= want_w), key=lambda f: f["width"])
    return geq[0] if geq else max(files, key=lambda f: f["width"])


def _gradient_card(path: str, w: int, h: int, seed: int) -> str:
    palettes = [((10, 20, 40), (18, 35, 63)), ((16, 12, 34), (70, 44, 108)),
                ((8, 26, 26), (22, 78, 74)), ((28, 18, 8), (104, 64, 26))]
    top, bottom = palettes[seed % len(palettes)]
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    img.save(path, quality=90)
    return path


def _orientation(cfg) -> str:
    return "portrait" if cfg["video"]["height"] > cfg["video"]["width"] else "landscape"


def _stock_videos(scene, need_seconds, outdir, cfg, api_key, used, max_clips,
                  gemini_key=""):
    w = cfg["video"]["width"]
    assets, covered, qc_budget = [], 0.0, 6  # cap vision checks per scene
    desc = scene.get("narration", "")
    for term in _shaped_queries(scene.get("search_terms", []), scene["n"]):
        if covered >= need_seconds or len(assets) >= max_clips:
            break
        try:
            data = _get(VIDEO_API, {"query": term, "per_page": 15,
                                    "orientation": _orientation(cfg)}, api_key)
        except Exception as e:
            print(f"[assets] video search failed for '{term}': {e}")
            continue
        for vid in data.get("videos", []):
            if covered >= need_seconds or len(assets) >= max_clips:
                break
            vid_key = f"v{vid['id']}"
            if vid_key in used or vid.get("duration", 0) < 4:
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
            if qc_budget > 0:  # visual sanity check before accepting
                qc_budget -= 1
                if not vision_qc.frame_ok(path, "video", desc, term,
                                          gemini_key, cfg):
                    used.add(vid_key)  # never try this clip again
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    continue
            used.add(vid_key)
            covered += min(vid.get("duration", 8), cfg["video"]["max_shot_seconds"] * 2)
            assets.append({"path": path, "kind": "video"})
            print(f"[assets] scene {scene['n']}: stock video {vid['id']} ({term})")
    return assets, covered


def _stock_photo(scene, outdir, api_key, used, orientation="landscape",
                 cfg=None, gemini_key=""):
    qc_budget = 3
    for term in _shaped_queries(scene.get("search_terms", []), scene["n"]):
        try:
            data = _get(PHOTO_API, {"query": term, "per_page": 8,
                                    "orientation": orientation, "size": "large"}, api_key)
        except Exception:
            continue
        for ph in data.get("photos", []):
            key = f"p{ph['id']}"
            if key in used:
                continue
            path = os.path.join(outdir, f"s{scene['n']:02d}_{key}.jpg")
            try:
                _download(ph["src"]["large2x"], path)
            except Exception:
                continue
            if cfg is not None and qc_budget > 0:
                qc_budget -= 1
                if not vision_qc.frame_ok(path, "image",
                                          scene.get("narration", ""), term,
                                          gemini_key, cfg):
                    used.add(key)
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    continue
            used.add(key)
            print(f"[assets] scene {scene['n']}: stock photo {ph['id']} ({term})")
            return {"path": path, "kind": "image"}
    return None


def fetch_scene_assets(scene: dict, need_seconds: float, outdir: str, cfg: dict,
                       pexels_key: str, gemini_key: str, used: set,
                       used_prompts: set, ai_budget: list) -> list[dict]:
    """Returns [{path, kind, ai(optional)}]. `used`/`used_prompts` are mutated;
    ai_budget is a single-element list acting as a mutable counter."""
    os.makedirs(outdir, exist_ok=True)
    mode = scene.get("visual_mode", "broll")
    assets: list[dict] = []

    # map scenes render their own background (MapZoom) — no assets needed
    if mode == "map" and scene.get("map_render"):
        return []

    # AI-generated hero image (for ai_image scenes, or as bg for kinetic/stat)
    wants_ai = mode == "ai_image" or (
        mode in ("kinetic", "stat", "card", "glass") and not scene.get("search_terms"))
    prompt = (scene.get("ai_prompt") or "").strip()
    if wants_ai and prompt and ai_budget[0] > 0:
        ph = hashlib.sha1(prompt.lower().encode()).hexdigest()[:16]
        if ph not in used_prompts:
            path = os.path.join(outdir, f"s{scene['n']:02d}_ai.png")
            aspect = ("9:16 tall vertical" if _orientation(cfg) == "portrait"
                      else "16:9 wide")
            if ai_images.generate(prompt, path, gemini_key, cfg, aspect):
                used_prompts.add(ph)
                ai_budget[0] -= 1
                assets.append({"path": path, "kind": "image", "ai": True})

    # Overlay scenes need one strong background; the graphic carries the beat.
    if mode in ("kinetic", "stat", "card", "glass"):
        if not assets:
            stock, _ = _stock_videos(scene, min(need_seconds, 10), outdir, cfg,
                                     pexels_key, used, max_clips=1,
                                     gemini_key=gemini_key)
            assets.extend(stock)
        if not assets:
            photo = _stock_photo(scene, outdir, pexels_key, used,
                                 _orientation(cfg), cfg, gemini_key)
            if photo:
                assets.append(photo)
    else:
        covered = 6.0 * len(assets)
        max_clips = max(2, int(need_seconds // cfg["video"]["max_shot_seconds"]) + 1)
        stock, c = _stock_videos(scene, need_seconds - covered, outdir, cfg,
                                 pexels_key, used, max_clips,
                                 gemini_key=gemini_key)
        assets.extend(stock)
        covered += c
        if covered < need_seconds and len(assets) < 2:
            photo = _stock_photo(scene, outdir, pexels_key, used,
                                 _orientation(cfg), cfg, gemini_key)
            if photo:
                assets.append(photo)

    if not assets:  # absolute fallback — never fail
        path = os.path.join(outdir, f"s{scene['n']:02d}_card.jpg")
        _gradient_card(path, cfg["video"]["width"], cfg["video"]["height"], scene["n"])
        assets.append({"path": path, "kind": "image"})
        print(f"[assets] scene {scene['n']}: gradient card fallback")
    return assets
