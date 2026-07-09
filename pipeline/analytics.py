"""Self-learning loop — digests YouTube Studio CSV exports into learnings.md.

Usage: drop CSV exports from YouTube Studio (Analytics -> Advanced mode ->
Export) into the analytics/ folder. The weekly "Update Learnings" workflow
(or a manual run) sends them to Gemini, which rewrites learnings.md.

learnings.md is read by script_gen before every video, and may contain a
machine-readable overrides block that run.py applies within safe bounds:

    ```yaml
    overrides:
      target_minutes: 7
    ```
"""
import glob
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
