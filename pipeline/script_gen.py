"""Stage 1 — topic selection + scene-segmented script via Gemini API (free tier).

Reads learnings.md (written by the analytics loop) so topic choice, hook
style, pacing and thumbnail text adapt to what has performed on the channel.
"""
import json
import os
import re
import time

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _gemini(prompt: str, cfg: dict, api_key: str) -> str:
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
                    break
                if r.status_code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"[script] rate limited, sleeping {wait}s")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except requests.RequestException as e:
                last_err = str(e)
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Gemini call failed on all models. Last error: {last_err}")


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def load_learnings(repo_root: str) -> str:
    path = os.path.join(repo_root, "learnings.md")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
        return text[:6000]
    except Exception:
        return ""


def pick_topic(cfg: dict, api_key: str, done_file: str = "topics_done.txt",
               learnings: str = "") -> str:
    forced = os.environ.get("FORCED_TOPIC", "").strip()
    if forced:
        print(f"[script] using forced topic: {forced}")
        return forced

    done = []
    if os.path.exists(done_file):
        with open(done_file, encoding="utf-8") as f:
            done = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    learn_block = (f"\nWHAT HAS WORKED ON THIS CHANNEL (analytics digest):\n{learnings}\n"
                   if learnings else "")
    prompt = f"""You are the content strategist for a faceless YouTube channel.

NICHE: {cfg['channel']['niche']}
AUDIENCE: {cfg['channel']['audience']}
{learn_block}
Already-covered topics (NEVER repeat or closely paraphrase these):
{json.dumps(done[-100:], indent=0)}

Invent ONE new video topic with strong curiosity-gap appeal that can be
illustrated with stock footage of landscapes, cities, nature, aerials and
oceans plus occasional AI-generated stills (no specific people, no events
needing news footage, nothing requiring licensed material). If the analytics
digest above shows a topic family performing well, lean into that family
without repeating covered topics.

Return JSON exactly: {{"topic": "<the topic as a working title>"}}"""
    topic = _parse_json(_gemini(prompt, cfg, api_key))["topic"].strip()
    print(f"[script] auto-picked topic: {topic}")
    return topic


def generate_script(cfg: dict, topic: str, api_key: str, learnings: str = "") -> dict:
    v = cfg["video"]
    words = int(v["target_minutes"] * 150)
    learn_block = (f"\nCHANNEL LEARNINGS — apply these to hook style, pacing, and "
                   f"thumbnail text:\n{learnings}\n" if learnings else "")
    prompt = f"""You are a scriptwriter for a faceless YouTube channel
(voiceover + b-roll + motion graphics + captions, no on-camera host).

TOPIC: {topic}
TARGET: ~{words} spoken words total (about {v['target_minutes']} minutes at 150 wpm)
TONE: {cfg['channel']['tone']}
AUDIENCE: {cfg['channel']['audience']}
{learn_block}
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
      "visual_mode": "broll | ai_image | kinetic | stat",
      "search_terms": ["stock video search term", "alternative term", "broader fallback term"],
      "ai_prompt": "detailed text-to-image prompt (only when visual_mode is ai_image, else empty string)",
      "kinetic_text": "3-6 word punch phrase (only when visual_mode is kinetic, else empty string)",
      "stat": {{"value": 0, "suffix": "", "label": ""}}
    }}
  ]
}}

Visual mode rules (variety is the goal — videos must not feel stock-only):
- Most scenes are "broll" (stock footage exists for them).
- EXACTLY 1-2 scenes are "ai_image": visuals stock can't provide (ancient/extinct
  scenes, cutaway views, imagined perspectives). Write a rich ai_prompt.
- EXACTLY 1-2 scenes are "kinetic": a bold typography moment for the strongest
  line (often the hook or re-hook). kinetic_text = the phrase, punchy.
- 0-2 scenes are "stat": when narration centers on ONE striking number.
  Fill stat.value (number only), stat.suffix ("%", "km", "×"...), stat.label
  (what the number is). Narration must actually say that number.
- Every scene still needs search_terms as fallback. Concrete visual nouns only,
  and every term must belong to the topic's own visual world — never
  metaphorical/studio/commercial imagery (no drinks, food, offices, product
  shots), and wildlife must look wild ("aerial", "natural habitat" — never
  zoo/enclosure footage).

Script rules:
- {v['scenes_min']} to {v['scenes_max']} scenes. Scene 1 is a 30-second HOOK opening a
  curiosity gap immediately. A re-hook mid-video. Final scene is a 20-second
  payoff with a next-video tease. No "like and subscribe" begging.
- Narration is written for the EAR: short sentences, makes sense with eyes closed.
- Facts must be well-established; when uncertain, phrase carefully rather than
  inventing precise numbers.
- Every scene advances exactly one idea."""

    for attempt in range(3):
        try:
            script = _parse_json(_gemini(prompt, cfg, api_key))
            assert isinstance(script["scenes"], list) and len(script["scenes"]) >= 4
            for s in script["scenes"]:
                assert s["narration"].strip()
                s.setdefault("visual_mode", "broll")
                if s["visual_mode"] not in ("broll", "ai_image", "kinetic", "stat"):
                    s["visual_mode"] = "broll"
                s.setdefault("search_terms", [])
                s.setdefault("ai_prompt", "")
                s.setdefault("kinetic_text", "")
                s.setdefault("stat", {})
            assert script["title"].strip()
            script.setdefault("thumb_text", script["title"][:30])
            script["topic"] = topic
            modes = [s["visual_mode"] for s in script["scenes"]]
            print(f"[script] '{script['title']}' — {len(modes)} scenes, modes: {modes}")
            return script
        except (KeyError, AssertionError, json.JSONDecodeError) as e:
            print(f"[script] invalid script JSON (attempt {attempt + 1}): {e}")
    raise RuntimeError("Could not obtain a valid script after 3 attempts")


def generate_short_script(cfg: dict, topic: str, api_key: str,
                          learnings: str = "") -> dict:
    """Script for a vertical Short/Reel: one idea, ~40s, loop-friendly."""
    scfg = cfg.get("short", {})
    seconds = int(scfg.get("target_seconds", 40))
    words = int(seconds / 60 * 155)
    learn_block = (f"\nCHANNEL LEARNINGS — apply to hook and pacing:\n{learnings}\n"
                   if learnings else "")
    prompt = f"""You are writing a YouTube SHORT / Instagram REEL script for a
faceless channel (vertical video: voiceover + b-roll + big captions).

TOPIC: {topic}
TARGET: ~{words} spoken words TOTAL (~{seconds} seconds — shorts are ruthless)
TONE: {cfg['channel']['tone']}, but faster and punchier than long-form
{learn_block}
Return ONLY valid JSON:
{{
  "title": "<= 80 chars, curiosity gap, no clickbait lies",
  "thumb_text": "2-4 punch words",
  "description": "1-2 lines, end with hashtags including #shorts",
  "tags": ["6-10 tags"],
  "scenes": [
    {{
      "n": 1,
      "title": "2-4 word label",
      "narration": "8-30 words",
      "visual_mode": "broll | ai_image | kinetic | stat",
      "search_terms": ["concrete visual term", "alternative", "broader fallback"],
      "ai_prompt": "text-to-image prompt (only for ai_image, else empty)",
      "kinetic_text": "3-6 word punch phrase (only for kinetic, else empty)",
      "stat": {{"value": 0, "suffix": "", "label": ""}}
    }}
  ]
}}

Shorts rules:
- {scfg.get('scenes_min', 4)}-{scfg.get('scenes_max', 6)} micro-scenes. ONE idea total.
  HARD CAP: ~{words} spoken words across the whole script — if over, cut
  adjectives and merge scenes. Shorter beats complete.
- Scene 1 = the hook: <= 12 words, the single most jolting fact/question.
  No greetings, no context, no "did you know".
- LOOP ENDING (critical): the final scene is 8-15 words and must NOT
  summarize or conclude. Banned: "...prove that", "so next time", "that's
  why". Instead end on a question or unresolved tension whose answer is the
  opening line, so an instant replay reads as one continuous thought.
- Exactly 1-2 "kinetic" scenes, 0-1 "stat", 0-1 "ai_image", rest "broll".
- SEARCH TERM DISCIPLINE (footage relevance depends on this):
  * Every term must belong to the TOPIC'S OWN VISUAL WORLD. If the topic is
    polar, terms are "glacier calving aerial", "arctic tundra", "ice sheet
    drone" — never generic ice cubes or drinks.
  * NEVER metaphorical, studio, or commercial-looking imagery: no beverages,
    food, offices, hands, product shots.
  * Wildlife must look WILD: add "wild"/"aerial"/"natural habitat" to animal
    terms; zoo or enclosure footage is forbidden.
  * Prefer vertical-friendly subjects (waterfalls, cliffs, towers, canyons,
    aurora, drone descents).
- Every sentence must earn its half-second. Cut every filler word."""

    for attempt in range(3):
        try:
            script = _parse_json(_gemini(prompt, cfg, api_key))
            assert isinstance(script["scenes"], list) and len(script["scenes"]) >= 3
            for s in script["scenes"]:
                assert s["narration"].strip()
                s.setdefault("visual_mode", "broll")
                if s["visual_mode"] not in ("broll", "ai_image", "kinetic", "stat"):
                    s["visual_mode"] = "broll"
                s.setdefault("search_terms", [])
                s.setdefault("ai_prompt", "")
                s.setdefault("kinetic_text", "")
                s.setdefault("stat", {})
            assert script["title"].strip()
            script.setdefault("thumb_text", script["title"][:20])
            script["topic"] = topic
            print(f"[script] SHORT '{script['title']}' — "
                  f"{[s['visual_mode'] for s in script['scenes']]}")
            return script
        except (KeyError, AssertionError, json.JSONDecodeError) as e:
            print(f"[script] invalid short JSON (attempt {attempt + 1}): {e}")
    raise RuntimeError("Could not obtain a valid short script after 3 attempts")


def log_topic_done(topic: str, done_file: str = "topics_done.txt") -> None:
    with open(done_file, "a", encoding="utf-8") as f:
        f.write(topic + "\n")
