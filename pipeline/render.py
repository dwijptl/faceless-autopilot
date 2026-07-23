"""Stage 4b/5 — assembly: b-roll conformed to voiceover, Ken Burns on stills,
scene crossfades, burned captions, ducked music, 1080p H.264 export.

Uses MoviePy 2.x API. Captions render with Noto Sans Devanagari first (Hindi;
installed by the workflow via fonts-noto-core), DejaVu as Latin fallback.
"""
import glob
import os
import random

import numpy as np
from moviepy import (AudioFileClip, CompositeAudioClip, CompositeVideoClip,
                     ImageClip, TextClip, VideoFileClip, afx,
                     concatenate_videoclips, vfx)

# Same palette family as assets._gradient_card so the fallback background
# reads as part of the house style.
_FALLBACK_PALETTES = [
    ((10, 20, 40), (18, 35, 63)),
    ((16, 12, 34), (70, 44, 108)),
    ((8, 26, 26), (22, 78, 74)),
    ((28, 18, 8), (104, 64, 26)),
]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font() -> str:
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            return f
    raise RuntimeError("No usable font found (install fonts-noto-core / fonts-dejavu-core)")


def _fit(clip, w: int, h: int):
    """Scale to cover the frame, then center-crop to exactly w x h."""
    scale = max(w / clip.w, h / clip.h)
    clip = clip.resized(scale)
    return clip.cropped(x_center=clip.w / 2, y_center=clip.h / 2, width=w, height=h)


def _ken_burns(img_path: str, duration: float, w: int, h: int, zoom_in: bool):
    base = ImageClip(img_path).with_duration(duration)
    scale = max(w / base.w, h / base.h) * 1.12  # headroom for the move
    base = base.resized(scale)
    z0, z1 = (1.0, 1.1) if zoom_in else (1.1, 1.0)
    moving = base.resized(lambda t: z0 + (z1 - z0) * (t / max(duration, 0.01)))
    return CompositeVideoClip([moving.with_position("center")], size=(w, h)).with_duration(duration)


def _gradient_frame(w: int, h: int, seed: int):
    """Vertical gradient as an (h, w, 3) uint8 array — no disk I/O."""
    top, bottom = _FALLBACK_PALETTES[seed % len(_FALLBACK_PALETTES)]
    ramp = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]        # (h, 1)
    top_a, bot_a = np.array(top, np.float32), np.array(bottom, np.float32)
    col = top_a[None, :] + (bot_a - top_a)[None, :] * ramp            # (h, 3)
    return np.repeat(col[:, None, :], w, axis=1).astype("uint8")      # (h, w, 3)


def _fallback_visual(duration: float, w: int, h: int, seed: int, zoom_in: bool):
    """Gentle Ken Burns over a house-palette gradient.

    Map scenes (and any scene whose sourcing produced nothing) reach this
    MoviePy fallback renderer with an empty asset list: Remotion draws their
    background itself via MapZoom, but this renderer has no such component.
    Rather than divide by zero, put a living gradient behind the voiceover —
    the same "never fail" gradient-card fallback assets.fetch_scene_assets
    uses for every other empty-asset path.
    """
    base = ImageClip(_gradient_frame(w, h, seed)).with_duration(duration)
    base = base.resized(1.12)  # headroom so the move never exposes an edge
    z0, z1 = (1.0, 1.08) if zoom_in else (1.08, 1.0)
    moving = base.resized(lambda t: z0 + (z1 - z0) * (t / max(duration, 0.01)))
    return CompositeVideoClip([moving.with_position("center")],
                              size=(w, h)).with_duration(duration)


def _scene_visual(assets: list[dict], duration: float, cfg: dict, rng: random.Random):
    w, h, max_shot = cfg["video"]["width"], cfg["video"]["height"], cfg["video"]["max_shot_seconds"]
    if not assets:
        return _fallback_visual(duration, w, h, int(rng.random() * 1000),
                                rng.random() < 0.5)
    parts, remaining, i = [], duration, 0
    zoom_in = rng.random() < 0.5
    while remaining > 0.05:
        a = assets[i % len(assets)]
        seg = min(max_shot, remaining) if remaining >= 2.5 else remaining
        if a["kind"] == "video":
            src = VideoFileClip(a["path"], audio=False)
            usable = max(src.duration - 0.2, 0.5)
            seg = min(seg, usable)
            start = rng.uniform(0, max(usable - seg, 0)) if i >= len(assets) else 0
            parts.append(_fit(src.subclipped(start, start + seg), w, h))
        else:
            parts.append(_ken_burns(a["path"], seg, w, h, zoom_in))
            zoom_in = not zoom_in
        remaining -= seg
        i += 1
    visual = parts[0] if len(parts) == 1 else concatenate_videoclips(parts)
    return visual.with_duration(duration)


def _caption_layer(events: list[tuple], cfg: dict, total: float):
    w, h = cfg["video"]["width"], cfg["video"]["height"]
    fs = cfg["captions"].get("font_size", 58)
    layers = []
    for start, end, text in events:
        if start >= total:
            continue
        tc = TextClip(
            font=_font(), text=text, font_size=fs, color="white",
            stroke_color="black", stroke_width=max(2, fs // 18),
            method="caption", size=(int(w * 0.78), None), text_align="center",
        )
        layers.append(
            tc.with_start(start)
              .with_duration(max(min(end, total) - start, 0.1))
              .with_position(("center", int(h * 0.78)))
        )
    return layers


def _music(total: float, cfg: dict):
    vol = float(cfg["music"].get("volume", 0))
    if vol <= 0:
        return None
    tracks = sorted(glob.glob("music/*.mp3") + glob.glob("music/*.wav")
                    + glob.glob("music/*.m4a") + glob.glob("music/*.ogg"))
    if not tracks:
        print("[render] no music files in music/ — rendering without music")
        return None
    rng = random.Random(int(total * 1000))
    m = AudioFileClip(rng.choice(tracks))
    fade = float(cfg["music"].get("fade", 1.5))
    return m.with_effects([
        afx.AudioLoop(duration=total),
        afx.MultiplyVolume(vol),
        afx.AudioFadeIn(fade),
        afx.AudioFadeOut(fade),
    ])


def render(scenes: list[dict], events: list[tuple], out_path: str, cfg: dict) -> float:
    """scenes: [{assets, audio_path, audio_duration}] in order. Returns duration."""
    w, h = cfg["video"]["width"], cfg["video"]["height"]
    xfade = float(cfg["video"].get("crossfade", 0.4))
    rng = random.Random(42)

    scene_clips = []
    for idx, sc in enumerate(scenes):
        visual = _scene_visual(sc["assets"], sc["audio_duration"], cfg, rng)
        clip = visual.with_audio(AudioFileClip(sc["audio_path"]))
        if idx > 0 and xfade > 0:
            clip = clip.with_effects([vfx.CrossFadeIn(xfade)])
        scene_clips.append(clip)
        print(f"[render] scene {idx + 1}/{len(scenes)} prepared "
              f"({sc['audio_duration']:.1f}s, {len(sc['assets'])} assets)")

    video = concatenate_videoclips(scene_clips, method="compose",
                                   padding=-xfade if xfade > 0 else 0)

    layers = [video]
    if cfg["captions"].get("enabled", True) and events:
        layers += _caption_layer(events, cfg, video.duration)
    final = CompositeVideoClip(layers, size=(w, h)).with_duration(video.duration)

    music = _music(video.duration, cfg)
    audio = CompositeAudioClip([video.audio, music]) if music else video.audio
    final = final.with_audio(audio)

    final.write_videofile(
        out_path,
        fps=cfg["video"]["fps"],
        codec="libx264",
        audio_codec="aac",
        bitrate=cfg["video"].get("bitrate", "6000k"),
        preset="medium",
        threads=os.cpu_count() or 2,
        logger="bar",
    )
    return final.duration
