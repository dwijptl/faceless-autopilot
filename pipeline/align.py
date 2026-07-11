"""Sarvam STT-assisted word timing for the narration captions.

This stage intentionally fails open: captions fall back to the deterministic
character-rate estimate when an API response is missing, malformed or does not
cover the expected speech.
"""
import os
import tempfile

import requests
import soundfile as sf


STT_URL = "https://api.sarvam.ai/speech-to-text"


def _windows(samples, sample_rate: int, seconds: float):
    frames = max(1, int(seconds * sample_rate))
    for start in range(0, len(samples), frames):
        yield start / sample_rate, samples[start:start + frames]


def _read_word_times(payload: dict, offset: float) -> list[tuple[str, float, float]]:
    timestamps = payload.get("timestamps") or {}
    words = timestamps.get("words") or []
    starts = timestamps.get("start_time_seconds") or []
    ends = timestamps.get("end_time_seconds") or []
    if not (len(words) == len(starts) == len(ends)):
        return []
    return [(str(word), float(start) + offset, float(end) + offset)
            for word, start, end in zip(words, starts, ends)]


def scene_word_times(scene: dict, cfg: dict) -> list[tuple[str, float, float]] | None:
    """Return scene-relative word times, or ``None`` when alignment is unsafe."""
    ccfg = cfg.get("captions", {})
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not ccfg.get("align", True) or not key:
        return None
    try:
        audio, sample_rate = sf.read(scene["audio_path"], dtype="float32")
        if getattr(audio, "ndim", 1) > 1:
            audio = audio.mean(axis=1)
        window_seconds = float(ccfg.get("align_window_seconds", 25))
        headers = {"api-subscription-key": key}
        result: list[tuple[str, float, float]] = []
        with tempfile.TemporaryDirectory(prefix="sarvam-align-") as tmp:
            for number, (offset, samples) in enumerate(_windows(audio, sample_rate, window_seconds)):
                path = os.path.join(tmp, f"window-{number}.wav")
                sf.write(path, samples, sample_rate)
                with open(path, "rb") as wav:
                    response = requests.post(
                        STT_URL,
                        headers=headers,
                        files={"file": ("narration.wav", wav, "audio/wav")},
                        data={"language_code": cfg["channel"].get("language", "hi-IN"),
                              "model": "saaras:v3", "mode": "transcribe",
                              "with_timestamps": "true"},
                        timeout=90,
                    )
                response.raise_for_status()
                words = _read_word_times(response.json(), offset)
                if not words:
                    return None
                result.extend(words)
        print(f"[align] scene {scene.get('n', '?')}: {len(result)} words")
        return result or None
    except Exception as exc:
        print(f"[align] scene {scene.get('n', '?')}: skipped ({exc})")
        return None
