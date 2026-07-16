"""Self-learning loop — digests YouTube Studio CSV exports into learnings.md.

Usage: drop CSV exports from YouTube Studio (Analytics -> Advanced mode ->
Export) into the analytics/ folder. The weekly "Update Learnings" workflow
(or a manual run) sends them to Gemini, which rewrites learnings.md.

Beat-level retention join: every render commits its beat map to
analytics/beats/<stamp>.json. Export a video's audience-retention curve
(Studio -> the video -> Analytics -> Engagement -> "Audience retention" ->
Advanced mode -> Export current view -> CSV) and save it as
analytics/retention/<stamp>.csv. This module joins the curve against the
beat map deterministically — per-scene retention drop by narrative role,
visual mode and delivery — and feeds the result into the digest.

learnings.md is read by script_gen before every video, and may contain a
machine-readable overrides block that run.py applies within safe bounds:

    ```yaml
    overrides:
      target_minutes: 7
    ```
"""
import csv
import glob
import io
import json
import os
import re
import sys
import time

import requests
import yaml

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_CSV_CHARS = 60_000
MIN_VIDEOS_PER_PATTERN = 5   # never infer a cross-video pattern from less


def parse_retention_csv(path: str) -> list[tuple[float, float]]:
    """Parse a YouTube audience-retention export into [(position, retention)]
    with both values normalized to 0..1. Column names vary by locale, so we
    take the first two numeric columns: position, then retention. Returns []
    on anything unparseable (fail-open)."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        points = []
        for row in csv.reader(io.StringIO(text)):
            nums = []
            for cell in row:
                cell = str(cell).strip().replace("%", "")
                try:
                    nums.append(float(cell))
                except ValueError:
                    continue
            if len(nums) >= 2:
                points.append((nums[0], nums[1]))
        if len(points) < 3:
            return []
        max_pos = max(p for p, _ in points) or 1.0
        max_ret = max(r for _, r in points)
        scale_p = 100.0 if max_pos > 1.5 else 1.0
        scale_r = 100.0 if max_ret > 1.5 else 1.0
        curve = sorted((p / scale_p, r / scale_r) for p, r in points)
        return [(min(max(p, 0.0), 1.0), max(r, 0.0)) for p, r in curve]
    except Exception:
        return []


def _retention_at(curve: list[tuple[float, float]], position: float) -> float:
    """Linear interpolation of the retention curve at position 0..1."""
    if not curve:
        return 0.0
    if position <= curve[0][0]:
        return curve[0][1]
    for (p1, r1), (p2, r2) in zip(curve, curve[1:]):
        if p1 <= position <= p2:
            if p2 == p1:
                return r2
            t = (position - p1) / (p2 - p1)
            return r1 + t * (r2 - r1)
    return curve[-1][1]


def join_retention(beats_doc: dict, curve: list[tuple[float, float]]) -> list[dict]:
    """Per-scene retention delta: what fraction of the audience left while
    this scene (narrative role / visual mode) was on screen, per second."""
    beats = beats_doc.get("beats") or []
    if not beats or not curve:
        return []
    total = max(float(beats[-1].get("end", 0)), 1.0)
    joined = []
    for b in beats:
        start, end = float(b.get("start", 0)), float(b.get("end", 0))
        seconds = max(end - start, 0.1)
        r_in = _retention_at(curve, start / total)
        r_out = _retention_at(curve, end / total)
        joined.append({
            "n": b.get("n"), "title": b.get("title", ""),
            "start": start, "end": end,
            "narrativeRole": b.get("narrativeRole", ""),
            "visualMode": b.get("visualMode", ""),
            "delivery": b.get("delivery", ""),
            "rewardType": b.get("rewardType", ""),
            "retentionIn": round(r_in, 4),
            "retentionOut": round(r_out, 4),
            "dropPerMinute": round((r_in - r_out) / seconds * 60, 4),
        })
    return joined


def collect_retention_joins() -> dict:
    """Pair analytics/retention/<stamp>.csv files with analytics/beats/
    <stamp>.json beat maps. Returns {"videos": [...], "aggregates": {...}}."""
    videos = []
    beats_dir = os.path.join(REPO_ROOT, "analytics", "beats")
    for csv_path in sorted(glob.glob(
            os.path.join(REPO_ROOT, "analytics", "retention", "*.csv"))):
        stamp = os.path.splitext(os.path.basename(csv_path))[0]
        beats_path = os.path.join(beats_dir, f"{stamp}.json")
        if not os.path.exists(beats_path):
            print(f"[learn] retention CSV {stamp} has no beat map — "
                  f"expected {os.path.relpath(beats_path, REPO_ROOT)}")
            continue
        try:
            with open(beats_path, encoding="utf-8") as f:
                beats_doc = json.load(f)
        except Exception:
            continue
        joined = join_retention(beats_doc, parse_retention_csv(csv_path))
        if not joined:
            continue
        worst = max(joined, key=lambda b: b["dropPerMinute"])
        videos.append({"stamp": stamp,
                       "title": beats_doc.get("title", ""),
                       "style": beats_doc.get("style", ""),
                       "scenes": joined,
                       "worst_scene": worst})

    # cross-video aggregates, guarded against tiny samples
    aggregates = {}
    for key in ("narrativeRole", "visualMode", "delivery"):
        buckets: dict = {}
        for v in videos:
            seen_in_video = set()
            for b in v["scenes"]:
                label = b.get(key) or "(unset)"
                slot = buckets.setdefault(label, {"drops": [], "videos": set()})
                slot["drops"].append(b["dropPerMinute"])
                seen_in_video.add(label)
            for label in seen_in_video:
                buckets[label]["videos"].add(v["stamp"])
        aggregates[key] = {
            label: {"meanDropPerMinute": round(sum(s["drops"]) / len(s["drops"]), 4),
                    "scenes": len(s["drops"]), "videos": len(s["videos"])}
            for label, s in sorted(buckets.items())
            if len(s["videos"]) >= MIN_VIDEOS_PER_PATTERN}
    return {"videos": videos, "aggregates": aggregates,
            "min_videos_per_pattern": MIN_VIDEOS_PER_PATTERN}


def retention_brief(joins: dict) -> str:
    """Compact, deterministic summary for the digest prompt."""
    videos = joins.get("videos") or []
    if not videos:
        return ""
    lines = [f"BEAT-LEVEL RETENTION JOIN ({len(videos)} video(s), deterministic "
             "— trust these numbers over impressions):"]
    for v in videos[-8:]:
        w = v["worst_scene"]
        lines.append(
            f"- {v['stamp']} '{v['title'][:40]}': worst scene {w['n']} "
            f"('{w['title'][:30]}', role={w['narrativeRole'] or '?'}, "
            f"mode={w['visualMode']}) lost {w['dropPerMinute']:.1%}/min; "
            f"video retention {v['scenes'][0]['retentionIn']:.0%} -> "
            f"{v['scenes'][-1]['retentionOut']:.0%}")
    for key, buckets in (joins.get("aggregates") or {}).items():
        if buckets:
            ranked = sorted(buckets.items(),
                            key=lambda kv: kv[1]["meanDropPerMinute"])
            lines.append(f"- by {key} (>= {joins['min_videos_per_pattern']} "
                         "videos): best "
                         + ", ".join(f"{k}={v['meanDropPerMinute']:.1%}/min"
                                     for k, v in ranked[:3])
                         + " | worst "
                         + ", ".join(f"{k}={v['meanDropPerMinute']:.1%}/min"
                                     for k, v in ranked[-2:]))
    return "\n".join(lines)


def _gemini_text(prompt: str, cfg: dict, api_key: str) -> str:
    models = [cfg["llm"]["model"]] + list(cfg["llm"].get("fallback_models", []))
    for model in models:
        url = f"{API_BASE}/{model}:generateContent?key={api_key}"
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4}}
        for attempt in range(3):
            r = requests.post(url, json=body, timeout=120)
            if r.status_code == 429:
                time.sleep(20 * (attempt + 1))
                continue
            if r.status_code in (400, 404):
                break
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    raise RuntimeError("Gemini call failed for analytics digest")


def collect_csvs() -> str:
    chunks, total = [], 0
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "analytics", "**", "*.csv"),
                                 recursive=True)):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception:
            continue
        take = text[: max(0, MAX_CSV_CHARS - total)]
        if not take:
            break
        chunks.append(f"--- FILE: {os.path.relpath(path, REPO_ROOT)} ---\n{take}")
        total += len(take)
    return "\n\n".join(chunks)


def parse_overrides(learnings_text: str) -> dict:
    """Extract and bound the machine-overrides block from learnings.md."""
    m = re.search(r"```yaml\s*(.*?)```", learnings_text, re.DOTALL)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1)) or {}
        o = data.get("overrides", {}) or {}
    except Exception:
        return {}
    safe = {}
    if isinstance(o.get("target_minutes"), (int, float)):
        safe["target_minutes"] = min(max(float(o["target_minutes"]), 4), 12)
    if isinstance(o.get("tts_speed"), (int, float)):
        safe["tts_speed"] = min(max(float(o["tts_speed"]), 0.85), 1.15)
    if isinstance(o.get("scenes_max"), int):
        safe["scenes_max"] = min(max(o["scenes_max"], 6), 14)
    return safe


def main() -> None:
    with open(os.path.join(REPO_ROOT, "config.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        sys.exit("Missing GEMINI_API_KEY")

    csvs = collect_csvs()
    if not csvs:
        print("[learn] no CSVs in analytics/ — nothing to digest (drop Studio "
              "exports there; see analytics/README.md)")
        return

    # deterministic beat-level retention join (fail-open: empty when no
    # retention exports or beat maps exist yet)
    joins = collect_retention_joins()
    join_block = retention_brief(joins)
    if joins.get("videos"):
        summary_path = os.path.join(REPO_ROOT, "analytics",
                                    "retention_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(joins, f, indent=2, ensure_ascii=False, default=list)
        print(f"[learn] beat-level retention join: {len(joins['videos'])} "
              f"video(s) -> analytics/retention_summary.json")

    topics = ""
    try:
        with open(os.path.join(REPO_ROOT, "topics_done.txt"), encoding="utf-8") as f:
            topics = f.read()[-4000:]
    except Exception:
        pass
    prev = ""
    try:
        with open(os.path.join(REPO_ROOT, "learnings.md"), encoding="utf-8") as f:
            prev = f.read()[:5000]
    except Exception:
        pass

    prompt = f"""You are the growth analyst for a faceless YouTube channel.

NICHE: {cfg['channel']['niche']}

VIDEOS PRODUCED SO FAR (titles/topics):
{topics}

PREVIOUS LEARNINGS FILE (update it, don't discard still-valid insights):
{prev}

RAW YOUTUBE STUDIO ANALYTICS EXPORTS (CSV):
{csvs}

{join_block}

Rewrite the channel's learnings file. Requirements:
1. Start with "# Channel learnings (auto-updated)" and the current date.
2. Sections: "## What's working", "## What's failing", "## Topic guidance",
   "## Hook & pacing guidance", "## Thumbnail & title guidance".
   Be specific and evidence-based — cite the numbers (CTR, avg view duration,
   retention drop-off points, impressions, traffic sources) that justify each
   insight. If data is thin, say so and keep advice conservative.
3. End with a machine block, exactly this format, choosing values the data
   supports (omit keys you have no evidence for):
```yaml
overrides:
  target_minutes: <4-12>
  scenes_max: <6-14>
```
Output ONLY the markdown file content."""

    result = _gemini_text(prompt, cfg, api_key)
    result = re.sub(r"^```(markdown|md)?\s*|```\s*$", "", result.strip())
    with open(os.path.join(REPO_ROOT, "learnings.md"), "w", encoding="utf-8") as f:
        f.write(result + "\n")
    print("[learn] learnings.md updated "
          f"({len(result)} chars, overrides={json.dumps(parse_overrides(result))})")


if __name__ == "__main__":
    main()
