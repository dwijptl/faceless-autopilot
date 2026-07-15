"""Faceless Autopilot — SHORTS orchestrator (vertical 1080x1920, ~25s, Hindi).

Same machinery as run.py, tuned for Shorts/Reels: portrait assets, micro-scene
pacing, big centered captions, loop-friendly ending, no outro card. Shares the
brand kit, music, learnings and the never-repeat asset log with long-form.
"""
import copy
import glob
import json
import os
import random
import shutil
import subprocess
import sys
import time

import yaml

sys.path.insert(0, os.path.dirname(__file__))
import analytics as analytics_mod   # noqa: E402
import align                         # noqa: E402
import assets as assets_mod         # noqa: E402
import captions as captions_mod     # noqa: E402
import factcheck                    # noqa: E402
import mapgen                       # noqa: E402
import motion as motion_mod         # noqa: E402
import postprocess                  # noqa: E402
import script_gen                   # noqa: E402
import sfx as sfx_mod               # noqa: E402
import tts as tts_mod               # noqa: E402
import vision_qc                    # noqa: E402
from run import _impact_start       # noqa: E402  (word-synced overlay timing)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION_DIR = os.path.join(REPO_ROOT, "remotion")
STYLES = ["kinetic", "documentary", "noir", "editorial"]  # shorts lean punchy
DONE_FILE = os.path.join(REPO_ROOT, "topics_done_shorts.txt")


def probe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60, check=True)
        return float(json.loads(out.stdout)["format"]["duration"])
    except Exception:
        return 4.0


def short_cfg(cfg: dict) -> dict:
    """Derive an effective config for vertical shorts from config.yaml."""
    s = cfg.get("short", {})
    c = copy.deepcopy(cfg)
    c["video"].update({
        "width": 1080, "height": 1920,
        "target_minutes": s.get("target_seconds", 25) / 60,
        "scenes_min": s.get("scenes_min", 5),
        "scenes_max": s.get("scenes_max", 7),
        "crossfade": s.get("crossfade", 0.25),
        "max_shot_seconds": s.get("max_shot_seconds", 3.5),
        "outro_seconds": 0,
    })
    c["captions"]["max_chars"] = s.get("captions_max_chars", 14)
    c["music"]["volume"] = s.get("music_volume", 0.18)
    c["tts"]["speed"] = s.get("tts_speed", 1.0)
    c["render"]["progress_bar"] = bool(s.get("progress_bar", False))
    if os.environ.get("FAL_KEY", "").strip():  # FLUX on -> richer AI visuals
        c["ai_images"]["max_per_video"] = s.get("ai_images_max_flux", 2)
    else:
        c["ai_images"]["max_per_video"] = s.get("ai_images_max", 1)
    return c


def main() -> None:
    t0 = time.time()
    tts_mod.reset_run_state()
    with open(os.path.join(REPO_ROOT, "config.yaml"), encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f)
    cfg = short_cfg(base_cfg)

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not gemini_key or not pexels_key:
        sys.exit("Missing GEMINI_API_KEY or PEXELS_API_KEY")
    if (cfg.get("tts", {}).get("engine") == "sarvam"
            and not os.environ.get("SARVAM_API_KEY", "").strip()):
        print("[warn] SARVAM_API_KEY not set — narration will use the Kokoro "
              "fallback voice, not your cloned voice")

    learnings = script_gen.load_learnings(REPO_ROOT)

    stamp = time.strftime("%Y-%m-%d_%H%M")
    outdir = os.path.join(REPO_ROOT, "out", f"short_{stamp}")
    workdir = os.path.join(outdir, "work")
    os.makedirs(workdir, exist_ok=True)

    done_count = 0
    try:
        with open(DONE_FILE, encoding="utf-8") as f:
            done_count = sum(1 for ln in f if ln.strip() and not ln.startswith("#"))
    except Exception:
        pass
    style = STYLES[done_count % len(STYLES)]
    cfg.setdefault("render", {})["style_pack"] = style  # steers AI-image look
    print(f"=== Shorts run {stamp} · style: {style} ===")

    # 1) topic + short script ------------------------------------------------
    # Shorts are trailers: bias the topic toward the latest long-form episode
    # so each Short funnels viewers into it (set it as the Short's related
    # video in Studio). Never a full summary — ONE shocking fact/mechanism.
    trailer_hint = ""
    try:
        with open(os.path.join(REPO_ROOT, "topics_done.txt"),
                  encoding="utf-8") as f:
            long_topics = [ln.strip() for ln in f
                           if ln.strip() and not ln.startswith(("#", "NEXT:"))]
        if long_topics:
            trailer_hint = (
                "\n\nTRAILER PRIORITY: the channel's newest long-form episode "
                f"is '{long_topics[-1]}'. STRONGLY prefer a Short that "
                "extracts ONE shocking fact or mechanism from that episode — "
                "a trailer that makes viewers open the full video. Never "
                "summarize the whole episode, and never repeat a covered "
                "Short topic.")
    except Exception:
        pass
    topic = script_gen.pick_topic(cfg, gemini_key, DONE_FILE,
                                  (learnings or "") + trailer_hint)
    script = script_gen.generate_short_script(cfg, topic, gemini_key, learnings)
    fact_report = factcheck.check_script(script, cfg, gemini_key)
    with open(os.path.join(outdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    # 2) voiceover -------------------------------------------------------------
    fps = int(cfg["video"]["fps"])
    xfade = float(cfg["video"]["crossfade"])
    scenes, offset = [], 0.0
    short_settings = cfg.get("short", {})
    final_index = len(script["scenes"]) - 1
    for index, sc in enumerate(script["scenes"]):
        wav = os.path.join(workdir, f"vo_s{sc['n']:02d}.wav")
        tail_seconds = (float(short_settings.get("loop_tail_seconds", 0.06))
                        if index == final_index else 0.35)
        dur = tts_mod.synth_scene(sc["narration"], wav, cfg,
                                  sc.get("delivery", "calm"), tail_seconds=tail_seconds)
        scenes.append({**sc, "audio_path": wav, "audio_duration": dur,
                       "start": max(offset, 0.0)})
        offset += dur - xfade
        print(f"[tts] scene {sc['n']}: {dur:.1f}s ({sc.get('visual_mode')}"
              f"/{sc.get('delivery', 'calm')})")
    scenes[0]["start"] = 0.0
    print(f"[tts] {tts_mod.usage_summary()}")
    total_speech = scenes[-1]["start"] + scenes[-1]["audio_duration"]
    target_s = float(short_settings.get("target_seconds", 25))
    if total_speech > target_s * 1.25:
        print(f"[warn] short runs {total_speech:.1f}s vs {target_s:.0f}s target "
              f"(+{(total_speech / target_s - 1) * 100:.0f}%) — lower short.wpm "
              f"in config.yaml to calibrate the word budget")
    voice_fallback = (str(cfg.get("tts", {}).get("engine", "")).lower() == "sarvam"
                      and tts_mod.fallback_used())
    aligned_scenes = 0
    if cfg.get("captions", {}).get("align", True):
        for sc in scenes:
            sc["word_times"] = align.scene_word_times(sc, cfg)
            aligned_scenes += int(bool(sc["word_times"]))
    caption_status = (f"aligned (Sarvam STT, {aligned_scenes}/{len(scenes)} scenes)"
                      if aligned_scenes == len(scenes) else
                      (f"mixed ({aligned_scenes}/{len(scenes)} scenes aligned)"
                       if aligned_scenes else "estimated (heuristic)"))

    # 2b) map scenes (portrait) — fail -> b-roll
    if cfg.get("maps", {}).get("enabled", True):
        for sc in scenes:
            if sc.get("visual_mode") == "map":
                mp = sc.get("map") or {}
                render = None
                if mp.get("lat") is not None and mp.get("lon") is not None:
                    render = mapgen.render_scene_maps(
                        mp["lat"], mp["lon"], workdir, sc["n"], portrait=True)
                if render:
                    render["label"] = str(mp.get("label", ""))[:40]
                    sc["map_render"] = render
                else:
                    sc["visual_mode"] = "broll"
    else:
        for sc in scenes:
            if sc.get("visual_mode") == "map":
                sc["visual_mode"] = "broll"

    # 3) portrait assets (shared never-repeat log) -----------------------------
    log_path = os.path.join(REPO_ROOT, "assets_used.json")
    usage_log = assets_mod.load_usage_log(log_path)
    vision_qc.begin_run(cfg)
    used: set = set(usage_log["pexels"])
    used_prompts: set = set(usage_log["prompts"])
    ai_budget = [int(cfg["ai_images"].get("max_per_video", 1))]
    rescue_budget = [int(cfg.get("short", {}).get("rescue_budget", 3))]
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

    # 4) captions (small chunks = word-group pops) -----------------------------
    events, srt = captions_mod.build_captions(scenes, cfg["captions"]["max_chars"])
    with open(os.path.join(outdir, "captions.srt"), "w", encoding="utf-8") as f:
        f.write(srt)

    # 5) manifest --------------------------------------------------------------
    brand_cfg = cfg.get("brand", {})
    wm = None
    src_wm = os.path.join(REPO_ROOT, "brand", "watermark.png")
    if os.path.exists(src_wm):
        shutil.copyfile(src_wm, os.path.join(workdir, "brand_watermark.png"))
        wm = "brand_watermark.png"
    motion_seed = f"{script['title']}:{style}:short"
    music_rel = None
    tracks = []
    for ext in ("mp3", "wav", "m4a", "ogg"):
        tracks += glob.glob(os.path.join(REPO_ROOT, "music", f"*.{ext}"))
    if tracks and float(cfg["music"]["volume"]) > 0:
        track = random.choice(sorted(tracks))
        music_rel = "music" + os.path.splitext(track)[1]
        shutil.copyfile(track, os.path.join(workdir, music_rel))
    elif float(cfg["music"]["volume"]) > 0 and cfg["music"].get("auto_ambient", True):
        music_rel = sfx_mod.build_ambient_bed(
            workdir, motion_seed, style, is_short=True)

    motion_mod.decorate_scenes(scenes, motion_seed)
    cta_event = motion_mod.plan_cta(scenes, cfg, motion_seed, is_short=True)
    sfx_events = sfx_mod.plan_events(scenes, cfg, workdir, cta_event)

    # word-synced impact windows: the graphic enters on the spoken keyword
    overlay_seconds = float(short_settings.get("overlay_seconds", 3.5))
    for sc in scenes:
        sc["impact_start"] = _impact_start(sc, overlay_seconds)
        if sc["impact_start"] > 0:
            print(f"[sync] scene {sc['n']}: {sc.get('visual_mode')} graphic "
                  f"word-synced to +{sc['impact_start']:.2f}s")

    manifest = {"manifest": {
        "fps": fps, "width": 1080, "height": 1920,
        "xfadeFrames": max(int(round(xfade * fps)), 1),
        "maxShotSeconds": float(cfg["video"].get("max_shot_seconds", 2.4)),
        "overlaySeconds": overlay_seconds,
        "style": style,
        "accent": cfg["render"].get("accent", "#FFB020"),
        "progressBar": bool(cfg["render"].get("progress_bar", False)),
        "brandName": brand_cfg.get("name", ""),
        "brandTagline": brand_cfg.get("tagline", ""),
        "watermarkPath": wm,
        "watermarkOpacity": float(brand_cfg.get("watermark_opacity", 0.08)),
        "outroSeconds": 0,
        "captionY": float(cfg.get("short", {}).get("caption_y", 0.62)),
        "title": script["title"],
        "thumbText": script.get("thumb_text", ""),
        "motionSeed": motion_seed,
        "cta": cta_event,
        "sfx": sfx_events,
        "musicPath": music_rel,
        "musicVolume": float(cfg["music"]["volume"]),
        "musicLoopSafe": music_rel == "ambient_auto.wav",
        "captions": [{"start": round(s, 3), "end": round(e, 3), "text": t}
                     for s, e, t in events],
        "scenes": [{
            "n": sc["n"], "title": sc.get("title", ""),
            "start": round(sc["start"], 3),
            "impactStart": sc.get("impact_start", 0.0),
            "visualMode": sc.get("visual_mode", "broll"),
            "kineticText": sc.get("kinetic_text", ""),
            "stat": sc.get("stat", {}) or {},
            "card": sc.get("card", {}) or {},
            "glass": sc.get("glass", {}) or {},
            "map": sc.get("map_render") or {},
            "motion": sc.get("motion") or {},
            "audioPath": os.path.basename(sc["audio_path"]),
            "audioDuration": round(sc["audio_duration"], 3),
            "assets": [{
                "path": os.path.basename(a["path"]), "kind": a["kind"],
                "duration": round(a["duration"], 2) if a.get("duration") else None,
            } for a in sc["assets"]],
        } for sc in scenes],
    }}
    manifest_path = os.path.join(workdir, "props.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 6) render the "Short" composition ---------------------------------------
    final_path = os.path.join(outdir, "final.mp4")
    cmd = ["npx", "remotion", "render", "src/index.ts", "Short",
           os.path.abspath(final_path),
           "--props", os.path.abspath(manifest_path),
           "--public-dir", os.path.abspath(workdir),
           "--concurrency", "2", "--log", "warn"]
    print("[render] remotion:", " ".join(cmd))
    subprocess.run(cmd, cwd=REMOTION_DIR, check=True, timeout=2 * 3600)
    if not os.path.exists(final_path) or os.path.getsize(final_path) < 200_000:
        raise RuntimeError("Remotion produced no/too-small output")
    postprocess.master_delivery(final_path, cfg)
    duration = probe_duration(final_path)

    # 7) metadata ---------------------------------------------------------------
    voice_line = tts_mod.ENGINE_USED or "unknown"
    fact_line = factcheck.markdown(fact_report)
    gate_mode = str(cfg.get("factcheck", {}).get("gate", False)).strip().lower()
    if gate_mode in ("true", "1", "all"):
        fact_requires_review = fact_report.get("unsupported", 0) > 0
    elif gate_mode == "high_risk":
        fact_requires_review = bool(fact_report.get("high_risk_unsupported"))
    else:
        fact_requires_review = False
    draft_release = voice_fallback or fact_requires_review
    status_voice = "⚠️ FALLBACK — DO NOT PUBLISH" if voice_fallback else "OK (cloned)"
    status_fact = (f"⚠️ REVIEW CLAIMS ({fact_report.get('unsupported', 0)} unsupported)"
                   if fact_requires_review else fact_report.get("status", "unknown"))
    voice_banner = ("> ⚠️ **VOICE FALLBACK — DO NOT PUBLISH.** This run used Kokoro, "
                    "not your cloned Sarvam voice. Re-run when Sarvam is available.\n\n"
                    if voice_fallback else "")
    meta = f"""## {script['title']}

{voice_banner}**Reliability:** Voice: {status_voice} | Captions: {caption_status} | Fact-check: {status_fact}

**SHORT** · {duration:.0f}s · {len(scenes)} scenes · style: {style} ·
voice: {voice_line} · run {stamp}

### Description (paste into YouTube/Instagram)

{script['description']}

### Tags

{', '.join(script.get('tags', []))}

### Reliability report

{fact_line}

### Checklist

- [ ] Watch it once (it's {duration:.0f} seconds)
- [ ] Publish or schedule for 18:00–20:00 IST — Shorts scroll peaks 7–10 PM IST
- [ ] YouTube: upload as a regular video — vertical + <3 min = Short automatically
- [ ] Set the video language to **Hindi** in YouTube Studio
- [ ] Instagram: same MP4 works as a Reel
- [ ] Confirm the loop: does the ending feed the opening?

*Vertical b-roll: Pexels. Voice: {voice_line}. Motion: Remotion.*
"""
    with open(os.path.join(outdir, "metadata.md"), "w", encoding="utf-8") as f:
        f.write(meta)

    with open(os.path.join(outdir, "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump({"draft_release": draft_release, "voice_fallback": voice_fallback,
                   "voice": voice_line, "captions": caption_status,
                   "factcheck": fact_report,
                   "motion_library": {
                       "seed": motion_seed,
                       "cta": cta_event,
                       "scene_variants": [sc.get("motion", {}) for sc in scenes],
                       "sound_events": len(sfx_events),
                   }}, f, indent=2, ensure_ascii=False)

    script_gen.log_topic_done(topic, DONE_FILE)

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        safe_title = script["title"].replace('"', "'").replace("\n", " ")
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"stamp={stamp}\ndir={os.path.relpath(outdir, os.getcwd())}\n"
                    f"title={safe_title}\nvoice_fallback={str(voice_fallback).lower()}\n"
                    f"draft_release={str(draft_release).lower()}\n")

    print(f"=== Short done in {(time.time() - t0) / 60:.1f} min -> {final_path} "
          f"({duration:.0f}s, style={style}) ===")
    if voice_fallback and cfg.get("tts", {}).get("fail_on_fallback", False):
        raise RuntimeError("Sarvam failed; artifacts were produced but publishing is blocked")


if __name__ == "__main__":
    main()
