"""Synthesized sound-design pack — zero downloads, zero licensing.

Generates broadcast-style SFX (whoosh, riser, impact hit) with numpy at
runtime and computes where they belong: whoosh on every scene transition,
riser building INTO each kinetic/stat reveal, deep hit ON the reveal.
The Remotion SfxLayer plays them from the manifest's `sfx` event list.
"""
import os

import numpy as np
import soundfile as sf

SR = 44100


def _norm(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = float(np.max(np.abs(x))) or 1.0
    return (x * (peak / m)).astype(np.float32)


def _lowpass(x: np.ndarray, cutoff_hz: float) -> np.ndarray:
    """Cheap FFT brick-wall lowpass — fine for SFX."""
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    spec[freqs > cutoff_hz] = 0
    return np.fft.irfft(spec, len(x))


def _whoosh(dur: float = 0.7) -> np.ndarray:
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = np.random.default_rng(7).standard_normal(n)
    # sweep the lowpass down as the whoosh passes (bright -> dark)
    a = _lowpass(noise, 2600) * np.sin(np.pi * t) ** 2
    b = _lowpass(noise, 700) * np.sin(np.pi * np.clip(t * 1.3 - 0.15, 0, 1)) ** 2
    return _norm(a * 0.6 + b, 0.7)


def _riser(dur: float = 1.5) -> np.ndarray:
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = np.random.default_rng(11).standard_normal(n)
    shimmer = _lowpass(noise, 5000) - _lowpass(noise, 900)
    env = t ** 2.2  # exponential build
    tone = np.sin(2 * np.pi * (110 + 220 * t ** 2) * t * dur / dur * t)  # rising tone bed
    out = shimmer * env * 0.8 + tone * env * 0.25
    out[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))  # declick
    return _norm(out, 0.65)


def _hit(dur: float = 1.3) -> np.ndarray:
    n = int(dur * SR)
    t = np.linspace(0, dur, n)
    f = 82 * np.exp(-t * 3.2) + 42  # pitch drop
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t * 3.5)
    thump = _lowpass(np.random.default_rng(3).standard_normal(n), 300)
    thump *= np.exp(-t * 18)
    return _norm(body + thump * 0.7, 0.85)


def build_pack(workdir: str) -> dict:
    """Synthesize the pack into workdir. Returns {name: filename}."""
    pack = {"whoosh": _whoosh(), "riser": _riser(), "hit": _hit()}
    out = {}
    for name, audio in pack.items():
        fn = f"sfx_{name}.wav"
        sf.write(os.path.join(workdir, fn), audio, SR)
        out[name] = fn
    return out


def plan_events(scenes: list[dict], cfg: dict, workdir: str) -> list[dict]:
    """Compute [{path, start, volume}] for the manifest. scenes need
    .start (absolute s) and .visual_mode. Fail-open: [] on any problem."""
    scfg = cfg.get("sfx", {})
    if not scfg.get("enabled", True):
        return []
    try:
        pack = build_pack(workdir)
    except Exception as e:
        print(f"[sfx] synthesis failed ({e}) — continuing without SFX")
        return []
    base = float(scfg.get("volume", 0.5))
    events: list[dict] = []
    for i, sc in enumerate(scenes):
        start = float(sc.get("start", 0.0))
        mode = sc.get("visual_mode", "broll")
        if i > 0:  # transition whoosh into every scene
            events.append({"path": pack["whoosh"],
                           "start": max(start - 0.18, 0.0),
                           "volume": round(base * 0.85, 3)})
        if mode in ("kinetic", "stat"):  # build-up + impact on reveals
            events.append({"path": pack["riser"],
                           "start": max(start - 1.35, 0.0),
                           "volume": round(base * 0.8, 3)})
            events.append({"path": pack["hit"],
                           "start": start + 0.04,
                           "volume": round(base, 3)})
    print(f"[sfx] planned {len(events)} sound-design events")
    return events
