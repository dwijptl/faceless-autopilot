"""Stage 1 — topic selection + scene-segmented script via Gemini API (free tier)."""
import json
import os
import re
import time

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _gemini(prompt: str, cfg: dict, api_key: str) -> str:
    """Call Gemini, walking the fallback model list on 404/400 model errors."""
    models = [cfg["llm"]["model"]] + list(cfg["llm"].get("fallback_models", []))
    last_err = None
    for model in models:
        url = f"{API_BASE}/{model}:generateContent?key={api_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": cfg["llm"].get("temperature", 0.9),
            },
        }
        for attempt in range(3):
            try:
                r = requests.post(url, json=body, timeout=120)
                if r.status_code == 404 or (r.status_code == 400 and "model" in r.text.lower()):
                    print(f"[script] model {model} unavailable, trying next")
                    last_err = r.text
                    break  # next model
                if r.status_code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"[script] rate limited, sleeping {wait}s")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except requests.RequestException as e:
                last_err = str(e)
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Gemini call failed on all models. Last error: {last_err}")


def _parse_json(text: str) -> dict:
    """Parse model output as JSON, tolerating stray code fences."""
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def pick_topic(cfg: dict, api_key: str, done_file: str = "topics_done.txt") -> str:
    forced = os.environ.get("FORCED_TOPIC", "").strip()
    if forced:
        print(f"[script] using forced topic: {forced}")
        return forced

    done = []
    if os.path.exists(done_file):
        with open(done_file, encoding="utf-8") as f:
            done = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    prompt = f"""You are the content strategist for a faceless YouTube channel.

NICHE: {cfg['channel']['niche']}
AUDIENCE: {cfg['channel']['audience']}

Already-covered topics (NEVER repeat or closely paraphrase these):
{json.dumps(done[-100:], indent=0)}

Invent ONE new video topic with strong curiosity-gap appeal that can be
illustrated almost entirely with stock footage of landscapes, cities,
nature, aerials and oceans (no specific people, no events needing news
footage, nothing requiring licensed material).

Return JSON exactly: {{"topic": "<the topic as a working title>"}}"""
    result = _parse_json(_gemini(prompt, cfg, api_key))
    topic = result["topic"].strip()
    print(f"[script] auto-picked topic: {topic}")
    return topic


def generate_script(cfg: dict, topic: str, api_key: str) -> dict:
    v = cfg["video"]
    words = int(cfg["video"]["target_minutes"] * 150)
    prompt = f"""You are a scriptwriter for a faceless YouTube channel
(voiceover + stock b-roll + captions, no on-camera host).

TOPIC: {topic}
TARGET: ~{words} spoken words total (about {v['target_minutes']} minutes at 150 wpm)
TONE: {cfg['channel']['tone']}
AUDIENCE: {cfg['channel']['audience']}

Write a scene-segmented script and return ONLY valid JSON with this exact shape:
{{
  "title": "click-worthy but honest YouTube title, <= 70 chars",
  "thumb_text": "3-5 punchy words for the thumbnail",
  "description": "2-3 sentence YouTube description ending with 3 relevant hashtags",
  "tags": ["8-12 YouTube tags"],
  "scenes": [
    {{
      "n": 1,
      "title": "3-6 word scene title",
      "narration": "60-150 words of spoken narration",
      "search_terms": ["stock video search term", "alternative term", "broader fallback term"]
    }}
  ]
}}

Rules:
- {v['scenes_min']} to {v['scenes_max']} scenes. Scene 1 is a 30-second HOOK that opens a
  curiosity gap immediately. A re-hook (tease what's coming) around the middle scene.
  Final scene is a 20-second payoff/outro with a next-video tease. No "like and subscribe".
- Narration is written for the EAR: short sentences, no lists, no headers read aloud,
  no "in this video", makes sense with eyes closed.
- search_terms must describe VISUALS that exist in stock libraries (e.g. "aerial desert
  highway", not "the concept of isolation"). Concrete nouns. 1-3 words each.
- Every scene advances exactly one idea. No filler.
- Facts must be well-established and verifiable; when uncertain, phrase carefully
  ("researchers estimate", "roughly") rather than inventing precise numbers."""

    for attempt in range(3):
        try:
            script = _parse_json(_gemini(prompt, cfg, api_key))
            assert isinstance(script["scenes"], list) and len(script["scenes"]) >= 4
            for s in script["scenes"]:
                assert s["narration"].strip() and s["search_terms"]
            assert script["title"].strip()
            script.setdefault("thumb_text", script["title"][:30])
            script["topic"] = topic
            print(f"[script] generated: '{script['title']}' with {len(script['scenes'])} scenes")
            return script
        except (KeyError, AssertionError, json.JSONDecodeError) as e:
            print(f"[script] invalid script JSON (attempt {attempt + 1}): {e}")
    raise RuntimeError("Could not obtain a valid script after 3 attempts")


def log_topic_done(topic: str, done_file: str = "topics_done.txt") -> None:
    with open(done_file, "a", encoding="utf-8") as f:
        f.write(topic + "\n")
