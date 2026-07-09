"""Faceless Autopilot — orchestrator.

topic -> script -> voiceover -> assets -> captions -> render -> metadata.

Rendering engine: Remotion (React-based motion design: spring animations,
per-scene transitions, animated captions, film grain) with an automatic
MoviePy fallback so a render problem can never kill the run.

Everything lands in out/<YYYY-MM-DD_HHMM>/ and is published as a GitHub
Release by the workflow.
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
import assets as assets_mod          # noqa: E402
import captions as captions_mod     # noqa: E402
import script_gen                   # noqa: E402
import tts as tts_mod               # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION_DIR = os.path.join(REPO_ROOT, "remotion")


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
    tracks = sorted(glob.glob(os.path.join(REPO_ROOT, "music", "*.mp3"))
                    + glob.glob(os.path.join(REPO_ROOT, "music", "*.wav"))
                    + glob.glob(os.path.join(REPO_ROOT, "music", "*.m4a"))
                    + glob.glob(os.path.join(REPO_ROOT, "music", "*.ogg")))
    if not tracks:
        print("[music] no files in music/ — rendering without music")
        return None
    track = random.choice(tracks)
    dest = os.path.join(workdir, "music" + os.path.splitext(track)[1])
    shutil.copyfile(track, dest)
    return os.path.basename(dest)


def render_remotion(manifest_path: str, workdir: str, final_path: str) -> None:
    cmd = [
        "npx", "remotion", "render", "src/index.ts", "Main",
        os.path.abspath(final_path),
        "--props", os.path.abspath(manifest_path),
        "--public-dir", os.path.abspath(workdir),
        "--concurrency", "2",
        "--log", "warn",
    ]
    print("[render] remotion:", " ".join(cmd))
    subprocess.run(cmd, cwd=REMOTION_DIR, check=True, timeout=3.2 * 3600)
    if not os.path.exists(final_path) or os.path.getsize(final_path) < 500_000:
        raise RuntimeError("Remotion produced no/too-small output file")


def thumbnail_remotion(manifest_path: str, workdir: str, thumb_path: str) -> None:
    cmd = [
        "npx", "remotion", "still", "src/index.ts", "Thumb",
        os.path.abspath(thumb_path),
        "--props", os.path.abspath(manifest_path),
        "--public-dir", os.path.abspath(workdir),
        "--log", "warn",
    ]
    subprocess.run(cmd, cwd=REMOTION_DIR, check=True, timeout=1200)


def main() -> None:
    t0 = time.time()
    with open(os.path.join(REPO_ROOT, "config.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not gemini_key or not pexels_key:
        sys.exit("Missing GEMINI_API_KEY or PEXELS_API_KEY (add them as repo secrets)")

    stamp = time.strftime("%Y-%m-%d_%H%M")
    outdir = os.path.join(REPO_ROOT, "out", stamp)
    workdir = os.path.join(outdir, "work")
    os.makedirs(workdir, exist_ok=True)
    print(f"=== Faceless Autopilot run {stamp} ===")

    # 1) topic + script -----------------------------------------------------
    topic = script_gen.pick_topic(cfg, gemini_key,
                                  os.path.join(REPO_ROOT, "topics_done.txt"))
    script = script_gen.generate_script(cfg, topic, gemini_key)
    with open(os.path.join(outdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    # 2) voiceover per scene (durations drive everything downstream) -------
    fps = int(cfg["video"]["fps"])
    xfade = float(cfg["video"].get("crossfade", 0.4))
    scenes = []
    offset = 0.0
    for sc in script["scenes"]:
        wav = os.path.join(workdir, f"vo_s{sc['n']:02d}.wav")
        dur = tts_mod.synth_scene(sc["narration"], wav, cfg)
        scenes.append({**sc, "audio_path": wav, "audio_duration": dur,
                       "start": max(offset, 0.0)})
        offset += dur - xfade
        print(f"[tts] scene {sc['n']}: {dur:.1f}s")
    scenes[0]["start"] = 0.0

    # 3) assets per scene ---------------------------------------------------
    used_ids: set = set()
    for sc in scenes:
        sc["assets"] = assets_mod.fetch_scene_assets(
            sc, sc["audio_duration"], workdir, cfg, pexels_key, used_ids)
        for a in sc["assets"]:
            a["duration"] = probe_duration(a["path"]) if a["kind"] == "video" else None

    # 4) captions -----------------------------------------------------------
    events, srt = captions_mod.build_captions(scenes, cfg["captions"]["max_chars"])
    with open(os.path.join(outdir, "captions.srt"), "w", encoding="utf-8") as f:
        f.write(srt)

    # 5) manifest for the Remotion renderer ---------------------------------
    rcfg = cfg.get("render", {})
    music_rel = pick_music(workdir, cfg)
    manifest = {
        "manifest": {
            "fps": fps,
            "width": int(cfg["video"]["width"]),
            "height": int(cfg["video"]["height"]),
            "xfadeFrames": max(int(round(xfade * fps)), 1),
            "accent": rcfg.get("accent", "#FFD24A"),
            "progressBar": bool(rcfg.get("progress_bar", True)),
            "title": script["title"],
            "thumbText": script.get("thumb_text", script["title"][:24]),
            "musicPath": music_rel,
            "musicVolume": float(cfg["music"].get("volume", 0.12)),
            "captions": [
                {"start": round(s, 3), "end": round(e, 3), "text": t}
                for s, e, t in events
                if bool(cfg["captions"].get("enabled", True))
            ],
            "scenes": [
                {
                    "n": sc["n"],
                    "title": sc.get("title", ""),
                    "audioPath": os.path.basename(sc["audio_path"]),
                    "audioDuration": round(sc["audio_duration"], 3),
                    "assets": [
                        {
                            "path": os.path.basename(a["path"]),
                            "kind": a["kind"],
                            "duration": round(a["duration"], 2) if a.get("duration") else None,
                        }
                        for a in sc["assets"]
                    ],
                }
                for sc in scenes
            ],
        }
    }
    manifest_path = os.path.join(workdir, "props.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # 6) render: Remotion first, MoviePy as automatic fallback --------------
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

    # 7) thumbnail (Remotion still -> PIL fallback) --------------------------
    thumb_path = os.path.join(outdir, "thumbnail.jpg")
    try:
        thumbnail_remotion(manifest_path, workdir, thumb_path)
        assert os.path.getsize(thumb_path) > 10_000
    except Exception as e:
        print(f"[thumb] Remotion still failed ({e}) -> PIL fallback")
        import thumbnail as thumb_mod
        thumb_mod.make_thumbnail(scenes[0]["assets"], script["thumb_text"], thumb_path)

    # 8) metadata ------------------------------------------------------------
    meta = f"""## {script['title']}

**Duration:** {duration / 60:.1f} min · **Scenes:** {len(scenes)} · **Run:** {stamp} · **Renderer:** {used_engine}

### Description (paste into YouTube)

{script['description']}

### Tags

{', '.join(script.get('tags', []))}

### Checklist before uploading

- [ ] Watch the video once — you are the editor of record
- [ ] Spot-check any specific numbers/claims in the narration
- [ ] If your music track is CC-BY, add the artist credit to the description
- [ ] Upload `captions.srt` in YouTube Studio → Subtitles

*Assets: Pexels (free commercial license). Voice: Kokoro-82M (Apache 2.0).
Motion design: Remotion (free license for individuals & teams ≤3). Made for $0.*
"""
    with open(os.path.join(outdir, "metadata.md"), "w", encoding="utf-8") as f:
        f.write(meta)

    script_gen.log_topic_done(topic, os.path.join(REPO_ROOT, "topics_done.txt"))

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        safe_title = script["title"].replace('"', "'").replace("\n", " ")
        rel_out = os.path.relpath(outdir, os.getcwd())
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"stamp={stamp}\ndir={rel_out}\ntitle={safe_title}\n")

    print(f"=== Done in {(time.time() - t0) / 60:.1f} min -> {final_path} "
          f"({duration / 60:.1f} min video, engine={used_engine}) ===")


if __name__ == "__main__":
    main()
