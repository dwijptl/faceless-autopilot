"""Faceless Autopilot — orchestrator (Terra Incognita edition, Hindi).

topic -> script (Hindi) -> voiceover (Sarvam cloned voice, Kokoro fallback)
-> assets (AI + stock, never-repeat log) -> captions -> Remotion render
(rotating style packs, brand kit, outro, watermark) with MoviePy fallback
-> release files.

Reads learnings.md (analytics loop) to adapt length/pacing within bounds.
"""
import glob
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import soundfile as sf
import yaml

sys.path.insert(0, os.path.dirname(__file__))
import ai_images                    # noqa: E402
import align                         # noqa: E402
import analytics as analytics_mod   # noqa: E402
import assets as assets_mod         # noqa: E402
import captions as captions_mod     # noqa: E402
import factcheck                    # noqa: E402
import hero_shots                   # noqa: E402
import mapgen                       # noqa: E402
import motion as motion_mod         # noqa: E402
import postprocess                  # noqa: E402
import quality_report as quality_mod  # noqa: E402
import script_gen                   # noqa: E402
import sfx as sfx_mod               # noqa: E402
import tts as tts_mod               # noqa: E402
import visual_beats as visual_beats_mod  # noqa: E402
import vision_qc                    # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION_DIR = os.path.join(REPO_ROOT, "remotion")
STYLES = ["documentary", "kinetic", "editorial", "noir", "telemetry"]


def probe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60, check=True)
        return float(json.loads(out.stdout)["format"]["duration"])
    except Exception:
        return 6.0


def pick_music(workdir: str, cfg: dict, seed: str, style: str) -> str | None:
    if float(cfg["music"].get("volume", 0)) <= 0:
        return None
    tracks = []
    for ext in ("mp3", "wav", "m4a", "ogg"):
        tracks += glob.glob(os.path.join(REPO_ROOT, "music", f"*.{ext}"))
    if not tracks:
        if cfg["music"].get("auto_ambient", True):
            return sfx_mod.build_ambient_bed(workdir, seed, style, is_short=False)
        print("[music] no files in music/ — rendering without music")
        return None
    track = random.choice(sorted(tracks))
    dest = os.path.join(workdir, "music" + os.path.splitext(track)[1])
    shutil.copyfile(track, dest)
    return os.path.basename(dest)


def stage_brand(workdir: str) -> str | None:
    src = os.path.join(REPO_ROOT, "brand", "watermark.png")
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(workdir, "brand_watermark.png"))
        return "brand_watermark.png"
    return None


def render_remotion(manifest_path: str, workdir: str, final_path: str) -> None:
    cmd = ["npx", "remotion", "render", "src/index.ts", "Main",
           os.path.abspath(final_path),
           "--props", os.path.abspath(manifest_path),
           "--public-dir", os.path.abspath(workdir),
           "--concurrency", "2", "--log", "warn"]
    print("[render] remotion:", " ".join(cmd))
    subprocess.run(cmd, cwd=REMOTION_DIR, check=True, timeout=3.2 * 3600)
    if not os.path.exists(final_path) or os.path.getsize(final_path) < 500_000:
        raise RuntimeError("Remotion produced no/too-small output file")


def thumbnail_remotion(manifest_path: str, workdir: str, thumb_path: str) -> None:
    cmd = ["npx", "remotion", "still", "src/index.ts", "Thumb",
           os.path.abspath(thumb_path),
           "--props", os.path.abspath(manifest_path),
           "--public-dir", os.path.abspath(workdir), "--log", "warn"]
    subprocess.run(cmd, cwd=REMOTION_DIR, check=True, timeout=1200)


def _asset_manifest(asset: dict) -> dict:
    return {
        "path": os.path.basename(asset["path"]),
        "kind": asset["kind"],
        "duration": round(asset["duration"], 2) if asset.get("duration") else None,
        "ai": bool(asset.get("ai")),
    }


def _pad_reveal_pause(wav_path: str, seconds: float = 0.35) -> float:
    """Insert leading silence — the breath before the reveal. Fail-open."""
    try:
        data, sr = sf.read(wav_path, dtype="float32")
        shape = (int(seconds * sr), data.shape[1]) if getattr(data, "ndim", 1) > 1 \
            else int(seconds * sr)
        sf.write(wav_path, np.concatenate([np.zeros(shape, dtype="float32"), data]), sr)
        return seconds
    except Exception as exc:
        print(f"[tts] reveal pad skipped ({exc})")
        return 0.0


def _attach_hero(scenes: list[dict], poses: dict) -> None:
    """Pin the episode's recurring hero to the hook, the reveal and the
    payoff. G6: a 3-pose set (establish / action / final) keeps ONE
    consistent subject on screen while its state visibly changes with the
    journey — continuity stock people can never provide."""
    default = next(iter(poses.values()))
    wanted = {scenes[0]["n"]: poses.get("establish", default),
              scenes[-1]["n"]: poses.get("final", default)}
    reveal_n = next((sc["n"] for sc in scenes
                     if sc.get("delivery") == "reveal"), None)
    if reveal_n is not None and reveal_n not in wanted:
        wanted[reveal_n] = poses.get("action", default)
    for sc in scenes:
        path = wanted.get(sc["n"])
        if not path:
            continue
        beats = sc.get("visual_beats") or []
        bi = max(len(beats) - 1, 0) if sc["n"] == scenes[-1]["n"] else 0
        sc["assets"].insert(0, {"path": path, "kind": "image",
                                "ai": True, "duration": None,
                                "beat_index": bi})
    print(f"[hero] attached {len(poses)} pose(s) to scenes {sorted(wanted)}")



def _animate_hero_shots(scenes: list[dict], workdir: str, cfg: dict,
                        gemini_key: str) -> None:
    """3b) Kling i2v on the hook + reveal stills (docs/HERO_SHOTS_SPEC.md).
    Fail-open: any failure leaves the beat's existing still untouched."""
    hcfg = cfg.get("hero_shots", {})
    if not hcfg.get("enabled", False) or not os.environ.get("FAL_KEY", "").strip():
        return
    hero_shots.begin_run()
    seconds = int(hcfg.get("seconds", 5))
    retries = max(0, int(hcfg.get("max_retries", 1)))
    targets = hero_shots.select_targets(scenes, int(hcfg.get("max_per_video", 2)))
    for sc, bi in targets:
        beats = sc.get("visual_beats") or []
        cue = ((beats[bi].get("cue") if bi < len(beats) else "")
               or sc.get("narration", "")[:160])
        if hero_shots.should_skip(cue):
            print(f"[hero] scene {sc['n']}: cue needs faces/text — keeping still")
            continue
        beat_assets = [a for a in sc.get("assets", [])
                       if a.get("beat_index") == bi]
        still = next((a for a in beat_assets
                      if a["kind"] == "image" and a.get("ai")),
                     next((a for a in beat_assets if a["kind"] == "image"),
                          None))
        if still is None:
            prompt = (sc.get("ai_prompt") or cue).strip()
            path = os.path.join(workdir, f"s{sc['n']:02d}_hero_still.png")
            if prompt and ai_images.generate(prompt, path, gemini_key, cfg,
                                             aspect="16:9 wide"):
                still = {"path": path, "kind": "image", "ai": True,
                         "duration": None, "beat_index": bi}
                sc["assets"].insert(0, still)
            else:
                continue  # nothing worth animating — beat keeps stock
        clip = os.path.join(workdir, f"s{sc['n']:02d}_hero.mp4")
        mprompt = hero_shots.motion_prompt(cue, cfg)
        ok, extra = False, ""
        for attempt in range(1 + retries):
            if attempt:
                hero_shots.note_retry()
            if not hero_shots.animate(still["path"], mprompt, clip, cfg,
                                      seconds, extra_negative=extra):
                break  # budget / network — a retry cannot change the verdict
            if vision_qc.frame_ok(
                    clip, "video", cue or sc.get("title", ""),
                    "cinematic hero shot", gemini_key, cfg,
                    forbidden=(sc.get("forbidden_visuals") or []) + [
                        "warped or morphing objects", "garbled or fake text",
                        "broken anatomy, extra limbs"],
                    source="generated"):
                ok = True
                break
            extra = "deformed geometry, unstable shapes"
            print(f"[hero] scene {sc['n']}: QC rejected the clip"
                  + (" — retrying" if attempt < retries
                     else " — shipping the still"))
        if ok:
            sc["assets"].insert(0, {"path": clip, "kind": "video", "ai": True,
                                    "hero": True, "beat_index": bi,
                                    "duration": probe_duration(clip)})
            print(f"[hero] scene {sc['n']} beat {bi}: animated hero shot live")
    print(f"[hero] {hero_shots.usage_summary()}")


def _thumb_mean_luma(path: str) -> float:
    try:
        from PIL import Image, ImageStat
        return float(ImageStat.Stat(Image.open(path).convert("L")).mean[0])
    except Exception:
        return 128.0


def _lift_thumb(path: str, target: float = 55.0) -> None:
    """Adaptive lift for murky AI thumbnails. A thumbnail that reads as a
    black rectangle at 160px feed size earns zero clicks — brighten toward a
    minimum mean luminance while keeping contrast. Fail-open."""
    try:
        from PIL import Image, ImageEnhance
        mean = _thumb_mean_luma(path)
        if mean >= target:
            return
        img = Image.open(path).convert("RGB")
        factor = min(target / max(mean, 12.0), 1.9)
        img = ImageEnhance.Brightness(img).enhance(factor)
        img = ImageEnhance.Contrast(img).enhance(1.12)
        img.save(path, quality=92)
        print(f"[thumb] lifted dark thumbnail (mean luma {mean:.0f} -> ~{target:.0f})")
    except Exception as exc:
        print(f"[thumb] lift skipped ({exc})")


def _chapters_block(scenes: list[dict]) -> str:
    """YouTube chapter timestamps from scene starts (first must be 0:00)."""
    if len(scenes) < 3:
        return ""
    lines = []
    for i, sc in enumerate(scenes):
        t = 0 if i == 0 else int(round(sc["start"]))
        title = str(sc.get("title", "")).strip() or f"Scene {sc['n']}"
        lines.append(f"{t // 60}:{t % 60:02d} {title}")
    return "\n".join(lines)


def _impact_start(sc: dict, overlay_seconds: float) -> float:
    """Word-synced start (seconds, scene-relative) for the scene's graphic.

    Uses Sarvam STT word timestamps so a stat/kinetic/card/glass overlay
    enters exactly when its key word or number is spoken — motion motivated
    by narration is what separates 'edited' from 'animated'. Fails open to
    0.0 (scene start) when alignment or a match is unavailable.
    """
    words = sc.get("word_times") or []
    mode = sc.get("visual_mode", "broll")
    if mode not in ("stat", "kinetic", "card", "glass") or not words:
        return 0.0

    def norm(text) -> str:
        return re.sub(r"[^\wऀ-ॿ]", "", str(text)).lower()

    targets: list[str] = []
    if mode == "stat":
        v = (sc.get("stat") or {}).get("value")
        if isinstance(v, (int, float)):
            targets.append(str(int(v)) if float(v).is_integer() else str(v))
    elif mode == "kinetic":
        targets += str(sc.get("kinetic_text", "")).split()[:2]
    elif mode == "card":
        targets += str((sc.get("card") or {}).get("headline", "")).split()[:2]
    elif mode == "glass":
        g = sc.get("glass") or {}
        v = g.get("value")
        if isinstance(v, (int, float)):
            targets.append(str(int(v)) if float(v).is_integer() else str(v))
        targets += str(g.get("headline", "")).split()[:2]
    targets = [norm(t) for t in targets if len(norm(t)) >= 2]
    if not targets:
        return 0.0

    for item in words:
        try:
            word, start = str(item[0]), float(item[1])
        except (TypeError, ValueError, IndexError):
            continue
        w = norm(word)
        if not w:
            continue
        if any(t in w or w in t for t in targets):
            impact = max(start - 0.15, 0.0)  # slight pre-roll: card lands ON the word
            # keep runway so most of the overlay window fits before scene end
            latest = max(sc["audio_duration"] - overlay_seconds * 0.8, 0.0)
            return round(min(impact, latest), 3)
    return 0.0


def _visual_beat_manifest(scene: dict) -> list[dict]:
    result = []
    for index, beat in enumerate(scene.get("visual_beats") or []):
        result.append({
            "start": round(float(beat.get("start", 0)), 3),
            "duration": round(float(beat.get("duration", 0)), 3),
            "cue": str(beat.get("cue", "")),
            "purpose": str(beat.get("purpose", "")),
            "searchTerms": list(beat.get("search_terms") or []),
            "assets": [_asset_manifest(a) for a in scene.get("assets", [])
                       if a.get("beat_index") == index],
        })
    return result


def main() -> None:
    t0 = time.time()
    tts_mod.reset_run_state()
    with open(os.path.join(REPO_ROOT, "config.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not gemini_key or not pexels_key:
        sys.exit("Missing GEMINI_API_KEY or PEXELS_API_KEY (add them as repo secrets)")
    if (cfg.get("tts", {}).get("engine") == "sarvam"
            and not os.environ.get("SARVAM_API_KEY", "").strip()):
        print("[warn] SARVAM_API_KEY not set — narration will use the Kokoro "
              "fallback voice, not your cloned voice")

    # learnings -> prompt context + bounded overrides -----------------------
    learnings = script_gen.load_learnings(REPO_ROOT)
    overrides = analytics_mod.parse_overrides(learnings) if learnings else {}
    if overrides.get("target_minutes"):
        cfg["video"]["target_minutes"] = overrides["target_minutes"]
    if overrides.get("scenes_max"):
        cfg["video"]["scenes_max"] = overrides["scenes_max"]
    if overrides.get("tts_speed"):
        cfg["tts"]["speed"] = overrides["tts_speed"]
    if overrides:
        print(f"[learn] applied overrides: {overrides}")

    stamp = time.strftime("%Y-%m-%d_%H%M")
    outdir = os.path.join(REPO_ROOT, "out", stamp)
    workdir = os.path.join(outdir, "work")
    os.makedirs(workdir, exist_ok=True)

    # style rotation: deterministic, based on how many videos exist ---------
    done_count = 0
    try:
        with open(os.path.join(REPO_ROOT, "topics_done.txt"), encoding="utf-8") as f:
            done_count = sum(1 for ln in f
                             if ln.strip() and not ln.startswith("#")
                             and not ln.startswith("NEXT:"))
    except Exception:
        pass
    style = STYLES[done_count % len(STYLES)]
    # telemetry shares editorial's photographic grammar + ambient palette for
    # the python-side helpers that don't know the new pack
    base_style = "editorial" if style == "telemetry" else style
    cfg.setdefault("render", {})["style_pack"] = base_style  # steers AI-image look
    print(f"=== Faceless Autopilot run {stamp} · style: {style} ===")

    # 1) topic + script ------------------------------------------------------
    topic = script_gen.pick_topic(cfg, gemini_key,
                                  os.path.join(REPO_ROOT, "topics_done.txt"),
                                  learnings)
    script = script_gen.generate_script(cfg, topic, gemini_key, learnings)
    fact_report = factcheck.check_script(script, cfg, gemini_key)
    with open(os.path.join(outdir, "claims.json"), "w", encoding="utf-8") as f:
        json.dump(fact_report, f, indent=2, ensure_ascii=False)  # claim ledger
    with open(os.path.join(outdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    # recurring hero — G6 3-pose set: one consistent subject whose STATE
    # changes with the journey (establish -> action -> final)
    hero_poses: dict = {}
    hp = (script.get("hero_prompt") or "").strip()
    if hp:
        pose_specs = [
            ("establish", "Establishing wide shot: the subject small against "
                          "its vast environment, sense of scale, the journey "
                          "about to begin"),
            ("action", "Dynamic mid-journey moment: the subject under visible "
                       "environmental stress, dramatic closer framing"),
            ("final", "Journey's end state: the subject transformed by the "
                      "conditions, quiet monumental conclusive lighting"),
        ]
        for name, pose in pose_specs:
            p = os.path.join(workdir, f"hero_{name}.png")
            if ai_images.generate(
                    f"{hp}. {pose}. CONTINUITY: the exact same subject with "
                    "identical design, materials, colors and proportions in "
                    "every image — one continuous character across a series.",
                    p, gemini_key, cfg, aspect="16:9 wide"):
                hero_poses[name] = p
        if hero_poses:
            print(f"[hero] pose set generated: {sorted(hero_poses)}")

    # 2) voiceover -----------------------------------------------------------
    fps = int(cfg["video"]["fps"])
    xfade = float(cfg["video"].get("crossfade", 0.4))
    scenes, offset = [], 0.0
    for sc in script["scenes"]:
        wav = os.path.join(workdir, f"vo_s{sc['n']:02d}.wav")
        dur = tts_mod.synth_scene(sc["narration"], wav, cfg,
                                  sc.get("delivery", "calm"))
        if sc.get("delivery") == "reveal":
            dur += _pad_reveal_pause(wav)  # the breath before the punchline
        scenes.append({**sc, "audio_path": wav, "audio_duration": dur,
                       "start": max(offset, 0.0)})
        offset += dur - xfade
        print(f"[tts] scene {sc['n']}: {dur:.1f}s ({sc.get('visual_mode', 'broll')}"
              f"/{sc.get('delivery', 'calm')})")
    scenes[0]["start"] = 0.0
    print(f"[tts] {tts_mod.usage_summary()}")
    total_speech = scenes[-1]["start"] + scenes[-1]["audio_duration"]
    target_s = float(cfg["video"]["target_minutes"]) * 60
    if not 0.85 * target_s <= total_speech <= 1.15 * target_s:
        print(f"[warn] narration runs {total_speech / 60:.1f} min vs "
              f"{target_s / 60:.1f} min target "
              f"({total_speech / target_s * 100:.0f}%) — check word budget "
              f"and channel.wpm calibration")
    voice_fallback = (str(cfg.get("tts", {}).get("engine", "")).lower() == "sarvam"
                      and tts_mod.fallback_used())

    # Real timestamps are optional. Failed alignment is deliberately visible
    # in metadata but never prevents a manual-review release.
    aligned_scenes = 0
    if cfg.get("captions", {}).get("align", True):
        for sc in scenes:
            sc["word_times"] = align.scene_word_times(sc, cfg)
            aligned_scenes += int(bool(sc["word_times"]))
    caption_status = (f"aligned (Sarvam STT, {aligned_scenes}/{len(scenes)} scenes)"
                      if aligned_scenes == len(scenes) else
                      (f"mixed ({aligned_scenes}/{len(scenes)} scenes aligned)"
                       if aligned_scenes else "estimated (heuristic)"))

    for sc in scenes:
        visual_beats_mod.time_scene(sc)

    # 2b) map scenes — render branded world/region maps (fail -> b-roll)
    if cfg.get("maps", {}).get("enabled", True):
        for sc in scenes:
            if sc.get("visual_mode") == "map":
                mp = sc.get("map") or {}
                render = None
                if mp.get("lat") is not None and mp.get("lon") is not None:
                    render = mapgen.render_scene_maps(
                        mp["lat"], mp["lon"], workdir, sc["n"], portrait=False)
                if render:
                    render["label"] = str(mp.get("label", ""))[:40]
                    sc["map_render"] = render
                else:
                    sc["visual_mode"] = "broll"
    else:
        for sc in scenes:
            if sc.get("visual_mode") == "map":
                sc["visual_mode"] = "broll"

    # 3) assets — AI first where scripted, stock fallback, never repeat -----
    log_path = os.path.join(REPO_ROOT, "assets_used.json")
    usage_log = assets_mod.load_usage_log(log_path)
    vision_qc.begin_run(cfg)
    assets_mod.reset_episode_state()  # fresh luma/duplicate guards per video
    used: set = set(usage_log["pexels"])
    used_prompts: set = set(usage_log["prompts"])
    aicfg = cfg.get("ai_images", {})
    if os.environ.get("FAL_KEY", "").strip():  # FLUX on -> richer AI visuals
        ai_budget = [int(aicfg.get("max_per_video_flux", 4))]
    else:
        ai_budget = [int(aicfg.get("max_per_video", 2))]
    rescue_budget = [int(aicfg.get("rescue_budget", 0))]
    for sc in scenes:
        sc["forbidden_visuals"] = script.get("forbidden_visuals") or []
        sc["assets"] = assets_mod.fetch_scene_assets(
            sc, sc["audio_duration"], workdir, cfg, pexels_key, gemini_key,
            used, used_prompts, ai_budget, rescue_budget=rescue_budget)
        for a in sc["assets"]:
            a["duration"] = probe_duration(a["path"]) if a["kind"] == "video" else None
    usage_log["pexels"] = sorted(used)
    usage_log["prompts"] = sorted(used_prompts)
    assets_mod.save_usage_log(log_path, usage_log)
    if hero_poses:
        _attach_hero(scenes, hero_poses)

    # 3b) animated hero shots — hook + reveal come alive (fail-open) --------
    _animate_hero_shots(scenes, workdir, cfg, gemini_key)

    # 4) captions ------------------------------------------------------------
    events, srt = captions_mod.build_captions(scenes, cfg["captions"]["max_chars"])
    with open(os.path.join(outdir, "captions.srt"), "w", encoding="utf-8") as f:
        f.write(srt)

    # 4b) deterministic motion library + sound design + dedicated thumbnail ----
    motion_seed = f"{script['title']}:{style}"
    motion_mod.decorate_scenes(scenes, motion_seed)
    cta_event = motion_mod.plan_cta(scenes, cfg, motion_seed, is_short=False)
    sfx_events = sfx_mod.plan_events(scenes, cfg, workdir, cta_event)
    music_automation = sfx_mod.plan_music_automation(scenes, cfg)
    music_path = pick_music(workdir, cfg, motion_seed, base_style)
    thumb_ai = None
    tp = (script.get("thumb_prompt") or "").strip()
    if tp:
        p = os.path.join(workdir, "thumb_ai.png")
        if ai_images.generate(tp, p, gemini_key, cfg, aspect="16:9 wide"):
            if _thumb_mean_luma(p) < 42:  # murky — one brighter retry
                print("[thumb] too dark for feed size — regenerating brighter")
                bright_tp = (tp + " The subject is LARGE in frame with bright "
                             "dramatic rim lighting and luminous volumetric "
                             "light — clearly readable as a tiny thumbnail, "
                             "not a dark murky image.")
                ai_images.generate(bright_tp, p, gemini_key, cfg,
                                   aspect="16:9 wide")
            _lift_thumb(p)
            thumb_ai = "thumb_ai.png"
            print("[thumb] dedicated AI thumbnail generated")

    # 5) manifest ------------------------------------------------------------
    rcfg = cfg.get("render", {})
    brand_cfg = cfg.get("brand", {})
    overlay_seconds = float(cfg.get("longform_quality", {})
                            .get("overlay_seconds", 5.0))
    for sc in scenes:
        sc["impact_start"] = _impact_start(sc, overlay_seconds)
        if sc["impact_start"] > 0:
            print(f"[sync] scene {sc['n']}: {sc.get('visual_mode')} graphic "
                  f"word-synced to +{sc['impact_start']:.2f}s")
    manifest = {"manifest": {
        "fps": fps,
        "width": int(cfg["video"]["width"]),
        "height": int(cfg["video"]["height"]),
        "xfadeFrames": max(int(round(xfade * fps)), 1),
        "maxShotSeconds": float(cfg["video"].get("max_shot_seconds", 5)),
        "overlaySeconds": overlay_seconds,
        "style": style,
        "variableLabel": str((script.get("changing_variable") or {})
                             .get("label", "")).upper()[:18],
        "variableUnit": str((script.get("changing_variable") or {})
                            .get("unit", ""))[:8],
        "accent": rcfg.get("accent", "#FFB020"),
        "progressBar": bool(rcfg.get("progress_bar", True)),
        "brandName": brand_cfg.get("name", ""),
        "brandTagline": brand_cfg.get("tagline", ""),
        "watermarkPath": stage_brand(workdir),
        "watermarkOpacity": float(brand_cfg.get("watermark_opacity", 0.08)),
        "outroSeconds": float(cfg["video"].get("outro_seconds", 4)),
        "title": script["title"],
        "thumbText": script.get("thumb_text", script["title"][:24]),
        "thumbHeadline": script.get("thumb_headline", ""),
        "thumbQuestion": script.get("thumb_question", ""),
        "thumbAiPath": thumb_ai,
        "motionSeed": motion_seed,
        "cta": cta_event,
        "sfx": sfx_events,
        "musicPath": music_path,
        "musicVolume": float(cfg["music"].get("volume", 0.12)),
        "musicLoopSafe": music_path == "ambient_auto.wav",
        "musicAutomation": music_automation,
        "musicTransitionSeconds": float(cfg.get("longform_quality", {})
                                        .get("dynamic_music", {})
                                        .get("transition_seconds", 0.45)),
        "captions": [{"start": round(s, 3), "end": round(e, 3), "text": t}
                     for s, e, t in events
                     if bool(cfg["captions"].get("enabled", True))],
        "scenes": [{
            "n": sc["n"],
            "start": round(sc["start"], 3),
            "impactStart": sc.get("impact_start", 0.0),
            "delivery": sc.get("delivery", "calm"),
            "milestone": sc.get("milestone") or {},
            "title": sc.get("title", ""),
            "visualMode": sc.get("visual_mode", "broll"),
            "kineticText": sc.get("kinetic_text", ""),
            "stat": sc.get("stat", {}) or {},
            "card": sc.get("card", {}) or {},
            "glass": sc.get("glass", {}) or {},
            "map": sc.get("map_render") or {},
            "motion": sc.get("motion") or {},
            "audioPath": os.path.basename(sc["audio_path"]),
            "audioDuration": round(sc["audio_duration"], 3),
            "assets": [_asset_manifest(a) for a in sc["assets"]],
            "visualBeats": _visual_beat_manifest(sc),
        } for sc in scenes],
    }}
    manifest_path = os.path.join(workdir, "props.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 6) render ----------------------------------------------------------------
    final_path = os.path.join(outdir, "final.mp4")
    engine = rcfg.get("engine", "remotion")
    used_engine = engine
    if engine == "remotion":
        try:
            render_remotion(manifest_path, workdir, final_path)
        except Exception as e:
            print(f"[render] Remotion failed ({e}) -> falling back to MoviePy")
            used_engine = "moviepy-fallback"
            import render as render_mod
            render_mod.render(scenes, events, final_path, cfg)
    else:
        used_engine = "moviepy"
        import render as render_mod
        render_mod.render(scenes, events, final_path, cfg)
    postprocess.master_delivery(final_path, cfg)
    duration = probe_duration(final_path)
    quality_report = quality_mod.audit_delivery(
        final_path, manifest["manifest"], cfg,
        os.path.join(outdir, "quality_report.json"))
    try:  # hero telemetry travels with the audit (docs/HERO_SHOTS_SPEC.md)
        quality_report.setdefault("metrics", {}).update(hero_shots.metrics())
        with open(os.path.join(outdir, "quality_report.json"), "w",
                  encoding="utf-8") as f:
            json.dump(quality_report, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    # G11 — one-vision-call contact-sheet audit of the ACTUAL render
    render_audit = vision_qc.audit_render(
        final_path, cfg, gemini_key,
        forbidden=script.get("forbidden_visuals") or [],
        out_path=os.path.join(outdir, "render_audit.json"))

    # 7) thumbnail ---------------------------------------------------------------
    thumb_path = os.path.join(outdir, "thumbnail.jpg")
    try:
        thumbnail_remotion(manifest_path, workdir, thumb_path)
        assert os.path.getsize(thumb_path) > 10_000
    except Exception as e:
        print(f"[thumb] Remotion still failed ({e}) -> PIL fallback")
        import thumbnail as thumb_mod
        thumb_assets = ([{"path": os.path.join(workdir, "thumb_ai.png"),
                          "kind": "image"}] if thumb_ai else []) + scenes[0]["assets"]
        thumb_mod.make_thumbnail(thumb_assets, script["thumb_text"], thumb_path)

    # 7b) thumbnail variants — same hero, alternate text, for YouTube's native
    # Test & Compare (upload all; YouTube picks the winner by watch-time share)
    try:
        seen = {manifest["manifest"]["thumbText"]}
        letter = ord("b")
        for opt in (script.get("thumb_options") or [])[:3]:
            text = str(opt.get("text", "")).strip()[:24]
            if not text or text in seen:
                continue
            seen.add(text)
            variant = json.loads(json.dumps(manifest, ensure_ascii=False))
            variant["manifest"]["thumbText"] = text
            vpath = os.path.join(workdir, f"props_thumb_{chr(letter)}.json")
            with open(vpath, "w", encoding="utf-8") as f:
                json.dump(variant, f, ensure_ascii=False)
            vout = os.path.join(outdir, f"thumbnail_{chr(letter)}.jpg")
            thumbnail_remotion(vpath, workdir, vout)
            print(f"[thumb] Test & Compare variant: {os.path.basename(vout)} "
                  f"({text})")
            letter += 1
    except Exception as exc:
        print(f"[thumb] variants skipped ({exc})")

    # 8) metadata ----------------------------------------------------------------
    n_ai = sum(1 for sc in scenes for a in sc["assets"] if a.get("ai"))
    voice_line = tts_mod.ENGINE_USED or "unknown"
    fact_line = factcheck.markdown(fact_report)
    # gate modes: false = advisory · high_risk = block on unsupported
    # high-risk claims only · true/all = block on any unsupported claim
    gate_mode = str(cfg.get("factcheck", {}).get("gate", False)).strip().lower()
    if gate_mode in ("true", "1", "all"):
        fact_requires_review = fact_report.get("unsupported", 0) > 0
    elif gate_mode == "high_risk":
        fact_requires_review = bool(fact_report.get("high_risk_unsupported"))
    else:
        fact_requires_review = False
    quality_requires_review = (
        bool(cfg.get("longform_quality", {}).get("render_qc", {}).get("gate", False))
        and not quality_report.get("passed", False))
    audit_requires_review = not render_audit.get("publishable", True)
    draft_release = (voice_fallback or fact_requires_review
                     or quality_requires_review or audit_requires_review)
    status_voice = "⚠️ FALLBACK — DO NOT PUBLISH" if voice_fallback else "OK (cloned)"
    status_fact = (f"⚠️ REVIEW CLAIMS ({fact_report.get('unsupported', 0)} unsupported)"
                   if fact_requires_review else fact_report.get("status", "unknown"))
    status_quality = ("OK" if quality_report.get("passed") else
                      f"⚠️ REVIEW ({len(quality_report.get('errors', []))} errors)")
    voice_banner = ("> ⚠️ **VOICE FALLBACK — DO NOT PUBLISH.** This run used Kokoro, "
                    "not your cloned Sarvam voice. Re-run when Sarvam is available.\n\n"
                    if voice_fallback else "")
    fact_banner = ("> ⚠️ **UNSUPPORTED HIGH-RISK CLAIMS — DO NOT PUBLISH** until "
                   "verified/removed: "
                   + "; ".join(fact_report.get("high_risk_unsupported", [])[:3])
                   + "\n\n" if fact_requires_review else "")
    audit_banner = ("> ⚠️ **RENDER AUDIT — DO NOT PUBLISH:** "
                    + "; ".join(str(i.get("note", "")) for i in
                                render_audit.get("issues", [])
                                if str(i.get("severity", "")).lower() == "serious")[:200]
                    + "\n\n" if audit_requires_review else "")
    status_audit = ("⚠️ REVIEW" if audit_requires_review
                    else render_audit.get("status", "skipped"))
    meta = f"""## {script['title']}

{voice_banner}{fact_banner}{audit_banner}**Reliability:** Voice: {status_voice} | Captions: {caption_status} | Fact-check: {status_fact} | Quality: {status_quality} | Render audit: {status_audit}

**Duration:** {duration / 60:.1f} min · **Scenes:** {len(scenes)} · **Style:** {style} ·
**AI visuals:** {n_ai} · **Run:** {stamp} · **Renderer:** {used_engine} ·
**Voice:** {voice_line}

### Description (paste into YouTube)

{script['description']}

### Chapters (paste at the END of the description — enables YouTube chapters)

{_chapters_block(scenes) or "_not enough scenes for chapters_"}

### Tags

{', '.join(script.get('tags', []))}

### Title & thumbnail alternates (pick your favourite before uploading)

{chr(10).join(f"{i + 1}. {t}" for i, t in enumerate(script.get('title_options') or [])) or "_none generated_"}

{chr(10).join(f"- **{o.get('text', '')}** — {o.get('concept', '')}" for o in (script.get('thumb_options') or []))}

### Reliability report

{fact_line}

### Checklist before uploading

- [ ] Watch the video once — you are the editor of record
- [ ] Spot-check any specific numbers/claims in the narration
- [ ] SCHEDULE the publish for 16:00–17:30 IST — Hindi long-form viewing
      peaks 6–8 PM IST; going live 2-3h early lets YouTube index + test it
- [ ] Set the video language to **Hindi** in YouTube Studio (Details → Video language)
- [ ] Upload ALL thumbnails (thumbnail.jpg + thumbnail_b/c.jpg if present) via
      Studio's **Test & Compare** — YouTube picks the winner by watch-time
- [ ] If your music track is CC-BY, add the artist credit to the description
- [ ] Upload `captions.srt` in YouTube Studio → Subtitles (language: Hindi)
- [ ] Occasionally drop fresh Studio analytics CSVs into analytics/ so the
      channel keeps learning

*Assets: Pexels + Gemini AI images (commercial-safe). Voice: {voice_line}
(your cloned Sarvam voice; Kokoro Apache-2.0 fallback). Motion design:
Remotion. Brand: Terra Incognita.*
"""
    with open(os.path.join(outdir, "metadata.md"), "w", encoding="utf-8") as f:
        f.write(meta)

    with open(os.path.join(outdir, "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"draft_release": draft_release, "voice_fallback": voice_fallback,
                   "voice": voice_line, "captions": caption_status,
                   "factcheck": fact_report,
                   "quality": quality_report,
                   "render_audit": render_audit,
                   "motion_library": {
                       "seed": motion_seed,
                       "cta": cta_event,
                       "scene_variants": [sc.get("motion", {}) for sc in scenes],
                       "sound_events": len(sfx_events),
                   }}, f, indent=2, ensure_ascii=False)

    # beat-timestamp map — lets future analytics map retention dips to the
    # exact scene, visual mode and asset choice that was on screen
    with open(os.path.join(outdir, "beats.json"), "w", encoding="utf-8") as f:
        json.dump([{"n": sc["n"], "title": sc.get("title", ""),
                    "start": round(sc["start"], 2),
                    "end": round(sc["start"] + sc["audio_duration"], 2),
                    "visualMode": sc.get("visual_mode", "broll"),
                    "visualRole": sc.get("visual_role", ""),
                    "delivery": sc.get("delivery", "calm"),
                    "assets": [f"{a['kind']}:{'ai' if a.get('ai') else 'stock'}"
                               for a in sc["assets"]]}
                   for sc in scenes], f, indent=2, ensure_ascii=False)

    script_gen.log_topic_done(topic, os.path.join(REPO_ROOT, "topics_done.txt"))
    tease = str(script.get("next_tease_topic", "")).strip()
    if tease:
        # the on-screen tease is a promise — lock it as the next episode
        with open(os.path.join(REPO_ROOT, "topics_done.txt"), "a",
                  encoding="utf-8") as f:
            f.write(f"NEXT: {tease}\n")
        print(f"[script] next episode locked to the on-screen tease: {tease}")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        safe_title = script["title"].replace('"', "'").replace("\n", " ")
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"stamp={stamp}\ndir={os.path.relpath(outdir, os.getcwd())}\n"
                    f"title={safe_title}\nvoice_fallback={str(voice_fallback).lower()}\n"
                    f"draft_release={str(draft_release).lower()}\n")

    print(f"=== Done in {(time.time() - t0) / 60:.1f} min -> {final_path} "
          f"({duration / 60:.1f} min, style={style}, engine={used_engine}) ===")
    if voice_fallback and cfg.get("tts", {}).get("fail_on_fallback", False):
        raise RuntimeError("Sarvam failed; artifacts were produced but publishing is blocked")


if __name__ == "__main__":
    main()
