"""Faceless Autopilot — orchestrator.

topic -> script -> voiceover -> assets -> captions -> render -> metadata.
Everything lands in out/<YYYY-MM-DD_HHMM>/ and is published as a GitHub
Release by the workflow.
"""
import json
import os
import sys
import time

import yaml

sys.path.insert(0, os.path.dirname(__file__))
import assets as assets_mod          # noqa: E402
import captions as captions_mod     # noqa: E402
import script_gen                   # noqa: E402
import thumbnail as thumb_mod       # noqa: E402
import tts as tts_mod               # noqa: E402


def main() -> None:
    t0 = time.time()
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not gemini_key or not pexels_key:
        sys.exit("Missing GEMINI_API_KEY or PEXELS_API_KEY (add them as repo secrets)")

    stamp = time.strftime("%Y-%m-%d_%H%M")
    outdir = os.path.join("out", stamp)
    workdir = os.path.join(outdir, "work")
    os.makedirs(workdir, exist_ok=True)
    print(f"=== Faceless Autopilot run {stamp} ===")

    # 1) topic + script -----------------------------------------------------
    topic = script_gen.pick_topic(cfg, gemini_key)
    script = script_gen.generate_script(cfg, topic, gemini_key)
    with open(os.path.join(outdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    # 2) voiceover per scene (durations drive everything downstream) -------
    scenes = []
    offset = 0.0
    for sc in script["scenes"]:
        wav = os.path.join(workdir, f"vo_s{sc['n']:02d}.wav")
        dur = tts_mod.synth_scene(sc["narration"], wav, cfg)
        scenes.append({**sc, "audio_path": wav, "audio_duration": dur, "start": offset})
        offset += dur - float(cfg["video"].get("crossfade", 0.4))
        print(f"[tts] scene {sc['n']}: {dur:.1f}s")
    # crossfade overlap shifts caption starts; clamp first scene
    scenes[0]["start"] = 0.0

    # 3) assets per scene ---------------------------------------------------
    used_ids: set = set()
    for sc in scenes:
        sc["assets"] = assets_mod.fetch_scene_assets(
            sc, sc["audio_duration"], workdir, cfg, pexels_key, used_ids)

    # 4) captions -----------------------------------------------------------
    events, srt = captions_mod.build_captions(scenes, cfg["captions"]["max_chars"])
    srt_path = os.path.join(outdir, "captions.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt)

    # 5) render -------------------------------------------------------------
    import render as render_mod  # deferred: moviepy import is slow
    final_path = os.path.join(outdir, "final.mp4")
    duration = render_mod.render(scenes, events, final_path, cfg)

    # 6) thumbnail + metadata ----------------------------------------------
    thumb_mod.make_thumbnail(scenes[0]["assets"], script["thumb_text"],
                             os.path.join(outdir, "thumbnail.jpg"))

    meta = f"""## {script['title']}

**Duration:** {duration / 60:.1f} min · **Scenes:** {len(scenes)} · **Run:** {stamp}

### Description (paste into YouTube)

{script['description']}

### Tags

{', '.join(script.get('tags', []))}

### Checklist before uploading

- [ ] Watch the video once — you are the editor of record
- [ ] Spot-check any specific numbers/claims in the narration
- [ ] If your music track is CC-BY, add the artist credit to the description
- [ ] Upload `captions.srt` in YouTube Studio → Subtitles

*Assets: Pexels (free commercial license). Voice: Kokoro-82M (Apache 2.0). Made for $0.*
"""
    with open(os.path.join(outdir, "metadata.md"), "w", encoding="utf-8") as f:
        f.write(meta)

    script_gen.log_topic_done(topic)

    # expose outputs to the workflow ---------------------------------------
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        safe_title = script["title"].replace('"', "'").replace("\n", " ")
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"stamp={stamp}\ndir={outdir}\ntitle={safe_title}\n")

    print(f"=== Done in {(time.time() - t0) / 60:.1f} min -> {final_path} "
          f"({duration / 60:.1f} min video) ===")


if __name__ == "__main__":
    main()
