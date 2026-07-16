"""Narration-pace self-calibration.

Every run measures ground truth (spoken words vs synthesized seconds) and the
next run's word budget uses the measured pace instead of the static
channel.wpm guess. This closes the runtime gap permanently in both directions
(FAILURES.md #6: 6:00 target -> 4:38 delivered; shorts once overran 36%).

Data lives in calibration.json at the repo root and is committed by the
workflow alongside topics_done.txt, so calibration survives across CI runs.
Fail-open: any problem returns None and the configured wpm applies.
"""
import json
import os
import statistics

FILENAME = "calibration.json"
MAX_ENTRIES = 60          # keep the file tiny and diff-friendly
WINDOW = 5                # rolling window per kind
CLAMP = 0.25              # never drift more than ±25% from configured wpm


def _path(repo_root: str) -> str:
    return os.path.join(repo_root, FILENAME)


def _load(repo_root: str) -> list:
    try:
        with open(_path(repo_root), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def record(repo_root: str, kind: str, words: int, seconds: float,
           stamp: str = "") -> float | None:
    """Append one measured run. Returns the realized wpm (or None)."""
    try:
        words = int(words)
        seconds = float(seconds)
        if words <= 0 or seconds <= 10:
            return None
        wpm = round(words / (seconds / 60.0), 1)
        entries = _load(repo_root)
        entries.append({"stamp": stamp, "kind": str(kind),
                        "words": words, "seconds": round(seconds, 1),
                        "wpm": wpm})
        with open(_path(repo_root), "w", encoding="utf-8") as f:
            json.dump(entries[-MAX_ENTRIES:], f, indent=2, ensure_ascii=False)
        print(f"[calib] recorded {kind} run: {words} words / "
              f"{seconds / 60:.1f} min = {wpm} wpm")
        return wpm
    except Exception as exc:  # never block a render over telemetry
        print(f"[calib] record skipped ({exc})")
        return None


def measured_wpm(repo_root: str, configured_wpm: int,
                 kind: str = "long") -> int | None:
    """Median realized wpm over the last WINDOW runs of this kind, clamped to
    ±CLAMP of the configured value. None until 2+ measurements exist."""
    try:
        runs = [e["wpm"] for e in _load(repo_root)
                if e.get("kind") == kind and isinstance(e.get("wpm"), (int, float))]
        if len(runs) < 2:
            return None
        median = statistics.median(runs[-WINDOW:])
        lo = configured_wpm * (1 - CLAMP)
        hi = configured_wpm * (1 + CLAMP)
        return int(round(min(max(median, lo), hi)))
    except Exception:
        return None
