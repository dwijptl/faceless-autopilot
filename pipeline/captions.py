"""Stage 4a — captions synced to the voiceover.

We know each scene's exact narration text and exact audio duration, so caption
timing is allocated proportionally by character count within each scene. This
is deterministic, needs no extra models, and tracks the voice closely because
Kokoro reads at a steady rate.
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
