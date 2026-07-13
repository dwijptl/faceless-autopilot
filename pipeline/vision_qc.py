"""Pre-render visual QC — kills the "AI slop" class of errors.

Before a downloaded stock clip/photo is accepted, one frame goes to Gemini
vision (free tier) with the scene's narration: does this footage plausibly
illustrate it for a nature/space documentary? Rejects studio, commercial,
product, zoo-enclosure and metaphor shots that keyword search sneaks in.
When the episode declares forbidden_visuals (its continuity contract), any
frame showing them is rejected even if it matches the scene semantically —
this is what keeps a scuba diver out of an unprotected-human premise.

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
             api_key: str, cfg: dict, forbidden: list | None = None,
             source: str = "generated") -> bool:
    """True = accept the asset. Fail-open on transient errors — EXCEPT stock
    assets once the budget is exhausted: unchecked stock is the top source of
    contradiction failures (FAILURES.md), so those are rejected and the scene
    routes to the truthful fallback hierarchy (AI still -> card -> gradient)
    instead of shipping an unverified clip."""
    global _requests_remaining
    if not cfg.get("qc", {}).get("visual_check", True) or not api_key:
        return True
    if _requests_remaining is None:
        begin_run(cfg)
    if _requests_remaining <= 0:
        if source == "stock":
            print("[qc] budget exhausted; rejecting unchecked stock "
                  "(truthful fallback will be used instead)")
            return False
        print("[qc] budget exhausted; accepting generated asset unchecked")
        return True
    images = _frame_jpegs_b64(media_path, kind, int(cfg.get("qc", {}).get("frames", 3)))
    if not images:
        return True
    contract = ""
    if forbidden:
        contract = (
            "EPISODE CONTINUITY CONTRACT — REJECT IMMEDIATELY if ANY frame "
            f"shows any of: {', '.join(str(f) for f in forbidden[:6])}. "
            "These break this episode's premise even when they otherwise "
            "match the scene.\n")
    prompt = (
        "You are the visual editor of a premium nature/space documentary "
        "channel. These frames were fetched for the scene below.\n"
        f'SCENE NARRATION (Hindi): "{scene_desc[:280]}"\n'
        f'SEARCH INTENT: "{search_term}"\n'
        + contract +
        "ACCEPT only if the footage plausibly belongs in this documentary "
        "scene. If the narration or search intent names a real landmark, "
        "machine, animal, planet or anatomical structure, REJECT lookalikes "
        "and generic substitutes that could mislead the viewer. REJECT if it is: studio/commercial/product imagery, food or "
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


def _models_list(cfg: dict) -> list[str]:
    return [cfg["llm"].get("model", "gemini-2.5-flash")] + list(
        cfg["llm"].get("fallback_models", []))


def pick_best(candidates: list, scene_desc: str, search_term: str,
              api_key: str, cfg: dict, forbidden: list | None = None) -> int:
    """G4 candidate ranking — ONE vision call compares candidate assets for a
    beat and picks the semantically better one. candidates = [(path, kind)].
    Returns 0-based index of the winner, or -1 when NONE is acceptable.
    Fail-open: any problem returns 0 (first candidate)."""
    global _requests_remaining
    if len(candidates) < 2:
        return 0
    if not cfg.get("qc", {}).get("visual_check", True) or not api_key:
        return 0
    if _requests_remaining is None:
        begin_run(cfg)
    if _requests_remaining <= 0:
        return 0
    parts = []
    for i, (path, kind) in enumerate(candidates):
        frames = _frame_jpegs_b64(path, kind, 1)
        if not frames:
            return 0
        parts.append({"text": f"CANDIDATE {i + 1}:"})
        parts.append({"inline_data": {"mime_type": "image/jpeg",
                                      "data": frames[0]}})
    contract = ""
    if forbidden:
        contract = ("REJECT any candidate showing: "
                    f"{', '.join(str(f) for f in forbidden[:6])}. ")
    parts.append({"text": (
        "You are the visual editor of a premium nature/space documentary. "
        f'SCENE NARRATION (Hindi): "{scene_desc[:280]}"\n'
        f'SEARCH INTENT: "{search_term}"\n' + contract +
        "Pick the candidate that best and most TRUTHFULLY illustrates this "
        "scene (semantic accuracy first, then composition, light, and how "
        "well it reads behind captions). "
        'Answer ONLY JSON: {"best": <1-based candidate number, or 0 if NONE '
        'is acceptable>, "reason": "<5 words>"}')})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"response_mime_type": "application/json",
                                 "temperature": 0.1}}
    for model in _models_list(cfg)[:2]:
        try:
            _requests_remaining -= 1
            r = requests.post(f"{API_BASE}/{model}:generateContent?key={api_key}",
                              json=body, timeout=60)
            if r.status_code == 429:
                time.sleep(10)
                continue
            if r.status_code in (400, 404):
                continue
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = re.sub(r"^```(json)?|```$", "", text.strip(),
                          flags=re.MULTILINE).strip()
            best = int(json.loads(text).get("best", 1))
            if best <= 0:
                return -1
            return min(best, len(candidates)) - 1
        except Exception:
            return 0  # fail-open to first candidate
    return 0


def audit_render(final_path: str, cfg: dict, api_key: str,
                 forbidden: list | None = None,
                 out_path: str | None = None) -> dict:
    """G11 post-render contact-sheet audit. Extracts one frame every ~12s,
    tiles them into a single sheet and asks ONE vision question: would the
    final publish reviewer flag anything? A `serious` issue flips
    publishable=False (run.py marks the release DRAFT). Fail-open."""
    report = {"status": "skipped", "publishable": True, "issues": []}
    try:
        if not api_key or not cfg.get("qc", {}).get("render_audit", True):
            return _write_audit(report, out_path)
        duration = _duration(final_path) or 0.0
        if duration < 30:
            return _write_audit(report, out_path)
        step = max(duration / 24.0, 12.0)
        positions, pos = [], step / 2
        while pos < duration and len(positions) < 24:
            positions.append(pos)
            pos += step
        tiles = []
        for p in positions:
            r = subprocess.run(
                ["ffmpeg", "-v", "error", "-ss", f"{p:.2f}", "-i", final_path,
                 "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"],
                check=True, timeout=60, capture_output=True)
            img = Image.open(io.BytesIO(r.stdout)).convert("RGB")
            img.thumbnail((320, 180))
            tiles.append(img)
        if not tiles:
            return _write_audit(report, out_path)
        cols = 4
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 320, rows * 180), (0, 0, 0))
        for i, im in enumerate(tiles):
            sheet.paste(im, ((i % cols) * 320, (i // cols) * 180))
        buf = io.BytesIO()
        sheet.save(buf, format="JPEG", quality=70)
        b64 = base64.b64encode(buf.getvalue()).decode()
        contract = ""
        if forbidden:
            contract = ("This episode's premise FORBIDS showing: "
                        f"{', '.join(str(f) for f in forbidden[:6])}. ")
        prompt = (
            "This contact sheet holds frames sampled at equal intervals "
            "(left-to-right, top-to-bottom) from a finished Hindi science "
            "documentary. " + contract +
            "Audit it as the final publish reviewer. Flag ONLY real problems: "
            "(1) a frame contradicting the premise/forbidden list, "
            "(2) near-black unreadable frames, (3) obviously identical "
            "repeated shots, (4) broken/overlapping text. Severity `serious` "
            "means a viewer would notice and lose trust; else `minor`. "
            'Return ONLY JSON: {"issues":[{"severity":"serious","note":'
            '"<10 words>","frame":3}]} — empty list when clean.')
        body = {"contents": [{"parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                    {"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json",
                                     "temperature": 0.1}}
        for model in _models_list(cfg)[:2]:
            r = requests.post(f"{API_BASE}/{model}:generateContent?key={api_key}",
                              json=body, timeout=90)
            if r.status_code == 429:
                time.sleep(10)
                continue
            if r.status_code in (400, 404):
                continue
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = re.sub(r"^```(json)?|```$", "", text.strip(),
                          flags=re.MULTILINE).strip()
            issues = json.loads(text).get("issues") or []
            report["issues"] = issues[:10]
            report["publishable"] = not any(
                str(i.get("severity", "")).lower() == "serious" for i in issues)
            report["status"] = "ok"
            n_serious = sum(1 for i in issues
                            if str(i.get('severity', '')).lower() == 'serious')
            print(f"[audit] render audit: {len(issues)} issue(s), "
                  f"{n_serious} serious")
            break
    except Exception as exc:
        report["status"] = f"skipped ({exc})"
        print(f"[audit] {report['status']}")
    return _write_audit(report, out_path)


def _write_audit(report: dict, out_path: str | None) -> dict:
    if out_path:
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return report
