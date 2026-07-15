"""Stage 1 — topic selection + scene-segmented script via Gemini API (free tier).

Reads learnings.md (written by the analytics loop) so topic choice, hook
style, pacing and thumbnail text adapt to what has performed on the channel.

Language: driven by channel.language in config.yaml. For Hindi (hi-*) all
viewer-facing text is written in Devanagari, while stock search terms and
AI image prompts stay in English (libraries are indexed in English).
"""
import json
import math
import os
import re
import time

import requests

import visual_beats as visual_beats_mod

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


_anthropic_available: list | None = None


def _anthropic_discover(headers: dict) -> list[str]:
    """Ask the API which models this key can actually use (newest first).
    Cached per run; failure just returns [] and we rely on config names."""
    global _anthropic_available
    if _anthropic_available is None:
        try:
            r = requests.get("https://api.anthropic.com/v1/models?limit=100",
                             headers=headers, timeout=30)
            r.raise_for_status()
            _anthropic_available = [m["id"] for m in r.json().get("data", [])]
            print(f"[script] anthropic models available: "
                  f"{_anthropic_available[:6]}")
        except Exception:
            _anthropic_available = []
    return _anthropic_available


def _anthropic(prompt: str, cfg: dict, api_key: str) -> str:
    """Claude for script writing — used when ANTHROPIC_API_KEY is set."""
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    models = [cfg["llm"].get("anthropic_model", "claude-sonnet-5")] + list(
        cfg["llm"].get("anthropic_fallback_models", ["claude-haiku-4-5-20251001"]))
    # self-heal: append whatever sonnet/haiku this key really has access to
    discovered = _anthropic_discover(headers)
    models += [m for m in discovered if "sonnet" in m]
    models += [m for m in discovered if "haiku" in m]
    seen: set = set()
    models = [m for m in models if not (m in seen or seen.add(m))]

    last_err = None
    for model in models:
        body = {
            "model": model,
            "max_tokens": 8000,
            "temperature": min(float(cfg["llm"].get("temperature", 0.9)), 1.0),
            "system": ("You are a JSON API. Respond with ONLY the requested "
                       "JSON object — no preamble, no markdown fences, no "
                       "commentary after the closing brace."),
            "messages": [{"role": "user", "content": prompt}],
        }
        for attempt in range(3):
            try:
                r = requests.post(ANTHROPIC_URL, json=body, headers=headers,
                                  timeout=180)
                if r.status_code == 404 or (r.status_code == 400
                                            and "model" in r.text.lower()):
                    print(f"[script] anthropic model {model} unavailable, next")
                    last_err = r.text[:200]
                    break
                if r.status_code in (429, 529):
                    wait = 20 * (attempt + 1)
                    print(f"[script] anthropic busy, sleeping {wait}s")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                return r.json()["content"][0]["text"]
            except requests.RequestException as e:
                last_err = str(e)
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Anthropic call failed on all models: {last_err}")


def _llm(prompt: str, cfg: dict, gemini_key: str) -> str:
    """Route to Claude when a key exists (better scripts), else Gemini.
    Any Claude failure silently falls back to Gemini — runs never block."""
    ak = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    provider = str(cfg["llm"].get("provider", "auto")).lower()
    if ak and provider in ("auto", "anthropic"):
        try:
            return _anthropic(prompt, cfg, ak)
        except Exception as e:
            print(f"[script] anthropic failed ({e}) -> gemini fallback")
    return _gemini(prompt, cfg, gemini_key)


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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # LLMs sometimes add prose around the JSON — extract the first
        # balanced object (string-aware brace scan) and parse that.
        start = text.find("{")
        if start == -1:
            raise
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])
        raise


def _is_hindi(cfg: dict) -> bool:
    return str(cfg["channel"].get("language", "en-us")).lower().startswith("hi")


def _wpm(cfg: dict) -> int:
    # Hindi documentary narration runs slower than English (~130 vs 150 wpm)
    return int(cfg["channel"].get("wpm", 130 if _is_hindi(cfg) else 150))


def _lang_rules(cfg: dict) -> str:
    if not _is_hindi(cfg):
        return ""
    return """
LANGUAGE — this channel speaks HINDI:
- narration, title, description, tags, scene titles, kinetic_text and
  stat.label are ALL in natural spoken Hindi (Devanagari script).
- EXCEPTION — thumb_text: bold ENGLISH/Hinglish keywords in Latin script
  ("DEADLY PLANET", "MYSTERY SOLVED", "AAKHIR KYUN?") — English thumbnail
  keywords outperform Devanagari in the Hindi market.
- Register: the Hindi of a good documentary narrator — clear, warm,
  conversational. Common loanwords are fine in Devanagari (डॉक्यूमेंट्री,
  किलोमीटर), but never write full English sentences.
- NUMBERS in narration: Arabic numerals; anything longer than 4 digits gets
  commas (10,000 not 10000) so the voice reads it as one number.
- HARD RULE: search_terms and ai_prompt stay in ENGLISH — stock libraries
  and image models are indexed in English.
- tags: mostly Hindi, plus 2-4 English tags for search reach.
"""


def _style_rules() -> str:
    return """
WRITING STYLE — the script must feel human-written, never AI-generated:
- BANNED openers/phrases (any language): "have you ever wondered", "did you
  know", "imagine a world", "let's dive in", "in conclusion", "क्या आप जानते
  हैं", "आइए जानते हैं", "कल्पना कीजिए" as a stock opener, "निष्कर्ष".
- Rhythm: alternate short punch sentences (3-6 words) with medium ones.
  Every scene ends on a concrete image, place or number — never an
  abstraction or a summary.
- Specificity beats breadth: one vivid, named fact per scene (a place, a
  number, a comparison a viewer can picture) instead of three vague claims.
- Voice: a person telling a friend a secret — confident, a little amused,
  zero lecture tone.
"""


def _ai_max(cfg: dict) -> int:
    """AI-image budget per video — richer when a FLUX (fal.ai) key is set."""
    aicfg = cfg.get("ai_images", {})
    if os.environ.get("FAL_KEY", "").strip():
        return int(aicfg.get("max_per_video_flux",
                             max(int(aicfg.get("max_per_video", 2)), 4)))
    return int(aicfg.get("max_per_video", 2))


VALID_MODES = ("broll", "ai_image", "kinetic", "stat", "card", "map", "glass")


def _num_or_none(value):
    """Return a finite float, otherwise None (LLMs sometimes emit NaN/inf)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _normalize_stat(raw) -> dict:
    """Keep only safe, bounded fields understood by the Remotion stat cards."""
    stat = raw if isinstance(raw, dict) else {}
    value = _num_or_none(stat.get("value"))
    baseline = _num_or_none(stat.get("baseline"))
    maximum = _num_or_none(stat.get("max"))
    bars = []
    if isinstance(stat.get("bars"), list):
        for item in stat["bars"][:5]:
            if not isinstance(item, dict):
                continue
            bar_value = _num_or_none(item.get("value"))
            if bar_value is None:
                continue
            bars.append({"label": str(item.get("label", ""))[:24],
                         "value": bar_value})
    result = {
        "value": value if value is not None else 0,
        "suffix": str(stat.get("suffix", ""))[:12],
        "label": str(stat.get("label", ""))[:100],
    }
    if baseline is not None:
        result["baseline"] = baseline
    if maximum is not None and maximum > 0:
        result["max"] = maximum
    if len(bars) >= 2:
        result["bars"] = bars
    return result


def _normalize_glass(raw) -> dict:
    """Bound the data contract consumed by the liquid-glass renderer."""
    data = raw if isinstance(raw, dict) else {}
    result = {
        "kicker": str(data.get("kicker", ""))[:32],
        "headline": str(data.get("headline", ""))[:90],
        "body": str(data.get("body", ""))[:130],
        "suffix": str(data.get("suffix", ""))[:14],
        "label": str(data.get("label", ""))[:90],
        "location": str(data.get("location", ""))[:60],
        "coordinates": str(data.get("coordinates", ""))[:36],
        "chapter": str(data.get("chapter", ""))[:24],
    }
    value = _num_or_none(data.get("value"))
    delta = _num_or_none(data.get("delta"))
    if value is not None:
        result["value"] = value
    if delta is not None:
        result["delta"] = delta
    direction = str(data.get("delta_direction", data.get("deltaDirection", ""))).lower()
    if direction in ("up", "down", "flat"):
        result["deltaDirection"] = direction
    return result


def _normalize_milestone(raw) -> dict:
    """Bound the per-scene simulation milestone for the story HUD."""
    data = raw if isinstance(raw, dict) else {}
    value = _num_or_none(data.get("value"))
    if value is None:
        return {}
    return {"value": value,
            "label": str(data.get("label", ""))[:18],
            "unit": str(data.get("unit", ""))[:8]}


def _normalize(script: dict, min_scenes: int) -> dict:
    """Validate + default-fill a script dict. Raises on structural problems."""
    assert isinstance(script["scenes"], list) and len(script["scenes"]) >= min_scenes
    for s in script["scenes"]:
        assert s["narration"].strip()
        s.setdefault("visual_mode", "broll")
        if s["visual_mode"] not in VALID_MODES:
            s["visual_mode"] = "broll"
        s.setdefault("search_terms", [])
        s.setdefault("ai_prompt", "")
        s.setdefault("kinetic_text", "")
        s["stat"] = _normalize_stat(s.get("stat"))
        s["glass"] = _normalize_glass(s.get("glass"))
        s.setdefault("card", {})
        s.setdefault("map", {})
        s["milestone"] = _normalize_milestone(s.get("milestone"))
        d = str(s.get("delivery", "calm")).lower().strip()
        s["delivery"] = d if d in ("hook", "calm", "reveal", "urgent") else "calm"
        role = str(s.get("visual_role", "")).lower().strip()
        s["visual_role"] = (role if role in ("experience", "explanation",
                                             "measurement") else "")
        s["must_show"] = [str(t)[:40] for t in (s.get("must_show") or [])
                          if str(t).strip()][:3]
    script["scenes"][0]["delivery"] = "hook"
    assert script["title"].strip()
    script.setdefault("thumb_text", script["title"][:30])
    script.setdefault("thumb_prompt", "")
    script["thumb_headline"] = str(script.get("thumb_headline", ""))[:60]
    script["thumb_question"] = str(script.get("thumb_question", ""))[:40]
    script["premise"] = str(script.get("premise", ""))[:200]
    cv = script.get("changing_variable") or {}
    script["changing_variable"] = {"label": str(cv.get("label", ""))[:18],
                                   "unit": str(cv.get("unit", ""))[:8]}
    script["hero_prompt"] = str(script.get("hero_prompt", ""))[:500]
    script["forbidden_visuals"] = [str(t)[:40] for t in
                                   (script.get("forbidden_visuals") or [])
                                   if str(t).strip()][:6]
    script["next_tease_topic"] = str(script.get("next_tease_topic", ""))[:120]
    script["title_options"] = [str(t)[:90] for t in
                               (script.get("title_options") or [])
                               if str(t).strip()][:5]
    thumbs = []
    for item in (script.get("thumb_options") or [])[:3]:
        if isinstance(item, dict) and str(item.get("text", "")).strip():
            thumbs.append({"text": str(item.get("text", ""))[:30],
                           "concept": str(item.get("concept", ""))[:120]})
    script["thumb_options"] = thumbs
    return script


def _critique(script: dict, cfg: dict, api_key: str, kind: str,
              min_scenes: int) -> dict:
    """Second pass — a ruthless retention editor rewrites weak scenes.
    Fail-open: any problem returns the original draft."""
    if not cfg["llm"].get("critique", True):
        return script
    fmt = ("a ~28-second vertical Short (hook <= 12 words; full PAYOFF, then "
           "a loop-friendly final line)" if kind == "short"
           else "a 6-minute documentary (30s hook, mid-video re-hook, payoff ending)")
    prompt = f"""You are a ruthless retention editor for a Hindi faceless
YouTube channel. Below is a draft script for {fmt}.

Grade every scene 1-10 on: hook strength, specificity (named places and
numbers a viewer can picture), curiosity pull into the NEXT scene, and
sentence rhythm. Then REWRITE any scene scoring below 8 — sharper verbs,
more concrete nouns, tighter sentences, zero filler. Keep the same JSON
schema, scene count, visual_mode and search_terms (you may improve
narration, titles, kinetic_text, delivery and thumb_text).
{_lang_rules(cfg)}
Return ONLY the full revised JSON — no scores, no commentary.

DRAFT:
{json.dumps(script, ensure_ascii=False)}"""
    try:
        revised = _normalize(_parse_json(_llm(prompt, cfg, api_key)), min_scenes)
        # The critique edits words, not factual display payloads. Preserve the
        # first pass's structured visual data so a rewrite cannot silently turn
        # a stat/glass/map scene into an empty overlay.
        for before, after in zip(script["scenes"], revised["scenes"]):
            for field in ("stat", "card", "glass", "map", "milestone",
                          "must_show", "visual_role"):
                after[field] = before.get(field, after.get(field, {}))
        for field in ("premise", "changing_variable", "hero_prompt",
                      "forbidden_visuals", "title_options", "thumb_options",
                      "thumb_headline", "thumb_question", "next_tease_topic"):
            if not revised.get(field):
                revised[field] = script.get(field, revised.get(field))
        revised["topic"] = script.get("topic", "")
        print("[script] critique pass applied")
        return revised
    except Exception as e:
        print(f"[script] critique pass skipped ({e}) — keeping draft")
        return script


def load_learnings(repo_root: str) -> str:
    """Analytics learnings + the permanent failure registry — both are
    injected into every topic/script prompt so past mistakes become rules."""
    text = ""
    try:
        with open(os.path.join(repo_root, "learnings.md"), encoding="utf-8") as f:
            text = f.read().strip()[:6000]
    except Exception:
        pass
    try:
        with open(os.path.join(repo_root, "FAILURES.md"), encoding="utf-8") as f:
            failures = f.read().strip()[:3000]
        if failures:
            text += ("\n\nPAST PRODUCTION FAILURES — HARD RULES, never repeat "
                     "any of these:\n" + failures)
    except Exception:
        pass
    return text.strip()


def pick_topic(cfg: dict, api_key: str, done_file: str = "topics_done.txt",
               learnings: str = "") -> str:
    forced = os.environ.get("FORCED_TOPIC", "").strip()
    if forced:
        print(f"[script] using forced topic: {forced}")
        return forced

    done, tease = [], ""
    if os.path.exists(done_file):
        with open(done_file, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                if ln.startswith("NEXT:"):
                    tease = ln[5:].strip()  # last marker wins
                else:
                    done.append(ln)
    # honor the previous episode's on-screen tease — the video made a promise
    if tease and tease not in done:
        print(f"[script] honoring previous episode's on-screen tease: {tease}")
        return tease

    learn_block = (f"\nWHAT HAS WORKED ON THIS CHANNEL (analytics digest):\n{learnings}\n"
                   if learnings else "")
    lang_note = ("\nWrite the topic itself in Hindi (Devanagari script).\n"
                 if _is_hindi(cfg) else "")
    prompt = f"""You are the content strategist for a faceless YouTube channel.

NICHE: {cfg['channel']['niche']}
AUDIENCE: {cfg['channel']['audience']}
{learn_block}
Already-covered topics (NEVER repeat or closely paraphrase these, in any
language):
{json.dumps(done[-100:], indent=0, ensure_ascii=False)}

Invent THREE candidate video topics with strong curiosity-gap appeal that can
be illustrated with stock footage of landscapes, cities, nature, aerials and
oceans plus occasional AI-generated stills (no specific people, no events
needing news footage, nothing requiring licensed material). If the analytics
digest above shows a topic family performing well, lean into that family
without repeating covered topics.

THE VISUAL JOURNEY TEST — score each candidate 1-10 on ALL of:
- journey: is there ONE changing variable the viewer travels along
  (depth, speed, time, temperature, scale)?
- escalation: can it produce 6+ visibly escalating milestones?
- number_hook: does it contain one concrete, quotable number?
- human_stakes: is there a consequence a viewer can feel on their own body/city?
- visual: does something VISIBLY change on screen every 30 seconds?
- thumbnail: can it be drawn as ONE dramatic image?
- feasibility: can stock footage + AI stills TRUTHFULLY illustrate it
  (no reenactments, no specific people, no news footage)?
- source_confidence: are its core facts well-established and easy to verify
  with primary scientific/government sources?
- sequel: does it naturally open an obvious next-episode question?
A topic that is a list of facts ("types of X") must score low on journey.
REJECT any candidate that is interesting but cannot be shown truthfully
(feasibility <= 4) or whose central claim cannot be verified
(source_confidence <= 4) — an accurate, filmable topic beats a viral,
unfilmable one.
{lang_note}
Return JSON exactly:
{{"candidates": [{{"topic": "...", "scores": {{"journey": 0, "escalation": 0,
"number_hook": 0, "human_stakes": 0, "visual": 0, "thumbnail": 0,
"feasibility": 0, "source_confidence": 0, "sequel": 0}},
"total": 0}}],
"topic": "<the candidate with the highest total>"}}"""
    last_err = None
    for attempt in range(3):
        try:
            parsed = _parse_json(_llm(prompt, cfg, api_key))
            topic = str(parsed.get("topic") or "").strip()
            if not topic:
                cands = parsed.get("candidates") or []
                cands = sorted(cands, key=lambda c: -float(c.get("total", 0)))
                topic = str(cands[0]["topic"]).strip()
            print(f"[script] auto-picked topic (journey-tested): {topic}")
            return topic
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            last_err = e
            print(f"[script] bad topic JSON (attempt {attempt + 1}): {e}")
    raise RuntimeError(f"Could not pick a topic after 3 attempts: {last_err}")


def _plan_visual_beats(script: dict, cfg: dict, api_key: str) -> dict:
    """Add sentence-level stock intentions using one free Gemini request.

    This intentionally bypasses the optional paid script provider.  The task
    is constrained visual indexing, not creative writing, and Gemini's free
    tier is sufficient.  Any API/schema failure falls back to deterministic
    coverage based on the scene's existing search terms.
    """
    settings = cfg.get("longform_quality", {}).get("visual_beats", {})
    if not settings.get("enabled", True):
        return script
    payload = visual_beats_mod.planner_payload(script, cfg)
    forbidden = script.get("forbidden_visuals") or []
    contract = ""
    if forbidden or script.get("hero_prompt"):
        contract = f"""
CONTINUITY CONTRACT (breaking it ruins the episode):
- FORBIDDEN VISUALS: {json.dumps(forbidden)} — never write a query that could
  return any of these; they contradict the premise.
- The episode has ONE recurring hero ({str(script.get('hero_prompt', ''))[:120]}).
  Beats about the protagonist are carried by that hero image — write those
  beats' queries for the surrounding ENVIRONMENT, never for stock humans.
"""
    prompt = f"""You are the visual editor of a premium science documentary.
Turn the FINAL Hindi narration below into a sentence-level visual beat sheet.
{contract}

Return ONLY JSON:
{{"scenes":[{{"n":1,"visual_beats":[{{
  "cue":"an EXACT 3-8 word verbatim phrase from the Hindi narration where this visual starts",
  "search_terms":["one exact concrete ENGLISH Pexels query","one fallback query"],
  "purpose":"what the viewer must understand from this visual"
}}]}}]}}

Rules:
- Return exactly target_beats for each scene and preserve scene order.
- Beat 1 starts at the beginning of its scene; all cues proceed in narration order.
- Each query must depict the nouns in its cue, not the scene's general mood.
- Named landmarks, animals, machines, planets and anatomy require the exact subject.
- Prefer real documentary footage: aerials, macro, natural habitat, physical processes.
- Never use metaphorical offices, typing, food, drinks, products or captive wildlife.
- Vary scale and camera language across consecutive beats.
- Do not request generated art, text, logos or copyrighted characters.

SCENES:
{json.dumps(payload, ensure_ascii=False)}"""
    try:
        raw = _parse_json(_gemini(prompt, cfg, api_key))
        script = visual_beats_mod.normalize_plan(script, raw, cfg)
        total = sum(len(s.get("visual_beats", [])) for s in script["scenes"])
        print(f"[script] semantic visual plan: {total} beats (free Gemini pass)")
        return script
    except Exception as exc:
        print(f"[script] visual beat planner skipped ({exc}) — deterministic fallback")
        return visual_beats_mod.normalize_plan(script, None, cfg)


def generate_script(cfg: dict, topic: str, api_key: str, learnings: str = "") -> dict:
    v = cfg["video"]
    wpm = _wpm(cfg)
    words = int(v["target_minutes"] * wpm)
    ai_max = _ai_max(cfg)
    learn_block = (f"\nCHANNEL LEARNINGS — apply these to hook style, pacing, and "
                   f"thumbnail text:\n{learnings}\n" if learnings else "")
    prompt = f"""You are a scriptwriter for a faceless YouTube channel
(voiceover + b-roll + motion graphics + captions, no on-camera host).

TOPIC: {topic}
TARGET: ~{words} spoken words total (about {v['target_minutes']} minutes at {wpm} wpm)
HARD RANGE: {int(words * 0.92)}-{int(words * 1.08)} spoken words across all
scenes. Under {int(words * 0.92)} produces a video shorter than promised;
count your words before returning and expand thin scenes with concrete
material (never filler).
TONE: {cfg['channel']['tone']}
AUDIENCE: {cfg['channel']['audience']}
{learn_block}{_lang_rules(cfg)}{_style_rules()}
Write a scene-segmented script and return ONLY valid JSON with this exact shape:
{{
  "title": "click-worthy but honest YouTube title, <= 70 chars",
  "title_options": ["5 alternative Hindi titles, strongest first: one conservative, one high-curiosity, one number-driven among them"],
  "thumb_text": "3-5 bold ENGLISH/Hinglish keywords for the thumbnail (Latin script)",
  "thumb_headline": "4-7 word DRAMATIC Hindi headline (Devanagari) — the emotional hook of the thumbnail, high intensity but 100% provable by the video (e.g. 'मारियाना ट्रेंच का खूनी सच!'); never a fabricated claim",
  "thumb_question": "3-5 word Hindi curiosity question for a small thumbnail annotation (e.g. 'शरीर का क्या होगा?'); empty string if none fits",
  "thumb_prompt": "ENGLISH text-to-image prompt for the thumbnail. NON-NEGOTIABLE: ONE dramatic subject FILLING 50-70% of the frame, strong rim light separating it clearly from the background, at least one vivid color accent; mid-dark background WITH visible depth — NEVER a mostly-black or murky image (it must read instantly at 160px feed size); keep the bottom third relatively empty for the title text",
  "thumb_options": [{{"text": "2-4 Latin punch words", "concept": "one-line alternative visual idea"}}, {{"text": "...", "concept": "..."}}, {{"text": "...", "concept": "..."}}],
  "premise": "ONE Hindi sentence: the impossible rule / continuous journey of this episode",
  "changing_variable": {{"label": "SHORT ENGLISH metric the viewer watches change (DEPTH, SPEED, TIME, TEMP, SIZE)", "unit": "km"}},
  "hero_prompt": "ENGLISH text-to-image prompt for the episode's recurring HERO subject — one person/object/place the video returns to as conditions change: subject + setting + light + camera angle",
  "forbidden_visuals": ["3-6 short ENGLISH phrases describing footage that would BREAK the premise and must never appear (e.g. for an unprotected-human deep-sea premise: 'scuba diver', 'diving suit', 'oxygen tank', 'snorkeler')"],
  "next_tease_topic": "the EXACT topic teased in the final scene, as a Hindi working title — the pipeline will make it the next episode, so it must be a producible topic (stock+AI illustrable) and the tease itself must be factually accurate",
  "description": "2-3 sentence YouTube description ending with 3 relevant hashtags",
  "tags": ["8-12 YouTube tags"],
  "scenes": [
    {{
      "n": 1,
      "title": "3-6 word scene title",
      "narration": "60-150 words of spoken narration",
      "visual_mode": "broll | ai_image | kinetic | stat | card | map | glass",
      "visual_role": "experience | explanation | measurement",
      "delivery": "hook | calm | reveal | urgent",
      "must_show": ["1-2 short ENGLISH phrases naming what MUST be visible on screen for this scene's narration to be true"],
      "milestone": {{"value": 0, "label": "optional ENGLISH override of the metric label", "unit": "km"}},
      "search_terms": ["stock video search term", "alternative term", "broader fallback term"],
      "ai_prompt": "detailed text-to-image prompt (only when visual_mode is ai_image, else empty string)",
      "kinetic_text": "3-6 word punch phrase (only when visual_mode is kinetic, else empty string)",
      "stat": {{"value": 0, "suffix": "", "label": "", "max": null, "baseline": null, "bars": [{{"label": "short label", "value": 0}}]}},
      "card": {{"kicker": "short category", "headline": "5-10 word headline", "body": "one concise explanatory sentence"}},
      "glass": {{"kicker": "short category", "headline": "main Hindi line", "body": "one short support line", "value": null, "suffix": "", "label": "", "delta": null, "delta_direction": "up | down | flat", "location": "", "coordinates": "", "chapter": ""}},
      "map": {{"lat": 0.0, "lon": 0.0, "label": ""}}
    }}
  ]
}}

Delivery direction (how the narrator speaks each scene):
- scene 1 = "hook" (energetic). The scene landing the biggest twist/number =
  "reveal" (slower, with a beat of silence before it). "urgent" at most once.
  Everything else "calm". Never two "reveal" scenes in a row.

Map scenes: when ONE specific place is the star of a scene, set visual_mode
"map" with accurate map.lat / map.lon and a short Hindi map.label (0-2 map
scenes per video; still provide search_terms as fallback).

Visual mode rules (variety is the goal — videos must not feel stock-only):
- Most scenes are "broll" (stock footage exists for them).
- EXACTLY 1-{ai_max} scenes are "ai_image": visuals stock can't provide
  (ancient/extinct scenes, cutaway views, imagined perspectives, precise
  historical moments). Write a rich, specific ai_prompt: subject + setting +
  light + camera angle. These become the video's signature shots — use them
  on the hook, the re-hook and the payoff where possible.
- EXACTLY 1-2 scenes are "kinetic": a bold typography moment for the strongest
  line (often the hook or re-hook). kinetic_text = the phrase, punchy.
- 0-2 scenes are "stat": when narration centers on ONE striking number.
  Fill stat.value (number only), stat.suffix ("%", "km", "×"...), stat.label
  (what the number is). Narration must actually say that number. For a share of
  a whole, add stat.max to opt into a ring gauge. For before/after, add numeric
  stat.baseline. For a 2-5 item comparison, add stat.bars with short labels and
  numeric values. Use only one of max, baseline or bars; omit unused fields.
- 0-2 scenes are "card": use a concise editorial definition, warning,
  comparison, quotation or timeline beat when text explains the idea better
  than generic stock. Fill card.kicker/headline/body; keep body under 18 words.
- EXACTLY 1 scene is "glass": a premium smoked liquid-glass information beat.
  Use value/suffix/label for a metric, location/coordinates for a place,
  chapter/headline for an act break, or headline/body for a fact. Reserve the
  biggest reveal for delivery="reveal"; the renderer selects the matching layout.
- Every scene still needs search_terms as fallback. Concrete visual nouns only,
  and every term must belong to the topic's own visual world — never
  metaphorical/studio/commercial imagery (no drinks, food, offices, product
  shots), and wildlife must look wild ("aerial", "natural habitat" — never
  zoo/enclosure footage).
- If narration names a real landmark, machine, animal or anatomical structure,
  search_terms[0] MUST name the exact subject. When exact footage is unlikely,
  rewrite the narration generically instead of showing a misleading substitute.
- CONTINUITY CONTRACT: no search term may describe (or be likely to return)
  anything in forbidden_visuals. When a scene needs the protagonist/hero,
  do not request stock humans — the recurring hero image carries those beats;
  write search_terms for the ENVIRONMENT instead.
- MUST-SHOW CONTRACT: each scene's must_show names the 1-2 concrete things
  the footage must actually depict for the narration to be true (e.g.
  "deep ocean darkness", "volcanic vent"). Keep them findable in stock —
  the pipeline rejects footage that misses them, so never demand the
  impossible; leave the list empty for abstract/graphic scenes.
- VISUAL ROLE ROTATION (anti-montage rule): tag every scene's visual_role —
  "experience" (what the viewer would see/feel there), "explanation" (why it
  happens — cards/diagrams/cutaways), "measurement" (how deep/hot/fast —
  stat/glass/HUD moments). Never let three consecutive scenes share one
  role; this rotation is what separates a documentary from a stock montage.
- SHOT RHYTHM (the idea sets the cut, not a timer): the hook cuts fast —
  write it in short punchy sentences; normal scenes breathe; give the single
  most beautiful or emotional scene FEWER words so its visual can hold for
  8-10 seconds; the reveal keeps its beat of silence.

Script rules:
- SCENARIO LOCK (scientific integrity): if the premise is a hypothetical with
  multiple interpretations, CHOOSE ONE in the cold open and derive every
  consequence from that single scenario — never mix consequences from
  different interpretations of the same "what if".
- SIMULATION ENGINE (most important rule): the video is a guided simulation.
  "premise" states one impossible/curious rule; "changing_variable" is the ONE
  number the viewer watches move. EVERY scene gets a milestone.value along
  that variable, and the values must escalate monotonically (deeper, faster,
  hotter, bigger) from scene 1 to the climax. The narration of each scene must
  actually SAY its milestone value. A viewer should be able to answer "where
  are we now?" at any second. If a scene has no meaningful position on the
  variable, it does not belong in the video.
- NARRATIVE SPINE: the whole video follows ONE concrete thread — a journey, a
  single tightening question, or one entity moving through the story (one
  drop of rain travelling underground; one signal crossing space). The
  "hero_prompt" subject is that entity: the video returns to it as conditions
  change. Introduce the spine inside the cold open and pay it off in the
  final scene — the ending should resolve the exact image the video opened on.
- SCALE ANCHORING: every large number gets exactly ONE familiar comparison the
  audience can feel — for this Hindi channel prefer Indian anchors (Delhi to
  Jaipur distance, Burj Khalifa/Himalaya heights, a Rajdhani train's speed,
  monsoon rainfall, Mumbai's population). One vivid anchor beats three vague
  ones; never force it.
- VISUAL PACING MIX (how a human editor cuts): ~60% of scenes are slow,
  majestic b-roll moments that breathe; ~20% are rapid intercut stretches
  (short beats, quick cuts, urgency); ~20% are graphic moments (kinetic /
  stat / card / glass / map). Graphics are 3-5 second IMPACT hits, not
  wallpaper — after a graphic lands, the narration must move on and hand the
  screen back to footage. Never let two graphic scenes sit adjacent.
- {v['scenes_min']} to {v['scenes_max']} scenes. Scene 1 is an 18-25 second COLD OPEN
  that states the premise immediately and opens a curiosity gap. Deliver the
  first concrete answer by 45 seconds. Add one-sentence re-hooks near 25%, 50%
  and 75% of the runtime, each paired with a new visual mode. Final scene is a 20-second
  payoff with a next-video tease. No "like and subscribe" begging.
- THE TEASE IS A CONTRACT: the final scene's tease must describe
  next_tease_topic exactly, and its claim must be factually accurate with the
  correct comparison (Venus melts LEAD — it does not vaporize iron). The next
  episode WILL be this topic — never tease something unproducible.
- Narration is written for the EAR: short sentences, makes sense with eyes closed.
- Facts must be well-established; when uncertain, phrase carefully rather than
  inventing precise numbers.
- Every scene advances exactly one idea."""

    def _word_count(s: dict) -> int:
        return sum(len(str(sc.get("narration", "")).split()) for sc in s["scenes"])

    for attempt in range(3):
        try:
            script = _normalize(_parse_json(_llm(prompt, cfg, api_key)), 4)
            script["topic"] = topic
            script = _critique(script, cfg, api_key, "long", 4)
            # enforce the word budget BEFORE TTS — a short script is a short
            # video, and expanding here is free (no wasted voice credits)
            wc = _word_count(script)
            if wc < int(words * 0.88):
                print(f"[script] undershoot ({wc}/{words} words) — expansion pass")
                exp = f"""The draft below runs {wc} spoken words but must run
{int(words * 0.95)}-{int(words * 1.05)} words. Expand the THINNEST scenes with
concrete, specific material — mechanisms, named places, numbers, consequences
— never filler, never repetition. Keep the same JSON schema, scene count,
visual modes and every non-narration field unchanged.
{_lang_rules(cfg)}
Return ONLY the full revised JSON.

DRAFT:
{json.dumps(script, ensure_ascii=False)}"""
                try:
                    expanded = _normalize(_parse_json(_llm(exp, cfg, api_key)), 4)
                    for before, after in zip(script["scenes"], expanded["scenes"]):
                        for field in ("stat", "card", "glass", "map", "milestone"):
                            after[field] = before.get(field, {})
                    for field in ("premise", "changing_variable", "hero_prompt",
                                  "forbidden_visuals", "title_options",
                                  "thumb_options", "thumb_headline",
                                  "thumb_question", "next_tease_topic"):
                        if not expanded.get(field):
                            expanded[field] = script.get(field)
                    expanded["topic"] = topic
                    if _word_count(expanded) > wc:
                        script = expanded
                        print(f"[script] expanded to {_word_count(script)} words")
                except Exception as exc:
                    print(f"[script] expansion skipped ({exc})")
            script = _plan_visual_beats(script, cfg, api_key)
            modes = [s["visual_mode"] for s in script["scenes"]]
            print(f"[script] '{script['title']}' — {len(modes)} scenes, modes: {modes}")
            return script
        except (KeyError, AssertionError, json.JSONDecodeError) as e:
            print(f"[script] invalid script JSON (attempt {attempt + 1}): {e}")
    raise RuntimeError("Could not obtain a valid script after 3 attempts")


def generate_short_script(cfg: dict, topic: str, api_key: str,
                          learnings: str = "") -> dict:
    """Script for a vertical Short/Reel: one idea, loop-friendly. Length is
    ADAPTIVE inside [min_seconds, max_seconds]: the story's promise decides,
    not a fixed clock — a checkpoint journey needs more runway than one fact
    (the #1 viewer complaint on fixed-length shorts was "feels cut off")."""
    scfg = cfg.get("short", {})
    min_seconds = int(scfg.get("min_seconds", scfg.get("target_seconds", 40)))
    max_seconds = int(scfg.get("max_seconds",
                               max(55, int(scfg.get("target_seconds", 30)))))
    # shorts word budget calibrates to the REAL spoken pace (Sarvam Hindi with
    # pauses runs ~95-105 wpm, well below the long-form planning rate)
    wpm = int(scfg.get("wpm", min(_wpm(cfg), 105)))
    min_words = int(min_seconds / 60 * wpm)
    words = int(max_seconds / 60 * wpm)
    seconds = max_seconds
    short_ai_max = min(_ai_max(cfg), 2)
    learn_block = (f"\nCHANNEL LEARNINGS — apply to hook and pacing:\n{learnings}\n"
                   if learnings else "")
    prompt = f"""You are writing a YouTube SHORT / Instagram REEL script for a
faceless channel (vertical video: voiceover + b-roll + big captions).

TOPIC: {topic}
LENGTH — the story decides, inside a hard band:
HARD RANGE: {min_words}-{int(words * 1.05)} spoken words TOTAL
({min_seconds}-{max_seconds} seconds). Use the FEWEST words that COMPLETELY
pay off the title's promise — one crisp fact fits the bottom of the band;
a journey/timeline/checkpoint topic ("हर 1000 मीटर पर...", "minute by
minute...") needs the top of the band, because every promised checkpoint
must actually appear. Never stretch a small idea and never amputate a big
one. Count your words before returning.

PROMISE AUDIT (do this BEFORE writing scenes): list to yourself the 3-5
questions your title makes the viewer expect. Every one of them must be
answered on screen. If the title promises N checkpoints/minutes/stages, all
N appear — a video that answers 2 of 5 expected questions feels cut off and
gets swiped into oblivion. The second-to-last scene must resolve the CENTRAL
question with a clear verdict (what it means / who survives / what remains),
not just another fact.
TONE: {cfg['channel']['tone']}, but faster and punchier than long-form
{learn_block}{_lang_rules(cfg)}{_style_rules()}
Return ONLY valid JSON:
{{
  "title": "<= 80 chars, curiosity gap, no clickbait lies",
  "thumb_text": "2-4 bold ENGLISH/Hinglish punch words (Latin script)",
  "delivery-note": "each scene also gets \"delivery\": hook | calm | reveal | urgent (scene 1 = hook; the twist scene = reveal); and may use visual_mode \"map\" with \"map\": {{\"lat\": 0.0, \"lon\": 0.0, \"label\": \"हिन्दी\"}} when one specific place is the star (0-1 map scenes)",
  "payoff": "ONE declarative Hindi sentence that ANSWERS the hook's question",
  "meaning": "ONE Hindi sentence: why that answer matters to the viewer",
  "loop_bridge": "optional short fragment that flows into the hook on replay ('' if none)",
  "description": "1-2 lines, end with hashtags including #shorts",
  "tags": ["6-10 tags"],
  "scenes": [
    {{
      "n": 1,
      "title": "2-4 word label",
      "narration": "8-30 words",
      "visual_mode": "broll | ai_image | kinetic | stat | card | map | glass",
      "search_terms": ["concrete visual term", "alternative", "broader fallback"],
      "ai_prompt": "text-to-image prompt (only for ai_image, else empty)",
      "kinetic_text": "3-6 word punch phrase (only for kinetic, else empty)",
      "forbidden_visuals-note": "also return a top-level \"forbidden_visuals\" array: 3-6 ENGLISH phrases of footage that would break this premise (e.g. 'scuba diver', 'oxygen tank')",
      "stat": {{"value": 0, "suffix": "", "label": "", "max": null, "baseline": null, "bars": [{{"label": "short label", "value": 0}}]}},
      "card": {{"kicker": "category", "headline": "short headline", "body": "under 12 words"}},
      "glass": {{"kicker": "category", "headline": "short Hindi line", "body": "under 10 words", "value": null, "suffix": "", "label": "", "delta": null, "delta_direction": "up | down | flat", "location": "", "coordinates": "", "chapter": ""}}
    }}
  ]
}}

Shorts rules:
- SCENARIO LOCK (scientific integrity — highest priority): if the topic is a
  hypothetical with multiple interpretations (e.g. "oxygen disappears" could
  mean atmospheric O₂ gas vanishing OR every oxygen atom vanishing from water,
  rock and concrete), CHOOSE EXACTLY ONE interpretation in scene 1 and derive
  every consequence from that one scenario only. Never mix consequences across
  interpretations (atmospheric-O₂ loss does NOT turn concrete to dust). When
  it sharpens the hook, state the boundary explicitly ("सिर्फ हवा की ऑक्सीजन —
  10 सेकंड के लिए"). Honest consequences of the chosen scenario are dramatic
  enough.
- VISUAL VARIETY: each scene's search_terms must name a DIFFERENT concrete
  subject — no two consecutive scenes may depict the same subject (never two
  scenes of the same distressed person). The viewer sees a new image every
  ~3 seconds.
- {scfg.get('scenes_min', 4)}-{scfg.get('scenes_max', 6)} micro-scenes. ONE idea total.
  HARD CAP: ~{words} spoken words across the whole script — if over, cut
  adjectives and merge scenes. Shorter beats complete.
- Scene 1 = the hook: <= 12 words, the single most jolting fact/question.
  No greetings, no context, no "did you know".
- ENDING CONTRACT (critical — order is law): the final scene's narration is
  built payoff -> meaning -> loop_bridge, in that order.
  * payoff FIRST: a complete declarative sentence answering the hook. A
    question is NOT a payoff. A new topic is NOT a payoff.
  * meaning SECOND: one sentence of why it matters ("सीमा हमारी है, अंतरिक्ष
    की नहीं") — this is what the viewer takes away.
  * loop_bridge LAST and OPTIONAL: a fragment that grammatically flows into
    the hook line on replay. It comes AFTER the story is complete — a loop
    tease before the payoff is a broken video, not a loop.
  * BANNED as final words: "लेकिन...", "और अगर...", "तो?", "क्या होगा?",
    "...साबित करते हैं", "तो अगली बार", "इसीलिए" — any construction that
    leaves the sentence hanging. The video must never feel cut off.
- Exactly 1-2 "kinetic" scenes, 0-1 "stat", 0-{short_ai_max} "ai_image"
  (put an ai_image on the hook when the topic's strongest visual doesn't
  exist as stock), rest "broll".
- A stat may add max (ring gauge), baseline (before/after) or 2-4 bars. Keep a
  bare value/suffix/label for the original punchy big-number treatment.
- 0-1 "card" scene may replace a broll scene when a definition, warning or
  comparison communicates the idea faster. Keep all card text extremely short.
- 0-1 "glass" scene may replace a stat/card beat for the hook or payoff. Use
  only one focal number or one short fact; never stack multiple facts in it.
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
  * If narration names a real landmark, machine, animal or anatomical part,
    search_terms[0] MUST name that exact subject. If exact footage is unlikely,
    rewrite the narration generically instead of showing a misleading substitute.
- Every sentence must earn its half-second. Cut every filler word."""

    for attempt in range(3):
        try:
            script = _normalize(_parse_json(_llm(prompt, cfg, api_key)), 3)
            script["topic"] = topic
            script = _critique(script, cfg, api_key, "short", 3)
            _enforce_short_payoff(script)
            print(f"[script] SHORT '{script['title']}' — "
                  f"{[s['visual_mode'] for s in script['scenes']]}")
            return script
        except (KeyError, AssertionError, json.JSONDecodeError) as e:
            print(f"[script] invalid short JSON (attempt {attempt + 1}): {e}")
    raise RuntimeError("Could not obtain a valid short script after 3 attempts")



# Final constructions that leave a short feeling cut off mid-sentence.
_DANGLING_END = re.compile(
    r"(लेकिन|और अगर|अगर|तो|क्या होगा|जानने के लिए|इसीलिए|तो अगली बार)"
    r"[\s.…?!]*$")


def _enforce_short_payoff(script: dict) -> None:
    """Deterministic ending contract (fail-open): the last scene must close
    with payoff -> meaning -> loop_bridge. If the model left the final line
    dangling on a connective/question, rebuild it from the structured fields
    so the video never ends mid-thought."""
    scenes = script.get("scenes") or []
    if not scenes:
        return
    payoff = str(script.get("payoff") or "").strip()
    meaning = str(script.get("meaning") or "").strip()
    bridge = str(script.get("loop_bridge") or "").strip()
    last = scenes[-1]
    narration = str(last.get("narration") or "").strip()
    dangling = bool(_DANGLING_END.search(narration))
    has_payoff = bool(payoff) and payoff[:24] in narration
    if payoff and (dangling or not has_payoff):
        rebuilt = " ".join(x for x in (payoff, meaning, bridge) if x).strip()
        if rebuilt:
            print(f"[script] ending contract: rebuilt final scene "
                  f"({'dangling' if dangling else 'payoff missing'})")
            last["narration"] = rebuilt
    elif dangling:
        print("[script] WARNING: final line dangles and no payoff field — "
              "shipping as-is (fail-open)")


def log_topic_done(topic: str, done_file: str = "topics_done.txt") -> None:
    with open(done_file, "a", encoding="utf-8") as f:
        f.write(topic + "\n")
