"""Per-scene asset sourcing with visual originality rules.

Priority per scene (by visual_mode from the script):
  ai_image  -> FLUX (fal.ai) or Gemini image gen -> stock fallback
  kinetic / stat / card / glass -> one background asset (stock or AI) — overlays drawn in Remotion
  broll     -> Pexels video -> Pexels photo -> animated evidence graphic

CINEMATIC QUERY SHAPING: raw search terms pull generic vacation-stock. Every
term is first searched with a rotating cinematic modifier ("aerial", "macro",
"drone"…) so results skew toward the moody, professional b-roll buried in
Pexels; the raw term follows as a recall fallback.

CONTINUITY CONTRACT: scenes carry the episode's forbidden_visuals list; the
vision QC rejects any candidate showing them even when it matches the scene
semantically (a scuba diver is "underwater human" to keyword search, but it
breaks an unprotected-human premise).

A persistent usage log (assets_used.json, committed back to the repo) makes
sure no Pexels clip/photo or AI prompt ever repeats across videos.
"""
import hashlib
import html
import json
import math
import os
import re
import time

import requests
from PIL import Image, ImageDraw

import ai_images
import families as families_mod
import vision_qc

# NASA/Wikimedia originals can be gigapixel (a 162 MP space still crashed a
# Short render in Chrome). We downscale every image before it reaches
# Remotion, so raise PIL's decompression-bomb guard from a hard error to
# something we handle deliberately in _downscale_image.
Image.MAX_IMAGE_PIXELS = None

# Longest edge any still is allowed to reach the renderer at. 2560 covers
# 1080p and vertical 1080x1920 with headroom for Ken Burns push-in; anything
# larger only burns GPU memory and risks a Chrome tab crash mid-render.
MAX_IMAGE_SIDE = 2560


def _downscale_image(path: str, max_side: int = MAX_IMAGE_SIDE) -> None:
    """Shrink an over-large still in place so Remotion never composites a
    gigapixel image. No-op for images already within bounds or unreadable
    (a genuinely broken file is caught later by the render guard)."""
    try:
        with Image.open(path) as im:
            w, h = im.size
            if max(w, h) <= max_side:
                return
            scale = max_side / float(max(w, h))
            im = im.convert("RGB").resize(
                (max(1, round(w * scale)), max(1, round(h * scale))),
                Image.LANCZOS)
            im.save(path, quality=90)
        print(f"[assets] downscaled {os.path.basename(path)} "
              f"{w}x{h} -> {round(w * scale)}x{round(h * scale)}")
    except Exception as exc:
        print(f"[assets] downscale skipped for "
              f"{os.path.basename(path)} ({exc})")

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


def _best_video_file(video: dict, want_w: int, want_h: int | None = None,
                     max_upscale: float = 1.25) -> dict | None:
    """Pick a source that can cover the target without obvious upscaling."""
    files = [
        f for f in video.get("video_files", [])
        if f.get("width") and f.get("height") and f.get("link")
    ]
    if not files:
        return None
    if want_h is None:
        geq = sorted((f for f in files if f["width"] >= want_w),
                     key=lambda f: f["width"])
        return geq[0] if geq else max(files, key=lambda f: f["width"])

    eligible = [
        f for f in files
        if max(want_w / float(f["width"]), want_h / float(f["height"]))
        <= max_upscale
    ]
    if not eligible:
        return None
    target_ratio = want_w / float(want_h)
    return min(eligible, key=lambda f: (
        abs((f["width"] / float(f["height"])) - target_ratio),
        f["width"] * f["height"],
    ))


def _gradient_card(path: str, w: int, h: int, seed: int) -> str:
    """Legacy on-disk fallback kept for old hero-shot callers.

    Scene and beat resolution must use :func:`fallback_graphic_asset` instead;
    a full-frame gradient is indistinguishable from missing footage.
    """
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


def fallback_graphic_asset(scene: dict, beat: dict | None = None,
                           index: int = 0) -> dict:
    """Return a zero-network, non-blank visual for a failed media lookup.

    Remotion renders this as an animated evidence board.  It deliberately has
    no filesystem dependency, so it also survives an episode-wide stock/AI
    outage.  The ``fallback`` marker keeps the quality gate honest: the draft
    remains review-only even though viewers never see a solid colour card.
    """
    beat = beat or {}
    raw_title = (beat.get("purpose") or beat.get("cue")
                 or scene.get("title") or scene.get("narration")
                 or "Visual evidence")
    title = " ".join(str(raw_title).split())[:60]
    terms = (beat.get("search_terms") or scene.get("search_terms") or [])
    labels = []
    for term in terms:
        label = " ".join(str(term).split())[:28]
        if label and label.casefold() not in {x.casefold() for x in labels}:
            labels.append(label)
        if len(labels) == 3:
            break
    if not labels:
        words = title.split()
        width = max(int(math.ceil(len(words) / 3)), 1)
        labels = [" ".join(words[pos:pos + width])[:28]
                  for pos in range(0, len(words), width)][:3]
    labels = labels or ["EVIDENCE"]
    try:
        scene_n = int(scene.get("n", 0))
    except (TypeError, ValueError):
        scene_n = 0
    return {
        "path": f"s{scene_n:02d}_b{index:02d}_fallback_graphic",
        "kind": "graphic",
        "beat_index": index,
        "graphic": {
            "kind": "fallback",
            "title": title,
            "items": [{"label": label} for label in labels],
        },
        "fallback": "programmatic",
    }


def _orientation(cfg) -> str:
    return "portrait" if cfg["video"]["height"] > cfg["video"]["width"] else "landscape"


# ── zero-cost local guards: darkness + episode-level duplicate detection ──
_EPISODE_HASHES: set = set()


def reset_episode_state() -> None:
    """Called once per video so luma/duplicate guards start fresh."""
    _EPISODE_HASHES.clear()


def _probe_frame(path: str, kind: str):
    """PIL image of the asset's representative frame; None on any failure."""
    try:
        if kind == "image":
            return Image.open(path).convert("RGB")
        import subprocess
        tmp = path + ".probe.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", "1", "-i", path,
                        "-frames:v", "1", "-q:v", "3", "-y", tmp],
                       capture_output=True, timeout=60, check=True)
        img = Image.open(tmp).convert("RGB")
        try:
            os.remove(tmp)
        except OSError:
            pass
        return img
    except Exception:
        return None


def _dhash(img, size: int = 8) -> str:
    """Perceptual difference hash — catches near-identical shots this episode."""
    try:
        g = img.convert("L").resize((size + 1, size))
        pixels = (g.get_flattened_data() if hasattr(g, "get_flattened_data")
                  else g.getdata())
        px = list(pixels)
        bits = "".join(
            "1" if px[r * (size + 1) + c] > px[r * (size + 1) + c + 1] else "0"
            for r in range(size) for c in range(size))
        return f"{int(bits, 2):016x}"
    except Exception:
        return ""


def _visual_ok(path: str, kind: str, label: str,
               cfg: dict | None = None) -> bool:
    """Reject unusable resolution, darkness and episode-level duplicates."""
    img = _probe_frame(path, kind)
    if img is None:
        return True
    if cfg is not None:
        target_w = float(cfg["video"]["width"])
        target_h = float(cfg["video"]["height"])
        max_upscale = float(cfg.get("qc", {}).get("max_upscale", 1.25))
        cover_scale = max(target_w / img.width, target_h / img.height)
        if cover_scale > max_upscale:
            print(f"[assets] {label}: rejected "
                  f"(needs {cover_scale:.2f}x upscale after crop)")
            return False
    try:
        from PIL import ImageStat
        if ImageStat.Stat(img.convert("L")).mean[0] < 26.0:
            print(f"[assets] {label}: rejected (near-black footage)")
            return False
    except Exception:
        pass
    h = _dhash(img)
    if h and h in _EPISODE_HASHES:
        print(f"[assets] {label}: rejected (visual duplicate this episode)")
        return False
    if h:
        _EPISODE_HASHES.add(h)
    return True


def _rm(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


# Three deliberately different compositions. Generating the same prompt
# three times mostly buys lottery tickets; distinct visual hypotheses give
# the opening-frame judge something meaningful to compare.
_HOOK_COMPOSITIONS = (
    "A wide, instantly legible establishing composition: one dominant subject "
    "isolated against its real environment, a clear path for the eye",
    "An evidence-first medium or close composition: one concrete physical "
    "detail that makes the mystery undeniable, environment still identifiable",
    "A threshold composition with foreground depth: the viewer feels one step "
    "away from entering the place or event, unresolved tension inside the frame",
)


def _hook_candidate_ok(path: str, cfg: dict, seen_hashes: set[str]) -> bool:
    """Cheap local screen before a paid/limited vision comparison."""
    try:
        from PIL import ImageStat
        with Image.open(path) as raw:
            img = raw.convert("RGB")
        target_w = float(cfg["video"]["width"])
        target_h = float(cfg["video"]["height"])
        max_upscale = float(cfg.get("qc", {}).get("max_upscale", 1.25))
        if max(target_w / img.width, target_h / img.height) > max_upscale:
            return False
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        hook_cfg = cfg.get("ai_images", {}).get("premium_hook", {})
        if stat.mean[0] < float(hook_cfg.get("min_luma", 30)):
            return False
        if stat.stddev[0] < float(hook_cfg.get("min_contrast", 18)):
            return False
        h = _dhash(img)
        if h and h in seen_hashes:
            return False
        if h:
            seen_hashes.add(h)
        return True
    except Exception:
        return False


def _premium_hook_asset(scene: dict, beat: dict, outdir: str, cfg: dict,
                        gemini_key: str, used_prompts: set) -> dict | None:
    """Generate and rank hook-only premium still candidates.

    This is a separate, hard-capped quality lane. It does not consume the
    normal scene/director credits, and any failure returns control to the
    existing AI -> stock -> card fallback chain.
    """
    hook_cfg = cfg.get("ai_images", {}).get("premium_hook", {})
    if not hook_cfg.get("enabled", False):
        return None
    if int(scene.get("n", 0)) != 1 or scene.get("delivery") != "hook":
        return None
    if hook_cfg.get("longform_only", True) and _orientation(cfg) == "portrait":
        return None

    wanted = max(1, min(int(hook_cfg.get("candidates", 3)),
                        len(_HOOK_COMPOSITIONS)))
    if os.environ.get("FAL_KEY", "").strip():
        estimated = max(float(hook_cfg.get("estimated_usd_per_candidate", 0.12)),
                        0.001)
        ceiling = max(float(hook_cfg.get("max_usd_per_video", 0.40)), 0.0)
        wanted = min(wanted, int(ceiling // estimated))
    if wanted <= 0:
        print("[hook-still] cost gate allows no premium candidates")
        return None

    cue = str(beat.get("cue", "")).strip()
    purpose = str(beat.get("purpose", "")).strip()
    search = ", ".join(str(t) for t in (beat.get("search_terms") or [])[:2])
    subject = (str(scene.get("hero_prompt", "")).strip()
               or str(scene.get("ai_prompt", "")).strip()
               or purpose or cue or str(scene.get("narration", ""))[:220])
    base = (
        f"Documentary opening image for: {scene.get('episode_title', '')}. "
        f"Exact subject and situation: {subject}. Opening spoken idea: {cue}. "
        f"Concrete visual anchors: {search}. "
        "Show only what can be defended as a factual reconstruction; do not "
        "invent evidence or present folklore/supernatural claims as fact. "
        "ONE clear subject, immediate visual question, readable at phone size, "
        "strong silhouette and tonal separation, layered cinematic depth, "
        "lower 25 percent calm and uncluttered for Hindi captions, no collage, "
        "no split screen, no typography, no symbols, no recognizable faces"
    )
    candidates = []
    local_hashes: set[str] = set()
    aspect = "16:9 wide"
    for index in range(wanted):
        prompt = f"{base}. COMPOSITION OPTION: {_HOOK_COMPOSITIONS[index]}."
        ph = hashlib.sha1(prompt.lower().encode()).hexdigest()[:16]
        # A rerender of the same topic must not lose its premium hook merely
        # because the previous attempt reached the persistent usage log.
        alternate = 2
        while ph in used_prompts and alternate <= 20:
            prompt = (f"{base}. COMPOSITION OPTION: {_HOOK_COMPOSITIONS[index]}. "
                      f"Fresh alternate photographic take {alternate}.")
            ph = hashlib.sha1(prompt.lower().encode()).hexdigest()[:16]
            alternate += 1
        if ph in used_prompts:
            continue
        path = os.path.join(outdir, f"s01_hook_c{index + 1:02d}.jpg")
        if not ai_images.generate(prompt, path, gemini_key, cfg, aspect,
                                  provider="premium"):
            _rm(path)
            continue
        used_prompts.add(ph)
        _downscale_image(path)
        if not _hook_candidate_ok(path, cfg, local_hashes):
            print(f"[hook-still] candidate {index + 1} failed local quality")
            _rm(path)
            continue
        candidates.append({"path": path, "prompt": prompt})

    if not candidates:
        print("[hook-still] no usable premium candidate — normal fallback")
        return None
    winner = vision_qc.pick_hook_still(
        [(item["path"], "image") for item in candidates],
        str(scene.get("narration", "")), str(scene.get("episode_title", "")),
        search or purpose or cue, gemini_key, cfg,
        forbidden=scene.get("forbidden_visuals") or [])
    if winner < 0:
        for item in candidates:
            _rm(item["path"])
        print("[hook-still] vision judge rejected every candidate")
        return None

    # If the chosen image duplicates another episode asset, try the runner-up
    # before abandoning the premium lane.
    order = [winner] + [i for i in range(len(candidates)) if i != winner]
    chosen = None
    for i in order:
        item = candidates[i]
        if _visual_ok(item["path"], "image", "premium hook still", cfg):
            chosen = item
            winner = i
            break
    if chosen is None:
        for item in candidates:
            _rm(item["path"])
        return None
    for i, item in enumerate(candidates):
        if i != winner:
            _rm(item["path"])
    print(f"[hook-still] selected candidate {winner + 1}/{len(candidates)}")
    return {"path": chosen["path"], "kind": "image", "ai": True,
            "premium_hook": True, "hook_candidates": len(candidates),
            "family": beat.get("family", "cold_open_hook")}


# ── G13: NASA image/video library — primary-source, public-domain space
# footage tried BEFORE generic stock for space scenes. Fail-open to Pexels. ──
NASA_API = "https://images-api.nasa.gov"
NASA_HINTS = ("space", "planet", "mars", "venus", "jupiter", "saturn",
              "mercury", "neptune", "uranus", "pluto", "moon", "lunar",
              "galaxy", "nebula", "astronaut", "orbit", "solar", "cosmos",
              "asteroid", "comet", "rocket", "spacecraft", "satellite",
              "telescope", "iss", "supernova", "black hole", "milky way")


def _nasa_relevant(terms: list) -> bool:
    joined = " ".join(str(t).lower() for t in terms)
    return any(h in joined for h in NASA_HINTS)


def _nasa_asset(scene: dict, outdir: str, used: set, cfg: dict,
                gemini_key: str = "") -> dict | None:
    """One exact-entity NASA asset, quality-checked like all other footage."""
    qc_budget = 3
    for term in list(scene.get("search_terms", []))[:2]:
        for media in ("video", "image"):
            try:
                r = requests.get(f"{NASA_API}/search",
                                 params={"q": term, "media_type": media,
                                         "page_size": 8}, timeout=30)
                r.raise_for_status()
                items = r.json().get("collection", {}).get("items", [])
            except Exception:
                continue
            for it in items:
                data = (it.get("data") or [{}])[0]
                nasa_id = str(data.get("nasa_id") or "")
                if not nasa_id or f"n{nasa_id}" in used:
                    continue
                try:
                    a = requests.get(
                        f"{NASA_API}/asset/{requests.utils.quote(nasa_id)}",
                        timeout=30)
                    a.raise_for_status()
                    hrefs = [i.get("href", "") for i in
                             a.json().get("collection", {}).get("items", [])]
                except Exception:
                    continue
                if media == "video":
                    mp4s = [h for h in hrefs if h.endswith(".mp4")]
                    cands = sorted(mp4s, key=lambda h: (
                        "~large.mp4" not in h,
                        "~orig.mp4" not in h,
                        "~mobile.mp4" in h,
                    ))
                else:
                    # prefer NASA's ~large (web-sized) over ~orig (can be
                    # gigapixel — the 162 MP still that crashed the render)
                    cands = ([h for h in hrefs if h.endswith("~large.jpg")]
                             or [h for h in hrefs if h.endswith("~orig.jpg")]
                             or [h for h in hrefs if h.endswith(".jpg")])
                if not cands:
                    continue
                url = cands[0].replace("http://", "https://").replace(" ", "%20")
                ext = "mp4" if media == "video" else "jpg"
                tag = hashlib.sha1(nasa_id.encode()).hexdigest()[:8]
                path = os.path.join(outdir, f"s{scene['n']:02d}_nasa_{tag}.{ext}")
                try:
                    _download(url, path)
                except Exception:
                    continue
                kind = "video" if media == "video" else "image"
                if kind == "image":
                    _downscale_image(path)
                if not _visual_ok(path, kind,
                                  f"scene {scene['n']} NASA {nasa_id}", cfg):
                    used.add(f"n{nasa_id}")
                    _rm(path)
                    continue
                if qc_budget <= 0:
                    _rm(path)
                    return None
                qc_budget -= 1
                if not vision_qc.frame_ok(
                        path, kind, _qc_desc(scene), term, gemini_key, cfg,
                        forbidden=scene.get("forbidden_visuals") or [],
                        source="stock"):
                    used.add(f"n{nasa_id}")
                    _rm(path)
                    continue
                used.add(f"n{nasa_id}")
                print(f"[assets] scene {scene['n']}: NASA {media} "
                      f"{nasa_id} ({term})")
                return {"path": path, "kind": kind}
    return None


# Wikimedia Commons is the primary-source lane for named places, buildings,
# inscriptions, documents and artifacts outside NASA's domain. Commons files
# carry machine-readable attribution metadata, which travels into the render
# manifest and a release-side credits file.
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_HEADERS = {
    "User-Agent": "RahasyaLokFacelessAutopilot/1.0 (documentary asset search)"
}
COMMONS_MIMES = {"image/jpeg", "image/png", "image/webp"}


def _commons_meta(extmetadata: dict, key: str) -> str:
    raw = str((extmetadata.get(key) or {}).get("value") or "")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def _commons_asset(scene: dict, outdir: str, used: set, cfg: dict,
                   gemini_key: str = "") -> dict | None:
    """Fetch one authenticated Commons image with reusable license credits.

    A vision match is mandatory. If Commons cannot provide an exact visual,
    the caller continues to another authentic source or a transparent card;
    it never converts the beat into an AI reconstruction silently.
    """
    queries = [str(t).strip() for t in scene.get("search_terms", [])
               if str(t).strip()][:3]
    for term in queries:
        try:
            response = requests.get(
                COMMONS_API,
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": term,
                    "gsrnamespace": 6,
                    "gsrlimit": 10,
                    "prop": "imageinfo",
                    "iiprop": "url|mime|extmetadata",
                    "iiurlwidth": MAX_IMAGE_SIDE,
                    "format": "json",
                    "formatversion": 2,
                    "origin": "*",
                },
                headers=COMMONS_HEADERS, timeout=45)
            response.raise_for_status()
            pages = response.json().get("query", {}).get("pages", [])
        except Exception as exc:
            print(f"[assets] Commons search failed for '{term}': {exc}")
            continue
        for page in pages:
            page_id = str(page.get("pageid") or "")
            info = (page.get("imageinfo") or [{}])[0]
            mime = str(info.get("mime") or "").lower()
            url = str(info.get("thumburl") or info.get("url") or "")
            if (not page_id or f"w{page_id}" in used or not url
                    or mime not in COMMONS_MIMES):
                continue
            metadata = info.get("extmetadata") or {}
            license_name = (_commons_meta(metadata, "LicenseShortName")
                            or _commons_meta(metadata, "UsageTerms"))
            # Do not distribute a file when its reusable license is not
            # machine-readable enough to credit correctly.
            if not license_name:
                continue
            ext = {"image/png": "png", "image/webp": "webp"}.get(mime, "jpg")
            path = os.path.join(
                outdir, f"s{scene['n']:02d}_commons_{page_id}.{ext}")
            try:
                _download(url, path)
                _downscale_image(path)
            except Exception:
                _rm(path)
                continue
            key = f"w{page_id}"
            if not _visual_ok(path, "image",
                              f"scene {scene['n']} Commons {page_id}", cfg):
                used.add(key)
                _rm(path)
                continue
            if not vision_qc.frame_ok(
                    path, "image", _qc_desc(scene), term, gemini_key, cfg,
                    forbidden=scene.get("forbidden_visuals") or [],
                    source="stock"):
                used.add(key)
                _rm(path)
                continue
            used.add(key)
            attribution = {
                "title": str(page.get("title") or "").removeprefix("File:"),
                "artist": (_commons_meta(metadata, "Artist")
                           or _commons_meta(metadata, "Credit")
                           or "Wikimedia Commons contributor"),
                "license": license_name,
                "licenseUrl": _commons_meta(metadata, "LicenseUrl"),
                "sourceUrl": str(info.get("descriptionurl") or ""),
            }
            print(f"[assets] scene {scene['n']}: Wikimedia Commons "
                  f"{page_id} ({term})")
            return {"path": path, "kind": "image", "source": "wikimedia",
                    "attribution": attribution}
    return None


def _qc_desc(scene: dict) -> str:
    """Narration plus the scene's must-show contract for the vision check."""
    desc = (f"EPISODE: {scene.get('episode_title', '')} | "
            f"SCENE: {scene.get('title', '')} | "
            f"{scene.get('narration', '')}")
    must = [str(m) for m in (scene.get("must_show") or []) if str(m).strip()]
    if must:
        desc += " | MUST SHOW (reject footage missing these): " + ", ".join(must[:3])
    return desc


def _stock_videos(scene, need_seconds, outdir, cfg, api_key, used, max_clips,
                  gemini_key=""):
    w = cfg["video"]["width"]
    h = cfg["video"]["height"]
    max_upscale = float(cfg.get("qc", {}).get("max_upscale", 1.25))
    assets, covered, qc_budget = [], 0.0, 6  # cap vision checks per scene
    desc = _qc_desc(scene)
    forbidden = scene.get("forbidden_visuals") or []
    # G4 candidate ranking: single-clip beats download up to TWO candidates
    # and let ONE vision call pick the semantically better one.
    rank_mode = (max_clips == 1
                 and cfg.get("qc", {}).get("rank_candidates", True))
    pool: list[dict] = []
    for term in _shaped_queries(scene.get("search_terms", []), scene["n"]):
        if covered >= need_seconds or len(assets) >= max_clips:
            break
        if rank_mode and len(pool) >= 2:
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
            if rank_mode and len(pool) >= 2:
                break
            vid_key = f"v{vid['id']}"
            if vid_key in used or vid.get("duration", 0) < 4:
                continue
            vf = _best_video_file(vid, w, h, max_upscale)
            if not vf:
                continue
            path = os.path.join(outdir, f"s{scene['n']:02d}_{vid['id']}.mp4")
            try:
                _download(vf["link"], path)
            except Exception as e:
                print(f"[assets] download failed ({vid['id']}): {e}")
                continue
            if not _visual_ok(path, "video",
                              f"scene {scene['n']} video {vid['id']}", cfg):
                used.add(vid_key)
                _rm(path)
                continue
            if rank_mode:
                pool.append({"path": path, "key": vid_key, "term": term,
                             "dur": vid.get("duration", 8)})
                continue
            if qc_budget > 0:  # visual sanity check before accepting
                qc_budget -= 1
                if not vision_qc.frame_ok(path, "video", desc, term,
                                          gemini_key, cfg,
                                          forbidden=forbidden,
                                          source="stock"):
                    used.add(vid_key)  # never try this clip again
                    _rm(path)
                    continue
            used.add(vid_key)
            covered += min(vid.get("duration", 8), cfg["video"]["max_shot_seconds"] * 2)
            assets.append({"path": path, "kind": "video"})
            print(f"[assets] scene {scene['n']}: stock video {vid['id']} ({term})")
    if rank_mode and pool:
        winner = 0
        accept = True
        if len(pool) == 2:
            winner = vision_qc.pick_best(
                [(c["path"], "video") for c in pool], desc, pool[0]["term"],
                gemini_key, cfg, forbidden=forbidden)
            accept = winner >= 0
        elif qc_budget > 0:  # single candidate — normal QC
            accept = vision_qc.frame_ok(pool[0]["path"], "video", desc,
                                        pool[0]["term"], gemini_key, cfg,
                                        forbidden=forbidden, source="stock")
        for i, c in enumerate(pool):
            used.add(c["key"])
            if not accept or i != winner:
                _rm(c["path"])
        if accept:
            chosen = pool[winner]
            covered += min(chosen["dur"], cfg["video"]["max_shot_seconds"] * 2)
            assets.append({"path": chosen["path"], "kind": "video"})
            note = "ranked" if len(pool) == 2 else "checked"
            print(f"[assets] scene {scene['n']}: stock video "
                  f"{chosen['key'][1:]} ({chosen['term']}, {note})")
    return assets, covered


def _stock_photo(scene, outdir, api_key, used, orientation="landscape",
                 cfg=None, gemini_key=""):
    qc_budget = 3
    forbidden = scene.get("forbidden_visuals") or []
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
                _downscale_image(path)
            except Exception:
                continue
            if not _visual_ok(path, "image",
                              f"scene {scene['n']} photo {ph['id']}", cfg):
                used.add(key)
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            if cfg is not None and qc_budget > 0:
                qc_budget -= 1
                if not vision_qc.frame_ok(path, "image",
                                          _qc_desc(scene), term,
                                          gemini_key, cfg,
                                          forbidden=forbidden,
                                          source="stock"):
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


def _director_beat_asset(scene: dict, beat: dict, index: int, outdir: str,
                         cfg: dict, gemini_key: str, used_prompts: set,
                         director_budget: list | None) -> dict | None:
    """Narrative-intent media resolution for one beat (visual director).

    Walks the beat family's media preference order:
      pg    -> a free programmatic graphic (timeline/scale/branch/chart/
               cutaway) drawn by Remotion from the planner's data payload
      ai    -> a family-composed AI still (only when this beat holds one of
               the priority-ranked grants, so the hook/reveal never lose
               their credit to an early filler beat)
      stock -> defer to the legacy exact-subject stock chain (returns None)
    Fail-open: any miss returns None and the legacy chain takes over.
    """
    family = beat.get("family")
    if not (families_mod.enabled(cfg) and family):
        return None
    policy = families_mod.source_policy(beat, scene)
    if policy == "primary":
        return None  # authentic/archival only; AI would invent evidence

    order = families_mod.media_order(family)
    if order and order[0] == "pg" and beat.get("graphic"):
        print(f"[director] scene {scene['n']} beat {index + 1}: "
              f"programmatic {beat['graphic'].get('kind')} ({family})")
        return {"path": f"s{scene['n']:02d}_b{index:02d}_graphic",
                "kind": "graphic", "graphic": beat["graphic"],
                "family": family, "source_policy": policy}

    def generate_ai() -> dict | None:
        if not beat.get("ai_grant") or not director_budget \
                or director_budget[0] <= 0:
            return None
        subject_parts = [str(beat.get("purpose") or beat.get("cue") or "").strip()]
        subject_parts += [str(t) for t in (beat.get("search_terms") or [])[:2]]
        must = [str(m) for m in (scene.get("must_show") or [])[:2]]
        if must:
            subject_parts.append("MUST SHOW: " + ", ".join(must))
        if scene.get("episode_title"):
            subject_parts.append("EPISODE CONTEXT: " + str(scene["episode_title"]))
        subject = ". ".join(p for p in subject_parts if p)
        if not subject:
            return None
        prompt = families_mod.compose_prompt(
            subject, family, scene.get("domain_pack"))
        if policy == "custom":
            prompt += (". Clearly staged documentary reconstruction, "
                       "regionally and historically accurate material culture, "
                       "no modern objects, no unrelated religion or architecture")
        ph = hashlib.sha1(prompt.lower().encode()).hexdigest()[:16]
        if ph in used_prompts:
            return None
        path = os.path.join(outdir,
                            f"s{scene['n']:02d}_b{index:02d}_fam.png")
        aspect = ("9:16 tall vertical" if _orientation(cfg) == "portrait"
                  else "16:9 wide")
        if not ai_images.generate(prompt, path, gemini_key, cfg, aspect):
            return None
        used_prompts.add(ph)
        director_budget[0] -= 1
        print(f"[director] scene {scene['n']} beat {index + 1}: "
              f"AI still ({family}/{policy}, {director_budget[0]} credits left)")
        return {"path": path, "kind": "image", "ai": True,
                "family": family, "source_policy": policy}

    # A custom reconstruction must be generated before considering the
    # family's ordinary stock preference.
    if policy == "custom":
        return generate_ai()
    for medium in order:
        if medium == "pg" and beat.get("graphic"):
            print(f"[director] scene {scene['n']} beat {index + 1}: "
                  f"programmatic {beat['graphic'].get('kind')} ({family})")
            return {"path": f"s{scene['n']:02d}_b{index:02d}_graphic",
                    "kind": "graphic", "graphic": beat["graphic"],
                    "family": family}
        if medium == "ai":
            generated = generate_ai()
            if generated:
                return generated
        if medium == "stock":
            return None  # legacy exact-subject stock chain owns this beat
    return None


def fetch_scene_assets(scene: dict, need_seconds: float, outdir: str, cfg: dict,
                       pexels_key: str, gemini_key: str, used: set,
                       used_prompts: set, ai_budget: list,
                       rescue_budget: list | None = None,
                       director_budget: list | None = None) -> list[dict]:
    """Returns [{path, kind, ai(optional)}]. `used`/`used_prompts` are mutated;
    ai_budget is a single-element list acting as a mutable counter."""
    os.makedirs(outdir, exist_ok=True)
    mode = scene.get("visual_mode", "broll")
    assets: list[dict] = []
    beats = scene.get("visual_beats") or []

    # map scenes render their own background (MapZoom) — no assets needed
    if mode == "map" and scene.get("map_render"):
        return []

    # Frame zero has its own premium lane: three different visual hypotheses,
    # one opening-specific vision decision. The winner preempts every generic
    # scene/stock asset for beat 0 and remains the fallback for hero animation.
    if beats:
        hook = _premium_hook_asset(scene, beats[0], outdir, cfg, gemini_key,
                                   used_prompts)
        if hook:
            hook["beat_index"] = 0
            assets.append(hook)

    # AI-generated hero image (for ai_image scenes, or as bg for kinetic/stat)
    wants_ai = mode == "ai_image" or (
        mode in ("kinetic", "stat", "card", "glass", "scale", "causal")
        and not scene.get("search_terms"))
    prompt = (scene.get("ai_prompt") or "").strip()
    if (wants_ai and prompt and ai_budget[0] > 0
            and not any(a.get("beat_index") == 0 for a in assets)):
        ph = hashlib.sha1(prompt.lower().encode()).hexdigest()[:16]
        if ph not in used_prompts:
            path = os.path.join(outdir, f"s{scene['n']:02d}_ai.png")
            aspect = ("9:16 tall vertical" if _orientation(cfg) == "portrait"
                      else "16:9 wide")
            if ai_images.generate(prompt, path, gemini_key, cfg, aspect):
                used_prompts.add(ph)
                ai_budget[0] -= 1
                assets.append({"path": path, "kind": "image", "ai": True,
                               "beat_index": 0})

    # Long-form semantic plan: source one concrete visual for each spoken idea.
    # This keeps roughly the same number of downloaded clips as the old
    # duration-based rotation, but now every clip has a narration binding.
    if beats:
        max_shot = max(float(cfg["video"].get("max_shot_seconds", 5)), 0.5)
        for index, beat in enumerate(beats):
            policy = families_mod.source_policy(beat, scene)
            beat["source_policy"] = policy
            beat_assets = [a for a in assets if a.get("beat_index") == index]
            if not beat_assets:
                directed = _director_beat_asset(scene, beat, index, outdir, cfg,
                                                gemini_key, used_prompts,
                                                director_budget)
                if directed:
                    beat_assets.append(directed)
            if not beat_assets:
                beat_scene = {
                    **scene,
                    "search_terms": beat.get("search_terms") or scene.get("search_terms", []),
                    "narration": f"{beat.get('cue', '')}. {beat.get('purpose', '')}".strip(),
                }
                need = min(max(float(beat.get("duration", max_shot)), 1.0), max_shot)
                if policy != "custom" and _nasa_relevant(beat_scene["search_terms"]):
                    nasa = _nasa_asset(beat_scene, outdir, used, cfg, gemini_key)
                    if nasa:
                        beat_assets.append(nasa)
                if not beat_assets and policy == "primary":
                    commons = _commons_asset(beat_scene, outdir, used, cfg,
                                             gemini_key)
                    if commons:
                        beat_assets.append(commons)
                if not beat_assets and policy != "custom":
                    stock, _ = _stock_videos(
                        beat_scene, need, outdir, cfg, pexels_key, used,
                        max_clips=1, gemini_key=gemini_key)
                    beat_assets.extend(stock)
                if (not beat_assets and policy != "primary"
                        and rescue_budget and rescue_budget[0] > 0):
                    # FLUX rescue still — stock failed exactly where the
                    # narration binding matters most (docs/HERO_SHOTS_SPEC.md)
                    rp = " ".join(x for x in (beat.get("cue", ""),
                                              beat.get("purpose", "")) if x).strip()
                    if rp and families_mod.enabled(cfg) and beat.get("family"):
                        # rescue stills speak the family's visual language too
                        rp = families_mod.compose_prompt(
                            rp, beat["family"], scene.get("domain_pack"))
                    if rp:
                        path = os.path.join(
                            outdir, f"s{scene['n']:02d}_b{index:02d}_rescue.png")
                        aspect = ("9:16 tall vertical"
                                  if _orientation(cfg) == "portrait"
                                  else "16:9 wide")
                        if ai_images.generate(rp, path, gemini_key, cfg, aspect):
                            rescue_budget[0] -= 1
                            beat_assets.append({"path": path, "kind": "image",
                                                "ai": True,
                                                "source_policy": policy})
                            print(f"[assets] scene {scene['n']} beat "
                                  f"{index + 1}: AI rescue still")
                if not beat_assets and policy != "custom":
                    photo = _stock_photo(beat_scene, outdir, pexels_key, used,
                                         _orientation(cfg), cfg, gemini_key)
                    if photo:
                        beat_assets.append(photo)
            if not beat_assets:
                beat_assets.append(fallback_graphic_asset(scene, beat, index))
                print(f"[assets] scene {scene['n']} beat {index + 1}: "
                      "animated evidence fallback")
            for asset in beat_assets:
                asset["beat_index"] = index
                asset.setdefault("source_policy", policy)
                if asset not in assets:
                    assets.append(asset)
        return assets

    # Overlay scenes need one strong background; the graphic carries the beat.
    if mode in ("kinetic", "stat", "card", "glass", "scale", "causal"):
        if not assets:
            # Long overlay scenes still need visual development behind the
            # graphic. Cap at three free stock clips to prevent a 30-second
            # card from sitting over one repeated background.
            max_shot = max(float(cfg["video"].get("max_shot_seconds", 5)), 0.5)
            overlay_clips = max(1, min(3, int(math.ceil(need_seconds / max_shot))))
            stock, _ = _stock_videos(scene, min(need_seconds, 10), outdir, cfg,
                                     pexels_key, used, max_clips=overlay_clips,
                                     gemini_key=gemini_key)
            assets.extend(stock)
        if not assets:
            photo = _stock_photo(scene, outdir, pexels_key, used,
                                 _orientation(cfg), cfg, gemini_key)
            if photo:
                assets.append(photo)
    else:
        if _nasa_relevant(scene.get("search_terms", [])):
            nasa = _nasa_asset(scene, outdir, used, cfg, gemini_key)
            if nasa:
                assets.append(nasa)
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

    if not assets and rescue_budget and rescue_budget[0] > 0:
        # AI rescue still (non-beat path, e.g. shorts): stock produced nothing
        # for this scene — a generated still beats an off-topic substitute or
        # a gradient card (docs/HERO_SHOTS_SPEC.md).
        rp = (scene.get("ai_prompt") or scene.get("narration") or "").strip()
        if rp:
            path = os.path.join(outdir, f"s{scene['n']:02d}_rescue.png")
            aspect = ("9:16 tall vertical" if _orientation(cfg) == "portrait"
                      else "16:9 wide")
            if ai_images.generate(rp, path, gemini_key, cfg, aspect):
                rescue_budget[0] -= 1
                assets.append({"path": path, "kind": "image", "ai": True})
                print(f"[assets] scene {scene['n']}: AI rescue still")
    if not assets:  # absolute fallback — never show a solid colour card
        assets.append(fallback_graphic_asset(scene))
        print(f"[assets] scene {scene['n']}: animated evidence fallback")
    return assets
