"""Stage 3 — voiceover.

PRIMARY: Sarvam AI bulbul:v3 (api.sarvam.ai) — the channel's CLONED Hindi
voice. The speaker comes from the SARVAM_SPEAKER secret (your cloned voice ID
from dashboard.sarvam.ai; any preset name like "amit" also works).

FALLBACK: Kokoro-82M (Apache 2.0, runs free on the runner) with its Hindi
voices — a Sarvam outage or empty credits never kills a scheduled run.
Set TTS_NO_FALLBACK=1 to fail hard instead (the Test Voice workflow does).
"""
import base64
import io
import os
import re
import time

import numpy as np
import requests
import soundfile as sf

SARVAM_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_CHAR_LIMIT = 1800   # API allows 2500 for bulbul:v3 — stay comfortably under
MODEL_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
MODEL_FILES = ["kokoro-v1.0.onnx", "voices-v1.0.bin"]
SAMPLE_RATE = 24000

ENGINE_USED = "none"       # run.py reports this in the release notes
_engines: set = set()
_sarvam_chars = 0          # cost telemetry (₹ estimate in usage_summary)
_kokoro = None
FALLBACK_USED = False       # never silently present a fallback run as cloned voice

# Per-scene voice direction: how a human narrator would deliver it.
# pace_mul multiplies cfg tts.speed; pre = seconds of silence BEFORE the
# scene (dramatic beat); temperature = bulbul:v3 expressiveness.
DELIVERY = {
    "hook":   {"pace_mul": 1.06, "temperature": 0.72, "pre": 0.0},
    "calm":   {"pace_mul": 1.00, "temperature": 0.55, "pre": 0.0},
    "reveal": {"pace_mul": 0.88, "temperature": 0.62, "pre": 0.5},
    "urgent": {"pace_mul": 1.12, "temperature": 0.75, "pre": 0.0},
}


# ── sentence-aware chunking (Hindi danda । + Latin punctuation) ──────────
def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[।.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _chunks(text: str, limit: int = SARVAM_CHAR_LIMIT) -> list[str]:
    """Greedy multi-sentence chunks under `limit` chars (better prosody than
    per-sentence requests, fewer API calls)."""
    out, cur = [], ""
    for sent in _sentences(text):
        while len(sent) > limit:  # pathological unbroken sentence
            out.append(sent[:limit].strip())
            sent = sent[limit:]
        if cur and len(cur) + 1 + len(sent) > limit:
            out.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        out.append(cur)
    return out


# ── Sarvam bulbul:v3 ─────────────────────────────────────────────────────
def _sarvam_request(chunk: str, cfg: dict, api_key: str, speaker: str,
                    dlv: dict) -> np.ndarray:
    t = cfg["tts"]
    base = float(t.get("speed", 1.0)) * dlv.get("pace_mul", 1.0)
    pace = min(max(base, 0.5), 2.0)  # bulbul:v3 range
    body = {
        "text": chunk,
        "target_language_code": cfg["channel"].get("language", "hi-IN"),
        "model": t.get("sarvam_model", "bulbul:v3"),
        "speaker": speaker,
        "pace": round(pace, 3),
        "temperature": dlv.get("temperature", float(t.get("temperature", 0.6))),
        "speech_sample_rate": SAMPLE_RATE,
    }
    headers = {"api-subscription-key": api_key, "Content-Type": "application/json"}
    last = ""
    for attempt in range(4):
        try:
            r = requests.post(SARVAM_URL, json=body, headers=headers, timeout=180)
        except requests.RequestException as e:
            last = str(e)
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 200:
            b64 = r.json()["audios"][0]
            data, sr = sf.read(io.BytesIO(base64.b64decode(b64)), dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)
            if sr != SAMPLE_RATE:  # defensive — we request 24000
                idx = np.linspace(0, len(data) - 1,
                                  int(len(data) * SAMPLE_RATE / sr))
                data = data[idx.astype(int)]
            return np.asarray(data, dtype=np.float32)
        if r.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"[tts] sarvam rate-limited, sleeping {wait}s")
            last = r.text[:300]
            time.sleep(wait)
            continue
        if r.status_code == 403:
            raise RuntimeError(
                "Sarvam 403 — check the SARVAM_API_KEY secret and remaining "
                f"credits at dashboard.sarvam.ai. Body: {r.text[:300]}")
        if r.status_code == 422:
            raise RuntimeError(
                "Sarvam 422 — invalid request; usually SARVAM_SPEAKER doesn't "
                f"match bulbul:v3. Body: {r.text[:300]}")
        last = f"HTTP {r.status_code}: {r.text[:300]}"
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Sarvam TTS failed after retries — {last}")


def _synth_sarvam(text: str, cfg: dict, dlv: dict) -> np.ndarray:
    global _sarvam_chars
    api_key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY not set (add it as a repo secret)")
    speaker = (os.environ.get("SARVAM_SPEAKER", "").strip()
               or cfg["tts"].get("sarvam_speaker", "amit"))
    pieces = []
    for chunk in _chunks(text):
        pieces.append(_sarvam_request(chunk, cfg, api_key, speaker, dlv))
        _sarvam_chars += len(chunk)
        time.sleep(0.3)  # gentle on rate limits
    if not pieces:
        pieces = [np.zeros(SAMPLE_RATE, dtype=np.float32)]
    return np.concatenate(pieces)


# ── Kokoro-82M fallback (Hindi voices: hf_alpha/hf_beta/hm_omega/hm_psi) ─
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


def _kokoro_lang(cfg: dict) -> str:
    lang = str(cfg["channel"].get("language", "en-us")).lower()
    return "hi" if lang.startswith("hi") else lang


def _synth_kokoro(text: str, cfg: dict) -> np.ndarray:
    k = _engine()
    voice = cfg["tts"].get("voice", "hm_omega")
    try:
        available = set(k.get_voices())
        if voice not in available:
            hindi = sorted(v for v in available if v.startswith(("hf_", "hm_")))
            fallback = hindi[0] if hindi else sorted(available)[0]
            print(f"[tts] voice '{voice}' not found, using '{fallback}'")
            voice = fallback
    except Exception:
        pass

    speed = float(cfg["tts"].get("speed", 1.0))
    lang = _kokoro_lang(cfg)
    gap = np.zeros(int(0.25 * SAMPLE_RATE), dtype=np.float32)
    chunks = []
    for sent in _sentences(text):
        samples, sr = k.create(sent, voice=voice, speed=speed, lang=lang)
        chunks.append(np.asarray(samples, dtype=np.float32))
        chunks.append(gap)
    if not chunks:
        chunks = [np.zeros(SAMPLE_RATE, dtype=np.float32)]
    return np.concatenate(chunks)


# ── public API ───────────────────────────────────────────────────────────
def synth_scene(text: str, wav_path: str, cfg: dict,
                delivery: str = "calm", tail_seconds: float = 0.35) -> float:
    """Synthesize one scene's narration to wav_path. Returns duration (s).
    delivery: hook | calm | reveal | urgent (per-scene voice direction)."""
    global ENGINE_USED, FALLBACK_USED
    dlv = DELIVERY.get(str(delivery).lower().strip(), DELIVERY["calm"])
    engine = str(cfg.get("tts", {}).get("engine", "sarvam")).lower()
    audio = None
    if engine == "sarvam":
        try:
            audio = _synth_sarvam(text, cfg, dlv)
            _engines.add("sarvam:" + cfg["tts"].get("sarvam_model", "bulbul:v3"))
        except Exception as e:
            if os.environ.get("TTS_NO_FALLBACK", "").strip() == "1":
                raise
            FALLBACK_USED = True
            print(f"[tts] SARVAM FAILED -> Kokoro fallback. Reason: {e}")
    if audio is None:
        kcfg = dict(cfg)
        kcfg["tts"] = dict(cfg["tts"])
        kcfg["tts"]["speed"] = float(cfg["tts"].get("speed", 1.0)) * dlv["pace_mul"]
        audio = _synth_kokoro(text, kcfg)
        _engines.add("kokoro-82m")
    ENGINE_USED = " + ".join(sorted(_engines))

    # dramatic beat before reveals + configurable breath before the next scene
    pre = np.zeros(int(dlv.get("pre", 0.0) * SAMPLE_RATE), dtype=np.float32)
    tail = max(0.0, min(float(tail_seconds), 2.0))
    audio = np.concatenate(
        [pre, audio, np.zeros(int(tail * SAMPLE_RATE), dtype=np.float32)])
    peak = float(np.max(np.abs(audio))) or 1.0  # normalize to healthy loudness
    audio = audio * (0.89 / peak)
    sf.write(wav_path, audio, SAMPLE_RATE)
    return len(audio) / SAMPLE_RATE


def fallback_used() -> bool:
    """Whether this run used a non-primary voice after a Sarvam failure."""
    return FALLBACK_USED


def reset_run_state() -> None:
    """Reset module telemetry when a process intentionally runs more than once."""
    global ENGINE_USED, FALLBACK_USED, _sarvam_chars
    ENGINE_USED = "none"
    FALLBACK_USED = False
    _sarvam_chars = 0
    _engines.clear()


def usage_summary() -> str:
    if _sarvam_chars <= 0:
        return f"engines: {ENGINE_USED} · sarvam chars: 0 (₹0)"
    rupees = _sarvam_chars / 10_000 * 30  # ₹30 / 10k chars (check dashboard)
    return (f"engines: {ENGINE_USED} · sarvam chars: {_sarvam_chars:,} "
            f"(≈ ₹{rupees:.1f})")
