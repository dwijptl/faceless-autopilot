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
import shutil
import subprocess
import sys
import time

import yaml

sys.path.insert(0, os.path.dirname(__file__))
import ai_images                    # noqa: E402
import analytics as analytics_mod   # noqa: E402
import assets as assets_mod         # noqa: E402
import captions as captions_mod     # noqa: E402
import mapgen                       # noqa: E402
import script_gen                   # noqa: E402
import sfx as sfx_mod               # noqa: E402
import tts as tts_mod               # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION_DIR = os.path.join(REPO_ROOT, "remotion")
STYLES = ["documentary", "kinetic", "editorial", "noir"]


def probe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60, check=True)
        return float(json.loads(out.stdout)["format"]["duration"])
    except Exception:
        return 6.0


def pick_music(workdir: str, cfg: dict) -> str | None:
    if float(cfg["music"].get("volume", 0)) <= 0:
        return None
    tracks = []
    for ext in ("mp3", "wav", "m4a", "ogg"):
        tracks += glob.glob(os.path.join(REPO_ROOT, "music", f"*.{ext}"))
    if not tracks:
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


def main() -> None:
    t0 = time.time()
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
            done_count = sum(1 for ln in f if ln.strip() and not ln.startswith("#"))
    except Exception:
        pass
    style = STYLES[done_count % len(STYLES)]
    cfg.setdefault("render", {})["style_pack"] = style  # steers AI-image look
    print(f"=== Faceless Autopilot run {stamp} · style: {style} ===")

    # 1) topic + script ------------------------------------------------------
    topic = script_gen.pick_topic(cfg, gemini_key,
                                  os.path.join(REPO_ROOT, "topics_done.txt"),
                                  learnings)
    script = script_gen.generate_script(cfg, topic, gemini_key, learnings)
    with open(os.path.join(outdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    # 2) voiceover -----------------------------------------------------------
    fps = int(cfg["video"]["fps"])
    xfade = float(cfg["video"].get("crossfade", 0.4))
    scenes, offset = [], 0.0
    for sc in script["scenes"]:
        wav = os.path.join(workdir, f"vo_s{sc['n']:02d}.wav")
        dur = tts_mod.synth_scene(sc["narration"], wav, cfg,
                                  sc.get("delivery", "calm"))
        scenes.append({**sc, "audio_path": wav, "audio_duration": dur,
                       "start": max(offset, 0.0)})
        offset += dur - xfade
        print(f"[tts] scene {sc['n']}: {dur:.1f}s ({sc.get('visual_mode', 'broll')}"
              f"/{sc.get('delivery', 'calm')})")
    scenes[0]["start"] = 0.0
    print(f"[tts] {tts_mod.usage_summary()}")

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
    used: set = set(usage_log["pexels"])
    used_prompts: set = set(usage_log["prompts"])
    aicfg = cfg.get("ai_images", {})
    if os.environ.get("FAL_KEY", "").strip():  # FLUX on -> richer AI visuals
        ai_budget = [int(aicfg.get("max_per_video_flux", 4))]
    else:
        ai_budget = [int(aicfg.get("max_per_video", 2))]
    for sc in scenes:
        sc["assets"] = assets_mod.fetch_scene_assets(
            sc, sc["audio_duration"], workdir, cfg, pexels_key, gemini_key,
            used, used_prompts, ai_budget)
        for a in sc["assets"]:
            a["duration"] = probe_duration(a["path"]) if a["kind"] == "video" else None
    usage_log["pexels"] = sorted(used)
    usage_log["prompts"] = sorted(used_prompts)
    assets_mod.save_usage_log(log_path, usage_log)

    # 4) captions ------------------------------------------------------------
    events, srt = captions_mod.build_captions(scenes, cfg["captions"]["max_chars"])
    with open(os.path.join(outdir, "captions.srt"), "w", encoding="utf-8") as f:
        f.write(srt)

    # 4b) sound design + dedicated AI thumbnail --------------------------------
    sfx_events = sfx_mod.plan_events(scenes, cfg, workdir)
    thumb_ai = None
    tp = (script.get("thumb_prompt") or "").strip()
    if tp:
        p = os.path.join(workdir, "thumb_ai.png")
        if ai_images.generate(tp, p, gemini_key, cfg, aspect="16:9 wide"):
            thumb_ai = "thumb_ai.png"
            print("[thumb] dedicated AI thumbnail generated")

    # 5) manifest ------------------------------------------------------------
    rcfg = cfg.get("render", {})
    brand_cfg = cfg.get("brand", {})
    manifest = {"manifest": {
        "fps": fps,
        "width": int(cfg["video"]["width"]),
        "height": int(cfg["video"]["height"]),
        "xfadeFrames": max(int(round(xfade * fps)), 1),
        "style": style,
        "accent": rcfg.get("accent", "#FFB020"),
        "progressBar": bool(rcfg.get("progress_bar", True)),
        "brandName": brand_cfg.get("name", ""),
        "brandTagline": brand_cfg.get("tagline", ""),
        "watermarkPath": stage_brand(workdir),
        "watermarkOpacity": float(brand_cfg.get("watermark_opacity", 0.08)),
        "outroSeconds": float(cfg["video"].get("outro_seconds", 4)),
        "title": script["title"],
        "thumbText": script.get("thumb_text", script["title"][:24]),
        "thumbAiPath": thumb_ai,
        "sfx": sfx_events,
        "musicPath": pick_music(workdir, cfg),
        "musicVolume": float(cfg["music"].get("volume", 0.12)),
        "captions": [{"start": round(s, 3), "end": round(e, 3), "text": t}
                     for s, e, t in events
                     if bool(cfg["captions"].get("enabled", True))],
        "scenes": [{
            "n": sc["n"],
            "title": sc.get("title", ""),
            "visualMode": sc.get("visual_mode", "broll"),
            "kineticText": sc.get("kinetic_text", ""),
            "stat": sc.get("stat", {}) or {},
            "map": sc.get("map_render") or {},
            "audioPath": os.path.basename(sc["audio_path"]),
            "audioDuration": round(sc["audio_duration"], 3),
            "assets": [{
                "path": os.path.basename(a["path"]),
                "kind": a["kind"],
                "duration": round(a["duration"], 2) if a.get("duration") else None,
            } for a in sc["assets"]],
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
    duration = probe_duration(final_path)

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

    # 8) metadata ----------------------------------------------------------------
    n_ai = sum(1 for sc in scenes for a in sc["assets"] if a.get("ai"))
    voice_line = tts_mod.ENGINE_USED or "unknown"
    meta = f"""## {script['title']}

**Duration:** {duration / 60:.1f} min · **Scenes:** {len(scenes)} · **Style:** {style} ·
**AI visuals:** {n_ai} · **Run:** {stamp} · **Renderer:** {used_engine} ·
**Voice:** {voice_line}

### Description (paste into YouTube)

{script['description']}

### Tags

{', '.join(script.get('tags', []))}

### Checklist before uploading

- [ ] Watch the video once — you are the editor of record
- [ ] Spot-check any specific numbers/claims in the narration
- [ ] SCHEDULE the publish for 16:00–17:30 IST — Hindi long-form viewing
      peaks 6–8 PM IST; going live 2-3h early lets YouTube index + test it
- [ ] Set the video language to **Hindi** in YouTube Studio (Details → Video language)
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

    script_gen.log_topic_done(topic, os.path.join(REPO_ROOT, "topics_done.txt"))

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        safe_title = script["title"].replace('"', "'").replace("\n", " ")
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"stamp={stamp}\ndir={os.path.relpath(outdir, os.getcwd())}\n"
                    f"title={safe_title}\n")

    print(f"=== Done in {(time.time() - t0) / 60:.1f} min -> {final_path} "
          f"({duration / 60:.1f} min, style={style}, engine={used_engine}) ===")


if __name__ == "__main__":
    main()
