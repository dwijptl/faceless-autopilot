"""Synthesized sound-design pack — zero downloads, zero licensing.

Generates a broadcast-style library with numpy at runtime: multiple whooshes,
risers, impacts, ticks, pops, pulses, chimes, bell, shimmer and glitch accents.
Events are selected by scene role and CTA type so the same sound is not used
on every transition.
The Remotion SfxLayer plays them from the manifest's `sfx` event list.
"""
import hashlib
import os

import numpy as np
import soundfile as sf

SR = 44100
SOUND_CATALOG = (
    "whoosh_soft", "whoosh_fast", "whoosh_reverse", "riser", "hit",
    "sub_hit", "pop", "tick", "pulse", "chime", "bell", "sparkle",
    "glitch", "beep", "shutter", "page_turn", "rumble", "air",
    "swell", "thud", "ui_blip", "sonar",
)

GLASS_SFX = {
    "fact": "ui_blip",
    "metric": "ui_blip",
    "location": "sonar",
    "chapter": "thud",
    "reveal": "swell",
}


def _norm(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = float(np.max(np.abs(x))) or 1.0
    return (x * (peak / m)).astype(np.float32)


def _lowpass(x: np.ndarray, cutoff_hz: float) -> np.ndarray:
    """Cheap FFT brick-wall lowpass — fine for SFX."""
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    spec[freqs > cutoff_hz] = 0
    return np.fft.irfft(spec, len(x))


def _whoosh(dur: float = 0.7, seed: int = 7,
            bright: float = 2600) -> np.ndarray:
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = np.random.default_rng(seed).standard_normal(n)
    # sweep the lowpass down as the whoosh passes (bright -> dark)
    a = _lowpass(noise, bright) * np.sin(np.pi * t) ** 2
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


def _pop(dur: float = 0.28) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * 520 * t) * np.exp(-t * 24)
            + 0.45 * np.sin(2 * np.pi * 260 * t) * np.exp(-t * 17))
    snap = _lowpass(np.random.default_rng(29).standard_normal(n), 5000)
    snap *= np.exp(-t * 60) * 0.28
    return _norm(tone + snap, 0.68)


def _tick(dur: float = 0.12) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    click = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 75)
    return _norm(click, 0.48)


def _pulse(dur: float = 0.55) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    phase = 2 * np.pi * np.cumsum(92 - 30 * (t / dur)) / SR
    return _norm(np.sin(phase) * np.exp(-t * 8), 0.66)


def _chime(dur: float = 1.25) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = sum(amp * np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)
              for freq, amp, decay in ((660, 1.0, 3.8), (990, 0.55, 4.4),
                                       (1320, 0.28, 5.2)))
    return _norm(out, 0.62)


def _bell(dur: float = 1.15) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    wobble = 1 + 0.004 * np.sin(2 * np.pi * 6 * t)
    out = (np.sin(2 * np.pi * 760 * wobble * t) * np.exp(-t * 3.4)
           + 0.42 * np.sin(2 * np.pi * 1520 * t) * np.exp(-t * 5.0)
           + 0.18 * np.sin(2 * np.pi * 2280 * t) * np.exp(-t * 7.0))
    return _norm(out, 0.64)


def _sparkle(dur: float = 1.0) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for delay, freq, amp in ((0.0, 1250, 0.7), (0.13, 1680, 0.55),
                             (0.28, 2100, 0.42), (0.46, 2600, 0.30)):
        shifted = np.maximum(t - delay, 0)
        out += amp * np.sin(2 * np.pi * freq * shifted) * np.exp(-shifted * 12) * (t >= delay)
    return _norm(out, 0.50)


def _glitch(dur: float = 0.42) -> np.ndarray:
    n = int(dur * SR)
    rng = np.random.default_rng(41)
    noise = _lowpass(rng.standard_normal(n), 3800)
    gate = np.zeros(n)
    for start, width in ((0.00, 0.045), (0.09, 0.028), (0.17, 0.065), (0.31, 0.035)):
        gate[int(start * SR):int((start + width) * SR)] = 1
    tone = np.sign(np.sin(2 * np.pi * 105 * np.arange(n) / SR))
    return _norm((noise * 0.5 + tone * 0.25) * gate, 0.52)


def _beep(dur: float = 0.34) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    first = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 18)
    shifted = np.maximum(t - 0.14, 0)
    second = np.sin(2 * np.pi * 1175 * shifted) * np.exp(-shifted * 20) * (t >= 0.14)
    return _norm(first + second * 0.8, 0.48)


def _shutter(dur: float = 0.30) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(53)
    snap1 = _lowpass(rng.standard_normal(n), 6500) * np.exp(-t * 95)
    shifted = np.maximum(t - 0.105, 0)
    snap2 = _lowpass(rng.standard_normal(n), 3600) * np.exp(-shifted * 80) * (t >= .105)
    mechanical = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 32)
    return _norm(snap1 + snap2 * .85 + mechanical * .35, 0.58)


def _page_turn(dur: float = 0.68) -> np.ndarray:
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = np.random.default_rng(61).standard_normal(n)
    paper = (_lowpass(noise, 5200) - _lowpass(noise, 900))
    env = np.sin(np.pi * t) ** 2 * (1 - .35 * t)
    return _norm(paper * env, 0.46)


def _rumble(dur: float = 1.8) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = _lowpass(np.random.default_rng(71).standard_normal(n), 150)
    tone = np.sin(2 * np.pi * 43 * t) * .5 + np.sin(2 * np.pi * 61 * t) * .25
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** .65
    return _norm((noise * .8 + tone) * env, 0.55)


def _air(dur: float = 1.55) -> np.ndarray:
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = _lowpass(np.random.default_rng(79).standard_normal(n), 1800)
    env = np.sin(np.pi * t) ** 1.4
    return _norm(noise * env, 0.38)


def _swell(dur: float = 1.65) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    phase = 2 * np.pi * np.cumsum(72 + 105 * (t / dur) ** 1.7) / SR
    tone = (np.sin(phase) + .32 * np.sin(phase * 2.01))
    air = _lowpass(np.random.default_rng(89).standard_normal(n), 3200)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.35
    return _norm((tone * .42 + air * .34) * env, .62)


def _thud(dur: float = .85) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    phase = 2 * np.pi * np.cumsum(96 * np.exp(-t * 5.8) + 43) / SR
    body = np.sin(phase) * np.exp(-t * 7.0)
    knock = _lowpass(np.random.default_rng(97).standard_normal(n), 420)
    knock *= np.exp(-t * 28)
    return _norm(body + knock * .55, .72)


def _ui_blip(dur: float = .32) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * 720 * t) * np.exp(-t * 22)
            + .42 * np.sin(2 * np.pi * 1080 * t) * np.exp(-t * 29))
    return _norm(tone, .45)


def _sonar(dur: float = 1.3) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    ping = np.sin(2 * np.pi * 980 * t) * np.exp(-t * 5.4)
    halo = np.sin(2 * np.pi * 490 * t) * np.exp(-t * 3.2) * .26
    return _norm(ping + halo, .56)


def build_pack(workdir: str) -> dict:
    """Synthesize the pack into workdir. Returns {name: filename}."""
    soft = _whoosh(0.76, 7, 2100)
    fast = _whoosh(0.42, 13, 4200)
    pack = {
        "whoosh_soft": soft,
        "whoosh_fast": fast,
        "whoosh_reverse": _norm(fast[::-1], 0.62),
        "riser": _riser(),
        "hit": _hit(),
        "sub_hit": _norm(_hit(1.65) * 0.82, 0.76),
        "pop": _pop(),
        "tick": _tick(),
        "pulse": _pulse(),
        "chime": _chime(),
        "bell": _bell(),
        "sparkle": _sparkle(),
        "glitch": _glitch(),
        "beep": _beep(),
        "shutter": _shutter(),
        "page_turn": _page_turn(),
        "rumble": _rumble(),
        "air": _air(),
        "swell": _swell(),
        "thud": _thud(),
        "ui_blip": _ui_blip(),
        "sonar": _sonar(),
    }
    out = {}
    for name, audio in pack.items():
        fn = f"sfx_{name}.wav"
        sf.write(os.path.join(workdir, fn), audio, SR)
        out[name] = fn
    return out


def build_ambient_bed(workdir: str, seed: str, style: str = "documentary",
                      is_short: bool = False) -> str:
    """Create a deterministic, loop-safe cinematic bed with no licensing cost.

    The waveform is periodic by construction, so Remotion can loop it without
    a click. It stays intentionally quiet; final loudness is handled by the
    delivery mastering pass after the video render.
    """
    duration = 12.0 if is_short else 24.0
    n = int(duration * SR)
    digest = hashlib.sha256(f"{seed}:{style}:{is_short}".encode()).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
    t = np.arange(n, dtype=np.float32) / SR
    profiles = {
        "noir": (42.0, 56.0, 84.0, 126.0),
        "kinetic": (48.0, 64.0, 96.0, 144.0),
        "editorial": (55.0, 73.0, 110.0, 165.0),
        "documentary": (46.0, 61.0, 92.0, 138.0),
    }
    targets = profiles.get(style, profiles["documentary"])

    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)
    for index, target in enumerate(targets):
        # Quantize to whole cycles so the first and last sample join cleanly.
        freq = round(target * duration) / duration
        phase = rng.uniform(0, 2 * np.pi)
        amp = (0.30, 0.23, 0.13, 0.08)[index]
        left += (amp * np.sin(2 * np.pi * freq * t + phase)).astype(np.float32)
        right += (amp * np.sin(2 * np.pi * freq * t + phase + 0.10 * (index + 1))).astype(np.float32)

    # Periodic filtered texture adds air without sounding like a plain chord.
    bins = np.fft.rfftfreq(n, 1 / SR)
    spectrum = np.zeros(len(bins), dtype=np.complex64)
    mask = (bins >= 120) & (bins <= (1100 if style != "noir" else 650))
    phases = rng.uniform(0, 2 * np.pi, int(mask.sum()))
    shaped = 1.0 / np.maximum(bins[mask], 1.0) ** 0.72
    spectrum[mask] = shaped * np.exp(1j * phases)
    texture = np.fft.irfft(spectrum, n).astype(np.float32)
    texture = _norm(texture, 0.22)
    left += texture * 0.22
    right += np.roll(texture, int(0.019 * SR)) * 0.20

    stereo = np.stack([left, right], axis=1)
    stereo = _norm(stereo, 0.32)
    filename = "ambient_auto.wav"
    sf.write(os.path.join(workdir, filename), stereo, SR, subtype="PCM_16")
    print(f"[music] generated {duration:.0f}s loop-safe {style} ambience")
    return filename


def plan_events(scenes: list[dict], cfg: dict, workdir: str,
                cta: dict | None = None) -> list[dict]:
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
    style_pack = str(cfg.get("render", {}).get("style_pack", "documentary"))
    transitions = (("page_turn", "whoosh_soft", "page_turn")
                   if style_pack == "editorial" else
                   (("air", "whoosh_reverse", "whoosh_soft")
                    if style_pack == "noir" else
                    ("whoosh_soft", "whoosh_fast", "whoosh_reverse")))
    for i, sc in enumerate(scenes):
        start = float(sc.get("start", 0.0))
        mode = sc.get("visual_mode", "broll")
        if i == 0:
            events.append({"path": pack["rumble"], "start": start,
                           "volume": round(base * 0.22, 3)})
        if i > 0:  # transition whoosh into every scene
            events.append({"path": pack[transitions[(i - 1) % len(transitions)]],
                           "start": max(start - 0.18, 0.0),
                           "volume": round(base * 0.85, 3)})
        if mode in ("kinetic", "stat"):
            events.append({"path": pack["riser"],
                           "start": max(start - 1.35, 0.0),
                           "volume": round(base * 0.8, 3)})
            events.append({"path": pack["hit" if mode == "kinetic" else "sub_hit"],
                           "start": start + 0.04,
                           "volume": round(base, 3)})
        if mode == "stat":
            for delay in (0.22, 0.50, 0.82):
                events.append({"path": pack["tick"], "start": start + delay,
                               "volume": round(base * 0.40, 3)})
            events.append({"path": pack["beep"], "start": start + 1.02,
                           "volume": round(base * 0.28, 3)})
        elif mode == "kinetic" and style_pack == "kinetic":
            events.append({"path": pack["glitch"], "start": start + 0.12,
                           "volume": round(base * 0.32, 3)})
        elif mode == "card":
            events.append({"path": pack["pop"], "start": start + 0.06,
                           "volume": round(base * 0.38, 3)})
            events.append({"path": pack["chime"], "start": start + 0.36,
                           "volume": round(base * 0.24, 3)})
        elif mode == "map":
            events.append({"path": pack["pulse"], "start": start + 0.16,
                           "volume": round(base * 0.58, 3)})
            events.append({"path": pack["chime"], "start": start + 0.60,
                           "volume": round(base * 0.36, 3)})
        elif mode == "glass":
            variant = str((sc.get("motion") or {}).get("glassVariant", "fact"))
            cue = GLASS_SFX.get(variant, "ui_blip")
            if variant == "reveal":
                events.append({"path": pack["swell"],
                               "start": max(start - 1.15, 0.0),
                               "volume": round(base * .62, 3)})
                events.append({"path": pack["thud"], "start": start + .08,
                               "volume": round(base * .74, 3)})
            else:
                events.append({"path": pack[cue], "start": start + .10,
                               "volume": round(base * .48, 3)})
        elif mode == "ai_image":
            events.append({"path": pack["shutter"], "start": start + 0.02,
                           "volume": round(base * 0.22, 3)})
            events.append({"path": pack["sparkle"], "start": start + 0.12,
                           "volume": round(base * 0.34, 3)})

    if cta:
        cta_start = float(cta.get("start", 0.0))
        events.extend([
            {"path": pack["pop"], "start": cta_start,
             "volume": round(base * 0.54, 3)},
            {"path": pack["bell"], "start": cta_start + 0.56,
             "volume": round(base * 0.48, 3)},
            {"path": pack["sparkle"], "start": cta_start + 0.88,
             "volume": round(base * 0.28, 3)},
        ])
    print(f"[sfx] planned {len(events)} sound-design events")
    return events
