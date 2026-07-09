"""Stage 3 — voiceover via Kokoro-82M (Apache 2.0, commercial-safe, CPU, $0).

Model files (~340 MB) are fetched once and cached by the workflow between runs.
"""
import os
import re

import numpy as np
import requests
import soundfile as sf

MODEL_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
MODEL_FILES = ["kokoro-v1.0.onnx", "voices-v1.0.bin"]
SAMPLE_RATE = 24000

_kokoro = None


def _cache_dir() -> str:
    d = os.path.join(os.path.expanduser("~"), ".cache", "kokoro")
    os.makedirs(d, exist_ok=True)
    return d


def _ensure_model() -> tuple[str, str]:
    paths = []
    for name in MODEL_FILES:
        path = os.path.join(_cache_dir(), name)
        if not os.path.exists(path) or os.path.getsize(path) < 1_000_000:
            print(f"[tts] downloading {name} ...")
            with requests.get(f"{MODEL_BASE}/{name}", stream=True, timeout=1200) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 22):
                        f.write(chunk)
        paths.append(path)
    return paths[0], paths[1]


def _engine():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        model, voices = _ensure_model()
        _kokoro = Kokoro(model, voices)
    return _kokoro


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def synth_scene(text: str, wav_path: str, cfg: dict) -> float:
    """Synthesize one scene's narration to wav_path. Returns duration in seconds."""
    k = _engine()
    voice = cfg["tts"]["voice"]
    try:
        available = set(k.get_voices())
        if voice not in available:
            fallback = sorted(available)[0]
            print(f"[tts] voice '{voice}' not found, using '{fallback}'")
            voice = fallback
    except Exception:
        pass

    speed = float(cfg["tts"].get("speed", 1.0))
    lang = cfg["channel"].get("language", "en-us")
    gap = np.zeros(int(0.25 * SAMPLE_RATE), dtype=np.float32)
    chunks = []
    for sent in _sentences(text):
        samples, sr = k.create(sent, voice=voice, speed=speed, lang=lang)
        chunks.append(np.asarray(samples, dtype=np.float32))
        chunks.append(gap)
    if not chunks:
        chunks = [np.zeros(SAMPLE_RATE, dtype=np.float32)]
    # trailing breath before the next scene
    chunks.append(np.zeros(int(0.35 * SAMPLE_RATE), dtype=np.float32))
    audio = np.concatenate(chunks)

    peak = float(np.max(np.abs(audio))) or 1.0  # normalize to healthy loudness
    audio = audio * (0.89 / peak)
    sf.write(wav_path, audio, SAMPLE_RATE)
    return len(audio) / SAMPLE_RATE
