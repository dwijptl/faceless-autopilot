"""Stage 4a — captions aligned to the narration when word timings exist.

Sarvam STT word timings are preferred. The character-rate estimate remains a
safe fallback when alignment is unavailable or does not match the script.
"""


def _chunks(text: str, max_chars: int) -> list[str]:
    words, out, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def _aligned_events(sc: dict, chunks: list[str]) -> list[tuple] | None:
    """Make caption-line timings from scene-relative ``word_times``.

    A transcript can normalize Hindi numbers or punctuation, so accept timing
    only when its token count is close to the intended narration. Captions keep
    the authored text while borrowing the actual spoken timing.
    """
    timings = sc.get("word_times") or []
    wanted = sc.get("narration", "").split()
    if not timings or not wanted:
        return None
    if not 0.80 <= len(timings) / len(wanted) <= 1.20:
        return None

    out, idx = [], 0
    for chunk in chunks:
        count = len(chunk.split())
        if count <= 0 or idx + count > len(timings):
            return None
        first, last = timings[idx], timings[idx + count - 1]
        try:
            start = sc["start"] + max(float(first[1]), 0.0)
            end = sc["start"] + max(float(last[2]), float(first[1]) + 0.05)
        except (IndexError, TypeError, ValueError):
            return None
        out.append((start, min(end, sc["start"] + sc["audio_duration"]), chunk))
        idx += count
    return out if idx <= len(timings) else None


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_captions(scenes: list[dict], max_chars: int) -> tuple[list[tuple], str]:
    """scenes: [{narration, audio_duration, start}] (start = absolute offset).

    Returns (events, srt_text) where events = [(start, end, text), ...].
    """
    events = []
    for sc in scenes:
        chunks = _chunks(sc["narration"], max_chars)
        if not chunks:
            continue
        aligned = _aligned_events(sc, chunks)
        if aligned is not None:
            events.extend(aligned)
            continue
        total_chars = sum(len(c) for c in chunks)
        speakable = max(sc["audio_duration"] - 0.35, 0.5)  # minus trailing pause
        t = sc["start"]
        for c in chunks:
            d = speakable * (len(c) / total_chars)
            events.append((t, min(t + d, sc["start"] + sc["audio_duration"]), c))
            t += d

    lines = []
    for i, (start, end, text) in enumerate(events, 1):
        lines += [str(i), f"{_ts(start)} --> {_ts(end)}", text, ""]
    return events, "\n".join(lines)
