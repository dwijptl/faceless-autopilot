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

import families as families_mod
import retention_lint
import topic_shape
import visual_beats as visual_beats_mod

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


_anthropic_available: list | None = None
ANTHROPIC_MODEL_USED = ""


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
            # the retention-engine schema (retention_plan + per-scene roles/
            # rewards/payloads) in Devanagari runs ~20-30k chars; 8000 tokens
            # truncated mid-JSON and every parse failed. Sonnet supports far
            # larger outputs — give the full script generous headroom.
            "max_tokens": 32000,
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
                global ANTHROPIC_MODEL_USED
                ANTHROPIC_MODEL_USED = model
                return r.json()["content"][0]["text"]
            except requests.RequestException as e:
                last_err = str(e)
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Anthropic call failed on all models: {last_err}")


PROVIDER_USED = ""  # which provider wrote the last CREATIVE call (see _llm)


def _llm(prompt: str, cfg: dict, gemini_key: str) -> str:
    """Route to Claude when a key exists (better scripts), else Gemini.
    Any Claude failure silently falls back to Gemini — runs never block."""
    global PROVIDER_USED
    ak = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    provider = str(cfg["llm"].get("provider", "auto")).lower()
    if ak and provider in ("auto", "anthropic"):
        try:
            out = _anthropic(prompt, cfg, ak)
            PROVIDER_USED = f"anthropic:{ANTHROPIC_MODEL_USED or '?'}"
            return out
        except Exception as e:
            print(f"[script] anthropic failed ({e}) -> gemini fallback")
    PROVIDER_USED = f"gemini:{cfg['llm'].get('model', '?')}"
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
    # Prefer the pace MEASURED from previous runs' actual TTS (run.py sets
    # channel.wpm_measured from calibration.json) — the static guess produced
    # 4:08 videos against 6:15 targets. Falls back to the configured value.
    measured = cfg["channel"].get("wpm_measured")
    if measured:
        return int(measured)
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
- Register: CASUAL spoken Hindi (Hindustani) — the Hindi a 22-year-old in
  Delhi uses with a friend, NOT शुद्ध/साहित्यिक/textbook Hindi. The viewer
  should never hit a word they'd have to look up.
- USE English loanwords in Devanagari wherever urban speakers naturally do:
  स्पेस, ग्रैविटी, यूनिवर्स, गैलेक्सी, एनर्जी, प्रेशर, टेम्परेचर, स्पीड,
  ऑर्बिट, एस्ट्रोनॉट, साइंटिस्ट, ब्लैक होल, लाइट, सिग्नल, मशीन.
- BANNED textbook words → use the everyday word instead:
  गुरुत्वाकर्षण→ग्रैविटी · आकाशगंगा→गैलेक्सी · परिक्रमा→ऑर्बिट/चक्कर ·
  खगोलशास्त्री→साइंटिस्ट · अंतरिक्ष यात्री→एस्ट्रोनॉट · ऊष्मा→गर्मी ·
  दाब→प्रेशर · प्रकाश वर्ष→लाइट ईयर · उत्सर्जित→बाहर फेंकता है ·
  संकुचित→सिकुड़ता है · अभिकल्पना→आइडिया · अनुनाद→रेज़ोनेंस.
  (ब्रह्मांड and वैज्ञानिक are fine — common speech.)
- SELF-TEST for every line: would it sound natural in a WhatsApp voice note
  to a friend? If any word feels like a school textbook, replace it. Never
  write full English sentences — mix at the word level only.
- NUMBERS in narration: Arabic numerals; anything longer than 4 digits gets
  commas (10,000 not 10000) so the voice reads it as one number.
- HARD RULE: search_terms and ai_prompt stay in ENGLISH — stock libraries
  and image models are indexed in English.
- tags: mostly Hindi, plus 2-4 English tags for search reach.
"""


def _style_rules() -> str:
    return """
WRITING STYLE — the narration must sound like a PERSON, not a language model.
Read every line aloud in your head; if a Hindi speaker could not say it
naturally in one breath to a friend, rewrite it.

BANNED (any language) — these instantly mark a script as AI:
- Stock openers: "have you ever wondered", "did you know", "imagine a world",
  "let's dive in", "क्या आप जानते हैं", "आइए जानते हैं", "कल्पना कीजिए" as an
  opener, "चलिए शुरू करते हैं".
- Stock transitions: "in conclusion", "निष्कर्ष", "अब बात करते हैं", "गौर करने
  वाली बात यह है", "यह ध्यान रखना ज़रूरी है", "दिलचस्प बात यह है कि" (more than
  once), robotic enumeration ("पहला... दूसरा... तीसरा...").
- Symmetric AI sentence templates repeated across scenes: "यह न सिर्फ X बल्कि
  Y भी", "X ही नहीं, Y भी", every scene starting with "लेकिन".
- Empty intensity: "हैरान कर देने वाला", "चौंकाने वाला" without a concrete
  fact attached in the SAME sentence.

HOW A HUMAN NARRATOR ACTUALLY SOUNDS (write like this):
- Rhythm is uneven ON PURPOSE: a 3-word punch. Then a longer flowing sentence
  that carries the viewer somewhere. Then a fragment. फिर एक सवाल।
- The viewer is IN the story — address them as the traveller, repeatedly:
  "अब आप 4,000 मीटर नीचे हैं। आपकी छाती पर 400 हाथियों का वज़न है।"
  Use "आप" naturally several times per scene, not once per video.
- One breath before the big moment: a short quiet line right before a reveal
  ("और फिर... सिग्नल बदल गया।").
- Small human asides are allowed once or twice per video ("सच कहूं तो मुझे भी
  यहीं यकीन नहीं हुआ था").
- Numbers speak like a person: "करीब 92 बार" not "लगभग 92.0 बार का दबाव
  अनुभव होता है". Attach every big number to ONE thing the viewer can feel.
- Real scientists, probes and missions may be NAMED in narration as
  characters (कहानी के किरदार) — a named person makes evidence human. Never
  show them via stock lookalikes; visuals stay environment/archive/AI.
- Every scene ends on a concrete image, place, number or question — never an
  abstraction or a summary.
- Specificity beats breadth: one vivid, named fact per scene instead of three
  vague claims. Voice: confident, a little amused, zero lecture tone.
"""


def _ai_max(cfg: dict) -> int:
    """AI-image budget per video — richer when a FLUX (fal.ai) key is set."""
    aicfg = cfg.get("ai_images", {})
    if os.environ.get("FAL_KEY", "").strip():
        return int(aicfg.get("max_per_video_flux",
                             max(int(aicfg.get("max_per_video", 2)), 4)))
    return int(aicfg.get("max_per_video", 2))


VALID_MODES = ("broll", "ai_image", "kinetic", "stat", "card", "map", "glass",
               "scale", "causal", "evidence")


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


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_compare(raw) -> dict:
    """Scale anchor: one unfamiliar number against one familiar unit."""
    data = raw if isinstance(raw, dict) else {}
    value = _num_or_none(data.get("value"))
    anchor = _num_or_none(data.get("anchor_value", data.get("anchorValue")))
    if value is None or anchor is None or anchor <= 0:
        return {}
    return {"value": value,
            "unit": str(data.get("unit", ""))[:16],
            "label": str(data.get("label", ""))[:60],
            "anchorLabel": str(data.get("anchor_label",
                                        data.get("anchorLabel", "")))[:40],
            "anchorValue": anchor,
            "anchorUnit": str(data.get("anchor_unit",
                                       data.get("anchorUnit", "")))[:16]}


def _normalize_causal(raw) -> dict:
    """Mechanism chain A -> B -> C with 2-6 short steps."""
    data = raw if isinstance(raw, dict) else {}
    steps = [str(s).strip()[:60] for s in (data.get("steps") or [])
             if str(s).strip()][:6]
    if len(steps) < 2:
        return {}
    return {"headline": str(data.get("headline", ""))[:80], "steps": steps}


def _normalize_evidence(raw) -> dict:
    """Named-source frame with an honest confidence tag."""
    data = raw if isinstance(raw, dict) else {}
    source = str(data.get("source", "")).strip()[:90]
    if not source:
        return {}
    conf = str(data.get("confidence", "")).strip()
    if conf not in ("पुष्टि", "अनुमान", "विवादित"):
        conf = ""
    return {"kicker": str(data.get("kicker", ""))[:24],
            "headline": str(data.get("headline", ""))[:80],
            "source": source,
            "date": str(data.get("date", ""))[:24],
            "confidence": conf}


def _normalize_retention_plan(raw, n_scenes: int) -> dict:
    """Bound the machine-readable story contract (see retention_lint.py)."""
    data = raw if isinstance(raw, dict) else {}
    loops = []
    for lp in (data.get("open_loops") or [])[:4]:
        if not isinstance(lp, dict) or not str(lp.get("question", "")).strip():
            continue
        loops.append({
            "question": str(lp.get("question", ""))[:140],
            "opens_scene": _int_or_none(lp.get("opens_scene")),
            "partial_scene": _int_or_none(lp.get("partial_scene")),
            "closes_scene": _int_or_none(lp.get("closes_scene")),
        })
    reveal_scene = _int_or_none(data.get("main_reveal_scene"))
    if reveal_scene is not None and not 1 <= reveal_scene <= n_scenes:
        reveal_scene = None
    return {
        "core_question": str(data.get("core_question", ""))[:160],
        "viewer_assumption": str(data.get("viewer_assumption", ""))[:160],
        "first_reversal": str(data.get("first_reversal", ""))[:160],
        "main_reveal": str(data.get("main_reveal", ""))[:200],
        "main_reveal_scene": reveal_scene,
        "open_loops": loops,
    }


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
        s["compare"] = _normalize_compare(s.get("compare"))
        s["causal"] = _normalize_causal(s.get("causal"))
        s["evidence"] = _normalize_evidence(s.get("evidence"))
        # a mode whose payload failed validation degrades to plain footage
        if s["visual_mode"] == "scale" and not s["compare"]:
            s["visual_mode"] = "broll"
        if s["visual_mode"] == "causal" and not s["causal"]:
            s["visual_mode"] = "broll"
        if s["visual_mode"] == "evidence" and not s["evidence"]:
            s["visual_mode"] = "broll"
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
        nrole = str(s.get("narrative_role", "")).lower().strip()
        s["narrative_role"] = nrole if nrole in retention_lint.ROLES else ""
        reward = s.get("reward") if isinstance(s.get("reward"), dict) else {}
        strength = _num_or_none(reward.get("strength"))
        s["reward"] = {"type": str(reward.get("type", ""))[:24],
                       "strength": (min(max(strength, 0.0), 1.0)
                                    if strength is not None else 0.0)}
        s["question_out"] = str(s.get("question_out", ""))[:140]
    script["scenes"][0]["delivery"] = "hook"
    if not script["scenes"][0]["narrative_role"]:
        script["scenes"][0]["narrative_role"] = "hook"
    script["retention_plan"] = _normalize_retention_plan(
        script.get("retention_plan"), len(script["scenes"]))
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
    fmt = ("a 40-55 second vertical Short (hook <= 12 words; full PAYOFF, "
           "a meaningful close, and no dangling final fragment)" if kind == "short"
           else "a 6-minute documentary (30s hook, mid-video re-hook, payoff ending)")
    prompt = f"""You are a ruthless retention editor for a Hindi faceless
YouTube channel. Below is a draft script for {fmt}.

Grade every scene 1-10 on ALL of:
- hook strength and specificity (named places and numbers a viewer can picture);
- curiosity pull into the NEXT scene (would a viewer predict the next line?
  if yes, the scene fails — break the prediction);
- HUMAN VOICE: read the narration aloud in your head. AI tells that force a
  rewrite: uniform sentence rhythm across scenes, stock transitions ("अब बात
  करते हैं", "गौर करने वाली बात"), symmetric templates ("X ही नहीं, Y भी")
  repeated, empty intensity words without a concrete fact, zero direct
  address. A human narrator talks TO the viewer ("आप"), varies rhythm on
  purpose, and lands each scene on something you can see or feel;
- emotion: the strongest fact of the scene must produce a nameable feeling
  (awe / fear / scale / disbelief) — "interesting" is not a feeling.

REWRITE any scene scoring below 8 — sharper verbs, more concrete nouns,
tighter sentences, zero filler, natural spoken Hindi. Keep the same JSON
schema, scene count, visual_mode, search_terms, narrative_role and
retention_plan (you may improve narration, titles, kinetic_text, delivery,
question_out, reward and thumb_text).
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
                          "compare", "causal", "evidence",
                          "must_show", "visual_role", "narrative_role"):
                after[field] = before.get(field, after.get(field, {}))
            if not str(after.get("question_out", "")).strip():
                after["question_out"] = before.get("question_out", "")
        for field in ("premise", "changing_variable", "hero_prompt",
                      "forbidden_visuals", "title_options", "thumb_options",
                      "thumb_headline", "thumb_question", "next_tease_topic"):
            if not revised.get(field):
                revised[field] = script.get(field, revised.get(field))
        if not (revised.get("retention_plan") or {}).get("core_question"):
            revised["retention_plan"] = script.get("retention_plan",
                                                   revised.get("retention_plan"))
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



# ── Variety engine (YouTube inauthentic-content policy, bucket 1) ────────
# "Content made with a template with little to no variation across videos"
# is ineligible for monetization. A pipeline naturally collapses into one
# winning formula, so variety is ENFORCED here rather than hoped for:
# the title FORM and the topic FAMILY both rotate deterministically, and a
# deterministic check rejects a title that reuses the previous frame.

TITLE_FORMS = [
    ("question", "a direct question the viewer wants answered "
                 "(\u0915\u094d\u092f\u093e \u0939\u094b\u0917\u093e / \u0915\u094d\u092f\u094b\u0902)"),
    ("claim", "a flat declarative claim that sounds impossible but is true "
              "\u2014 NO question mark anywhere in the title"),
    ("number", "lead with one shocking number as the first characters"),
    ("contradiction", "two facts in tension, joined by \u0932\u0947\u0915\u093f\u0928/\u092b\u093f\u0930 \u092d\u0940"),
    ("scene", "drop the viewer into a moment, present tense, no question"),
    ("verdict", "state the outcome up front, then who/what it happens to"),
]

# Topic families — no single family may dominate the channel.
TOPIC_FAMILIES = {
    "survival_timeline": ["\u0936\u0930\u0940\u0930", "\u092e\u093f\u0928\u091f", "\u0918\u0902\u091f", "\u0938\u0947\u0915\u0902\u0921",
                          "body", "survive", "minute", "hour"],
    "vanishing_whatif": ["\u0905\u0917\u0930", "\u0917\u093e\u092f\u092c", "what if", "vanish", "disappear"],
    "mystery_investigation": ["\u0930\u0939\u0938\u094d\u092f", "\u0916\u094b\u091c", "mystery", "discover", "unexplained"],
    "scale_comparison": ["\u0924\u0941\u0932\u0928", "\u0917\u0941\u0928\u093e", "\u092c\u0921\u093c\u093e", "scale", "compare", "size"],
    "disagreement": ["\u0935\u0948\u091c\u094d\u091e\u093e\u0928\u093f\u0915", "\u092c\u0939\u0938", "disagree", "debate", "theory"],
}
FAMILY_CAP = 0.40   # no family may exceed this share of recent output


# Descent/extreme-place topics are the channel's proven core, and its two
# best-performing titles were claim/number forms (Kola: rank-1 day-one reach;
# Mariana: 13.6% CTR). For that family, bias the rotation toward those two
# forms — alternating so consecutive descent videos still differ — while
# every other family keeps the full 6-form rotation.
# Data: 2026-07 window — docs/CHANNEL_OPTIMIZATION_PLAN.md (A2).
DESCENT_HINTS = ("मीटर", "किमी", "नीचे", "गहरा", "गहरे", "गहराई", "सतह",
                 "ट्रेंच", "meter", "metre", "deep", "depth", "descent",
                 "borehole", "trench", "beneath")
_DESCENT_FORMS = ("claim", "number")


def _is_descent_topic(topic: str) -> bool:
    low = str(topic).lower()
    return any(h in low for h in DESCENT_HINTS)


def _title_form(done_count: int, topic: str = "") -> tuple:
    form = TITLE_FORMS[done_count % len(TITLE_FORMS)]
    if _is_descent_topic(topic) and form[0] not in _DESCENT_FORMS:
        form = TITLE_FORMS[2] if done_count % 2 else TITLE_FORMS[1]
    return form


def _frame_signature(title: str) -> str:
    """Structural fingerprint of a title: the trailing phrase with all digits
    and Latin words stripped. Two titles that differ only in their nouns and
    numbers collapse to the same signature."""
    t = re.sub(r"[0-9\u0966-\u096F,.\u2212\-\u00b0%]+", "", str(title))
    t = re.sub(r"[A-Za-z]+", "", t)
    words = [w for w in t.replace("?", " ").replace(":", " ").split() if w]
    return " ".join(words[-4:]).strip()


def _family_of(topic: str) -> str:
    low = str(topic).lower()
    for fam, keys in TOPIC_FAMILIES.items():
        if any(k.lower() in low for k in keys):
            return fam
    return "other"


def _overused_families(done: list, window: int = 10) -> list:
    recent = [t for t in done[-window:] if t]
    if len(recent) < 4:
        return []
    counts = {}
    for t in recent:
        fam = _family_of(t)
        counts[fam] = counts.get(fam, 0) + 1
    return [f for f, c in counts.items()
            if f != "other" and c / len(recent) > FAMILY_CAP]


def _variety_rules(done: list, done_count: int, topic: str = "") -> str:
    """Prompt block that forces this video away from the last one's shape."""
    form, how = _title_form(done_count, topic)
    recent_sigs = [_frame_signature(t) for t in done[-3:] if t]
    banned = "\n".join(f'  - "{s}"' for s in recent_sigs if s)
    over = _overused_families(done)
    fam_note = ""
    if over:
        fam_note = (f"\nOVER-USED FAMILIES (do NOT write another one of these): "
                    f"{', '.join(over)}. Pick a DIFFERENT angle: an "
                    f"investigation, a scale comparison, a scientific "
                    f"disagreement, or a single-object deep dive.\n")
    return f"""
TITLE VARIETY (mandatory \u2014 the channel must not look templated):
- This video's title FORM is **{form}**: {how}.
- The title must NOT end with the same phrase-shape as the last videos:
{banned or "  (no history yet)"}
  Reusing a trailing frame like "...\u0915\u0947 \u0938\u093e\u0925 \u0915\u094d\u092f\u093e \u0939\u094b\u0917\u093e?" across videos is BANNED.
- Vary sentence length and rhythm from the previous title.
{fam_note}"""


def _score_template(shape: str) -> str:
    """The "scores" object literal for pick_topic's JSON contract, matching
    whichever rubric this run is using."""
    return "{" + ", ".join(f'"{k}": 0' for k in topic_shape.score_keys(shape)) + "}"


def _read_done(done_file: str) -> tuple:
    """(topics, last NEXT: marker) from a topics_done file. Missing file is
    not an error — a fresh channel has no history."""
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
    return done, tease


def pick_topic(cfg: dict, api_key: str, done_file: str = "topics_done.txt",
               learnings: str = "", shape: str = "any",
               also_done: list | None = None, max_seconds: float = 90) -> str:
    """Pick the next topic.

    `shape` routes the candidate rubric (see topic_shape): "single_claim" for
    Shorts, "any"/"checkpoint_journey" for long-form. Shorts and long-form used
    to share the VISUAL JOURNEY TEST, which rewards "6+ escalating milestones"
    — a promise a 45-second Short cannot keep, and the measured cause of the
    channel's sub-40% Shorts retention.

    `also_done` is the OTHER format's topic history. The two topics_done files
    are separate namespaces, so before this parameter existed a Short could
    duplicate a long-form topic — which is exactly what happened on 2026-07-22
    and 07-23 (the same Earth-signal topic shipped as an 83s Short and a 399s
    long-form one day apart; the Short did 78 views, the long-form did 4).
    """
    forced = os.environ.get("FORCED_TOPIC", "").strip()
    if forced:
        print(f"[script] using forced topic: {forced}")
        return forced

    done, tease = _read_done(done_file)
    cross = [t for t in (also_done or []) if t]
    if cross:
        print(f"[script] cross-format dedupe: {len(cross)} topic(s) from the "
              f"other format are off-limits too")
    # honor a manual NEXT: override the owner added to topics_done.txt
    if tease and tease not in done:
        if shape != "any" and topic_shape.classify(tease) != shape:
            print(f"[script] WARNING: manual NEXT: override is "
                  f"{topic_shape.explain(tease)} but this run wants {shape} — "
                  f"honoring the override anyway (owner intent wins)")
        print(f"[script] honoring manual NEXT: override: {tease}")
        return tease

    learn_block = (f"\nWHAT HAS WORKED ON THIS CHANNEL (analytics digest):\n{learnings}\n"
                   if learnings else "")
    lang_note = ("\nWrite the topic itself in Hindi (Devanagari script).\n"
                 if _is_hindi(cfg) else "")
    over = _overused_families(done)
    _family_block = ""
    if over:
        _family_block = (
            f"\nTOPIC FAMILY BALANCE \u2014 the channel has over-used: "
            f"{', '.join(over)}. At least TWO of your three candidates must "
            f"come from a DIFFERENT family (investigation / scale comparison / "
            f"scientific disagreement / single-object deep dive). Repeating one "
            f"formula makes the channel ineligible for monetization.\n")
        print(f"[script] variety: steering away from over-used families: {over}")
    prompt = f"""You are the content strategist for a faceless YouTube channel.

NICHE: {cfg['channel']['niche']}
AUDIENCE: {cfg['channel']['audience']}
{learn_block}
Already-covered topics (NEVER repeat or closely paraphrase these, in any
language):
{json.dumps((done + cross)[-100:], indent=0, ensure_ascii=False)}

{_family_block}
Invent THREE candidate video topics with strong curiosity-gap appeal that can
be illustrated with stock footage of landscapes, cities, nature, aerials and
oceans plus occasional AI-generated stills (no specific people, no events
needing news footage, nothing requiring licensed material). If the analytics
digest above shows a topic family performing well, lean into that family
without repeating covered topics.

{topic_shape.rubric(shape, max_seconds)}
REJECT any candidate that is interesting but cannot be shown truthfully
(feasibility <= 4) or whose central claim cannot be verified
(source_confidence <= 4) — an accurate, filmable topic beats a viral,
unfilmable one.
{lang_note}
Return JSON exactly:
{{"candidates": [{{"topic": "...", "scores": {_score_template(shape)},
"total": 0}}],
"topic": "<the candidate with the highest total>"}}"""

    def _candidates(parsed) -> list:
        out = []
        head = str(parsed.get("topic") or "").strip()
        if head:
            out.append(head)
        for c in sorted(parsed.get("candidates") or [],
                        key=lambda c: -float(c.get("total", 0) or 0)):
            t = str(c.get("topic") or "").strip()
            if t and t not in out:
                out.append(t)
        return out

    last_err, reject_note = None, ""
    for attempt in range(3):
        try:
            parsed = _parse_json(_llm(prompt + reject_note, cfg, api_key))
            cands = _candidates(parsed)
            if not cands:
                raise KeyError("topic")
            if shape == "any":
                print(f"[script] auto-picked topic: {cands[0]}")
                return cands[0]
            # Shape gate: take the best candidate that actually fits the format.
            # The model is told the rule; this verifies it, because a rubric in
            # a prompt is a request and a check is a guarantee.
            for t in cands:
                if topic_shape.classify(t) == shape and (
                        shape != topic_shape.SINGLE_CLAIM
                        or topic_shape.fits_in(t, max_seconds)):
                    print(f"[script] auto-picked topic ({shape}): {t}")
                    print(f"[script]   shape check: {topic_shape.explain(t)}")
                    return t
            worst = cands[0]
            print(f"[script] shape reject (attempt {attempt + 1}): all "
                  f"{len(cands)} candidates are wrong-shaped for {shape} — "
                  f"e.g. '{worst[:50]}' is {topic_shape.explain(worst)}")
            reject_note = f"""

REJECTED — your previous candidates all failed the shape gate:
{json.dumps(cands, ensure_ascii=False)}
Each promises checkpoints or stages that cannot be paid off in
{int(max_seconds)} seconds. Propose topics that resolve in ONE claim: no
"हर N मिनट/मीटर", no "X से Y तक", no stage-by-stage timeline."""
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            last_err = e
            print(f"[script] bad topic JSON (attempt {attempt + 1}): {e}")
    raise RuntimeError(f"Could not pick a {shape} topic after 3 attempts: "
                       f"{last_err or 'every candidate failed the shape gate'}")


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
    director_on = families_mod.enabled(cfg)
    director_fields = ""
    director_rules = ""
    if director_on:
        director_fields = """,
  "family":"ONE narrative-intent family key from the menu below — what this beat DOES in the story",
  "intensity":1,
  "graphic":{"kind":"timeline|scale|branch|chart|cutaway","title":"short ENGLISH title","unit":"km","items":[{"label":"short label","value":0}]}"""
        director_rules = f"""
NARRATIVE-INTENT FAMILIES (pick by story function, never by subject):
{families_mod.prompt_hint_lines()}
- "family" is REQUIRED per beat; "intensity" is 1 (calm) to 3 (peak moment),
  at most one 3 per scene.
- "graphic" ONLY for beats whose family is diagram-like (timeline_advance,
  scale_comparison, hypothesis_branch, data_story, cause_chain, measurement,
  mechanism_cutaway, penetrate_layers, countdown): give 2-6 items with short
  ENGLISH labels and real numeric values from the narration. Omit "graphic"
  for every other beat.
- Families in the hypothesis cluster mark competing explanations; use
  hypothesis_branch exactly where the narration lists multiple theories.
- The final beat of the last scene should be lingering_question, legacy or
  haunting_echo — never a random subject."""
    prompt = f"""You are the visual editor of a premium factual-mystery documentary.
Turn the FINAL Hindi narration below into a sentence-level visual beat sheet.
{contract}

Return ONLY JSON:
{{"scenes":[{{"n":1,"visual_beats":[{{
  "cue":"an EXACT 3-8 word verbatim phrase from the Hindi narration where this visual starts",
  "search_terms":["one exact concrete ENGLISH Pexels query","one fallback query"],
  "purpose":"what the viewer must understand from this visual"{director_fields}
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
{director_rules}

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


def _reconcile_display_numbers(script: dict, report: dict, cfg: dict) -> dict:
    """Deterministic last resort for claim_display_mismatch (C9), applied
    AFTER the LLM repair loop and BEFORE TTS: a displayed number the
    narration never speaks is removed from the screen. Screen and voice must
    agree — when the repair could not make the voice say the number, the
    screen stops showing it. Milestones simply hide for that scene; a
    stat/compare scene whose narration has no number falls back to broll
    (this runs pre-assets, so the fallback renders normally). Fail-open."""
    codes = {v.get("code") for v in report.get("violations", [])}
    if "claim_display_mismatch" not in codes:
        return report
    fixed = []
    for i, s in enumerate(script.get("scenes", [])):
        narration = str(s.get("narration", ""))
        for field in ("stat", "compare", "milestone"):
            payload = s.get(field) or {}
            value = payload.get("value")
            variants = retention_lint._num_variants(value)
            try:
                if not variants or float(value) == 0:
                    continue
            except (TypeError, ValueError):
                continue
            if any(v in narration for v in variants):
                continue
            s[field] = {}
            if field in ("stat", "compare") and s.get("visual_mode") == field:
                s["visual_mode"] = "broll"
            fixed.append(f"scene {i + 1} {field}={value:g}")
    if fixed:
        print("[retention] reconciled unspoken display numbers (screen now "
              "agrees with voice): " + "; ".join(fixed))
        report = retention_lint.lint(script, cfg)
    return report


def _retention_pass(script: dict, cfg: dict, api_key: str, topic: str) -> dict:
    """Deterministic story audit + bounded repair loop (pre-TTS, so repairs
    are free). Fail-open: the final report travels on the script and run.py
    decides whether a failure drafts or blocks the release."""
    rcfg = cfg.get("retention", {})
    if not rcfg.get("enabled", True):
        return script
    report = retention_lint.lint(script, cfg)
    revisions = int(rcfg.get("max_revisions", 2))
    for attempt in range(revisions):
        if report["passed"]:
            break
        print(f"[retention] {len(report['violations'])} violation(s) — "
              f"repair pass {attempt + 1}/{revisions}: "
              + ", ".join(sorted({v["code"] for v in report["violations"]})))
        try:
            fixed = _normalize(_parse_json(_llm(
                retention_lint.repair_prompt(script, report, cfg,
                                             _lang_rules(cfg)),
                cfg, api_key)), 4)
            # keep visual payloads unless the repair legitimately changed them
            # (engine_flat repairs MUST rewrite milestones, so no blanket copy)
            for before, after in zip(script["scenes"], fixed["scenes"]):
                for field in ("stat", "card", "glass", "map",
                              "compare", "causal", "evidence"):
                    if not after.get(field) and before.get(field):
                        after[field] = before[field]
            for field in ("premise", "changing_variable", "hero_prompt",
                          "forbidden_visuals", "title_options", "thumb_options",
                          "thumb_headline", "thumb_question",
                          "next_tease_topic", "word_budget"):
                if not fixed.get(field):
                    fixed[field] = script.get(field)
            fixed["topic"] = topic
            script = fixed
        except Exception as exc:
            print(f"[retention] repair pass failed ({exc}) — keeping draft")
            break
        report = retention_lint.lint(script, cfg)
    report = _reconcile_display_numbers(script, report, cfg)
    status = "PASSED" if report["passed"] else "FAILED"
    print(f"[retention] story audit {status} — "
          f"reveal at {report['metrics'].get('reveal_fraction')}, "
          f"{report['metrics'].get('open_loops', 0)} loops, "
          f"{len(report['violations'])} open violation(s)")
    script["retention_report"] = report
    return script


def _done_titles(done_file: str) -> list:
    """Titles/topics already shipped — drives title-form + family rotation."""
    out = []
    try:
        with open(done_file, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#") and not ln.startswith("NEXT:"):
                    out.append(ln)
    except OSError:
        pass
    return out


def _enforce_title_variety(script: dict, done: list) -> None:
    """Deterministic backstop for the prompt rule: if the new title reuses a
    trailing frame from the last 3 videos, promote a title_option that does
    not. Fail-open — never blocks a render."""
    recent = {_frame_signature(t) for t in done[-3:] if t}
    title = str(script.get("title", ""))
    if not recent or _frame_signature(title) not in recent:
        return
    for alt in (script.get("title_options") or []):
        if _frame_signature(alt) not in recent:
            print(f"[script] title variety: '{title[:40]}...' reused a recent "
                  f"frame -> swapped to '{alt[:40]}...'")
            script["title_options"] = [title] + [
                t for t in script["title_options"] if t != alt]
            script["title"] = alt
            return
    print(f"[script] WARNING: title reuses a recent frame and no alternate "
          f"differs \u2014 shipping as-is: {title[:60]}")


def _skeleton_block(done_count: int) -> tuple:
    """(name, prompt block) for this episode's narrative shape."""
    name = retention_lint.skeleton_for(done_count)
    s = retention_lint.SKELETONS[name]
    lo, hi = s["reveal_window"]
    roles = ", ".join(f"'{r}'" for r in s["must_include"])
    return name, f"""
NARRATIVE SHAPE for THIS episode: **{name}** — {s['note']}.
- The main reveal must land between {lo:.0%} and {hi:.0%} of the script.
- At least one scene must carry narrative_role {roles}.
- Do NOT default to the build-up-then-reveal shape unless it is named above;
  the channel rotates shapes so consecutive videos are structurally different.
"""


def generate_script(cfg: dict, topic: str, api_key: str, learnings: str = "",
                    done: list | None = None) -> dict:
    v = cfg["video"]
    done = done if done is not None else []
    skel_name, skel_block = _skeleton_block(len(done))
    wpm = _wpm(cfg)
    # ADAPTIVE long-form length (mirrors the Shorts band): the story decides
    # its natural end inside [min_minutes, max_minutes] — a mystery that
    # resolves at 15 min is not padded to 20, and a documentary that needs
    # 20 is not truncated. Falls back to fixed target_minutes if no band set.
    t_min = float(v.get("min_minutes", v["target_minutes"]))
    t_max = float(v.get("max_minutes", v["target_minutes"]))
    min_words = int(t_min * wpm)
    max_words = int(t_max * wpm)
    words = (min_words + max_words) // 2  # planning midpoint
    ai_max = _ai_max(cfg)
    learn_block = (f"\nCHANNEL LEARNINGS — apply these to hook style, pacing, and "
                   f"thumbnail text:\n{learnings}\n" if learnings else "")
    prompt = f"""You are a scriptwriter for a faceless YouTube channel
(voiceover + b-roll + motion graphics + captions, no on-camera host).

TOPIC: {topic}
TARGET: ADAPTIVE — the story decides its own natural length between
{t_min:g} and {t_max:g} minutes ({min_words}-{max_words} spoken words at
{wpm} wpm). End the video exactly where the mystery is fully resolved and
the documentary promise feels satisfied — never pad toward the ceiling,
never truncate a payoff to fit.
HARD RANGE: {min_words}-{max_words} spoken words across all scenes. Under
{min_words} produces a video shorter than promised; count your words before
returning and expand thin scenes with concrete material (never filler).
TONE: {cfg['channel']['tone']}
AUDIENCE: {cfg['channel']['audience']}
{learn_block}{_variety_rules(done, len(done), topic)}{skel_block}{_lang_rules(cfg)}{_style_rules()}
Write a scene-segmented script and return ONLY valid JSON with this exact shape:
{{
  "title": "click-worthy but honest YouTube title, <= 70 chars",
  "title_options": ["5 alternative Hindi titles, strongest first: one conservative, one high-curiosity, one number-driven among them"],
  "thumb_text": "2-4 bold ENGLISH/Hinglish punch words for the thumbnail (Latin script), ONE number mandatory (e.g. '12262 METERS DOWN')",
  "thumb_headline": "4-7 word DRAMATIC Hindi headline (Devanagari) — the emotional hook of the thumbnail, high intensity but 100% provable by the video (e.g. 'मारियाना ट्रेंच का खूनी सच!'); never a fabricated claim",
  "thumb_question": "3-5 word Hindi curiosity question for a small thumbnail annotation (e.g. 'शरीर का क्या होगा?'); empty string if none fits",
  "thumb_prompt": "ENGLISH text-to-image prompt for the thumbnail. NON-NEGOTIABLE: ONE dramatic subject FILLING 50-70% of the frame, strong rim light separating it clearly from the background, at least one vivid color accent; mid-dark background WITH visible depth — NEVER a mostly-black or murky image (it must read instantly at 160px feed size); keep the bottom third relatively empty for the title text",
  "thumb_options": [{{"text": "2-4 Latin punch words", "concept": "one-line alternative visual idea"}}, {{"text": "...", "concept": "..."}}, {{"text": "...", "concept": "..."}}],
  "premise": "ONE Hindi sentence: the impossible rule / continuous journey of this episode",
  "changing_variable": {{"label": "SHORT ENGLISH metric the viewer watches change (DEPTH, SPEED, TIME, TEMP, SIZE)", "unit": "km"}},
  "hero_prompt": "ENGLISH text-to-image prompt for the episode's recurring HERO subject — one person/object/place the video returns to as conditions change: subject + setting + light + camera angle",
  "forbidden_visuals": ["3-6 short ENGLISH phrases describing footage that would BREAK the premise and must never appear (e.g. for an unprotected-human deep-sea premise: 'scuba diver', 'diving suit', 'oxygen tank', 'snorkeler')"],
  "retention_plan": {{
    "core_question": "the ONE Hindi question the whole video exists to answer — the title's promise, sharpened",
    "viewer_assumption": "what the target viewer already believes about this topic (Hindi)",
    "first_reversal": "one Hindi line: the moment that assumption breaks",
    "main_reveal": "the single strongest answer/fact, held for the climax (Hindi) — the exact content of the main_reveal scene",
    "main_reveal_scene": 0,
    "open_loops": [{{"question": "a Hindi question the viewer is left holding", "opens_scene": 1, "partial_scene": 4, "closes_scene": 7}}]
  }},
  "description": "2-3 sentences in HINDI (Devanagari) — line 1 restates the hook as a question a viewer would ask, line 2-3 tease the payoff WITHOUT spoiling it. Name the episode's REAL anchor entity (place/machine/mission, e.g. 'कोला सुपरडीप बोरहोल') once — recommendations key on entities. No hashtags here (the pipeline appends them).",
  "tags": ["8-12 tags a HINDI-SPEAKING viewer in India would actually type. At least 6 in Devanagari (e.g. 'मंगल ग्रह', 'ब्रह्मांड के रहस्य'), 2-3 Hinglish in Latin script (e.g. 'mangal grah', 'space hindi'), rest English topic terms. Include 2-3 tags naming the episode's REAL anchor entity in BOTH scripts (e.g. 'Kola Superdeep Borehole', 'कोला सुपरडीप'). No generic single words like 'science'."],
  "scenes": [
    {{
      "n": 1,
      "title": "3-6 word scene title",
      "narration": "60-150 words of spoken narration",
      "visual_mode": "broll | ai_image | kinetic | stat | card | map | glass | scale | causal | evidence",
      "visual_role": "experience | explanation | measurement",
      "narrative_role": "hook | question | context | discovery | explanation | comparison | reversal | evidence | escalation | partial_answer | mini_reveal | main_reveal | implication | conclusion | next_curiosity",
      "reward": {{"type": "fact | comparison | visual_reveal | partial_answer | contradiction | consequence | scale | evidence", "strength": 0.7}},
      "question_out": "the Hindi question this scene leaves OPEN that pulls the viewer into the next scene ('' only for the final scene)",
      "delivery": "hook | calm | reveal | urgent",
      "must_show": ["1-2 short ENGLISH phrases naming what MUST be visible on screen for this scene's narration to be true"],
      "milestone": {{"value": 0, "label": "optional ENGLISH override of the metric label", "unit": "km"}},
      "search_terms": ["stock video search term", "alternative term", "broader fallback term"],
      "ai_prompt": "detailed text-to-image prompt (only when visual_mode is ai_image, else empty string)",
      "kinetic_text": "3-6 word punch phrase (only when visual_mode is kinetic, else empty string)",
      "stat": {{"value": 0, "suffix": "", "label": "", "max": null, "baseline": null, "bars": [{{"label": "short label", "value": 0}}]}},
      "card": {{"kicker": "short category", "headline": "5-10 word headline", "body": "one concise explanatory sentence"}},
      "glass": {{"kicker": "short category", "headline": "main Hindi line", "body": "one short support line", "value": null, "suffix": "", "label": "", "delta": null, "delta_direction": "up | down | flat", "location": "", "coordinates": "", "chapter": ""}},
      "map": {{"lat": 0.0, "lon": 0.0, "label": ""}},
      "compare": {{"value": 0, "unit": "मीटर", "label": "what the number is (Hindi)", "anchor_label": "बुर्ज ख़लीफ़ा", "anchor_value": 828, "anchor_unit": "मीटर"}},
      "causal": {{"headline": "optional short Hindi headline", "steps": ["3-6 SHORT Hindi steps, each <= 6 words, cause -> effect order"]}},
      "evidence": {{"kicker": "स्रोत", "headline": "short Hindi claim being proven", "source": "the REAL named source (mission/agency/journal + name)", "date": "year or date", "confidence": "पुष्टि | अनुमान | विवादित"}}
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
- 0-1 scenes are "scale": when ONE big number begs a physical comparison the
  viewer can feel. Fill compare: the number (value+unit) and ONE familiar
  Indian anchor (anchor_label + anchor_value in the same unit — बुर्ज ख़लीफ़ा
  828 मीटर, कुतुब मीनार 73 मीटर, एक रेल डिब्बा 25 मीटर, हिमालय 8,849 मीटर).
  The narration must SAY the value. Use on a "comparison" narrative_role scene.
- 0-1 scenes are "causal": when the mechanism is a chain (A causes B causes C),
  show it as a stepwise diagram instead of generic footage. causal.steps =
  3-6 SHORT Hindi steps in strict cause->effect order. Pair with
  narrative_role "explanation" — this replaces the weakest broll explanation.
- 0-1 scenes are "evidence": on the video's strongest PROOF beat. Name the
  REAL source (mission, agency, journal, scientist + year) in evidence.source
  and tag confidence HONESTLY: "पुष्टि" only for well-established findings,
  "अनुमान" for estimates/models, "विवादित" for contested claims. The frame
  brackets real footage — search_terms must request authentic/archival
  material (NASA, expedition, observatory), NEVER generated art. Pair with
  narrative_role "evidence". An honest "अनुमान" tag builds more trust than a
  fake certainty.
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
- PROMISE LADDER (the retention engine — a deterministic audit enforces this):
  the video is NOT one giant withheld secret. It rewards early, then deepens:
  hook conflict -> partial answer -> deeper question -> mechanism/evidence ->
  reversal -> main reveal -> implication.
  * Scene 1 frames retention_plan.core_question but NEVER answers it. If the
    topic's headline fact is unavoidable in the hook (the title already says
    it), state it and immediately make the REAL question deeper: "क्यों",
    "कैसे", "सबसे पहले क्या फेल होगा", "इससे क्या बदलता है".
  * A partial answer/reward lands within the first 2 scenes.
  * The main_reveal scene sits at 55-85% of the total words — never earlier,
    and its content (retention_plan.main_reveal) must not be stated or
    paraphrased by ANY earlier scene.
  * Keep 1-2 major open_loops active at all times; close one before opening
    a third; every loop closes before the video ends.
  * Every scene changes at least one of: knowledge, stakes, certainty, scale,
    direction or emotion. A scene that only restates an earlier idea with new
    footage does not belong in the video.
  * No more than two consecutive scenes share a narrative_role.
  * After the main reveal: one implication scene (what this means for the
    viewer/world), then a decisive conclusion that closes every open loop.
- ENGINE NEVER GOES FLAT: milestone values must keep moving until at least
  ~75-80% of the script. If the changing_variable naturally reaches its
  destination earlier, hand the story to a SECOND engine (an investigation,
  a failure chain, a countdown) and let the milestones track that instead —
  never repeat the same milestone value for 3 scenes in a row.
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
  payoff that lands the answer with a strong, conclusive final line — NO
  next-video tease, NO "like and subscribe" begging.
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
            # video, and expanding here is free (no wasted voice credits).
            # Two attempts; a persistent miss is recorded as a FAILURE (not a
            # warning) and run.py drafts the release (retention.gate).
            for _pass in range(2):
                wc = _word_count(script)
                if wc >= int(min_words * 0.94):
                    break
                print(f"[script] undershoot ({wc}/{min_words}-{max_words} "
                      f"words) — expansion pass {_pass + 1}")
                exp = f"""The draft below runs {wc} spoken words but must run
at least {min_words} words (band {min_words}-{max_words}; stop where the
story naturally resolves). Expand the THINNEST scenes with
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
                        for field in ("stat", "card", "glass", "map", "milestone",
                                      "compare", "causal", "evidence",
                                      "narrative_role"):
                            after[field] = before.get(field, {})
                    for field in ("premise", "changing_variable", "hero_prompt",
                                  "forbidden_visuals", "title_options",
                                  "thumb_options", "thumb_headline",
                                  "thumb_question", "next_tease_topic",
                                  "retention_plan"):
                        if not expanded.get(field):
                            expanded[field] = script.get(field)
                    expanded["topic"] = topic
                    if _word_count(expanded) > wc:
                        script = expanded
                        print(f"[script] expanded to {_word_count(script)} words")
                except Exception as exc:
                    print(f"[script] expansion skipped ({exc})")
                    break
            # overshoot is a miss too: running past the band's ceiling
            # dilutes pacing and trips the runtime gate at render.
            # Trim verbose scenes BEFORE TTS (free), mirroring the expansion.
            for _pass in range(2):
                wc = _word_count(script)
                if wc <= int(max_words * 1.05):
                    break
                print(f"[script] overshoot ({wc}/{min_words}-{max_words} "
                      f"words) — trim pass {_pass + 1}")
                trim = f"""The draft below runs {wc} spoken words but must stay
under {int(max_words * 1.03)} words (band {min_words}-{max_words}). TRIM the
most verbose scenes: cut adjectives, repeated ideas and any sentence that adds
no new information — NEVER cut milestone values, reveals, numbers that graphics
display, or the promise-ladder structure. Keep the same JSON schema, scene
count, visual modes and every non-narration field unchanged.
{_lang_rules(cfg)}
Return ONLY the full revised JSON.

DRAFT:
{json.dumps(script, ensure_ascii=False)}"""
                try:
                    trimmed = _normalize(_parse_json(_llm(trim, cfg, api_key)), 4)
                    for before, after in zip(script["scenes"], trimmed["scenes"]):
                        for field in ("stat", "card", "glass", "map", "milestone",
                                      "compare", "causal", "evidence",
                                      "narrative_role"):
                            after[field] = before.get(field, {})
                    for field in ("premise", "changing_variable", "hero_prompt",
                                  "forbidden_visuals", "title_options",
                                  "thumb_options", "thumb_headline",
                                  "thumb_question", "next_tease_topic",
                                  "retention_plan"):
                        if not trimmed.get(field):
                            trimmed[field] = script.get(field)
                    trimmed["topic"] = topic
                    if _word_count(trimmed) < wc:
                        script = trimmed
                        print(f"[script] trimmed to {_word_count(script)} words")
                except Exception as exc:
                    print(f"[script] trim skipped ({exc})")
                    break
            wc = _word_count(script)
            script["word_budget"] = {
                "target": words, "min": min_words,
                "max": max_words, "actual": wc,
                "wpm_used": wpm,
                "ok": int(min_words * 0.90) <= wc <= int(max_words * 1.10),
            }
            if not script["word_budget"]["ok"]:
                print(f"[script] WORD BUDGET MISS: {wc} vs band "
                      f"{min_words}-{max_words} — the release "
                      "will be flagged for review")
            script["skeleton"] = skel_name
            _enforce_title_variety(script, done)
            script = _retention_pass(script, cfg, api_key, topic)
            script = _plan_visual_beats(script, cfg, api_key)
            modes = [s["visual_mode"] for s in script["scenes"]]
            print(f"[script] '{script['title']}' — {len(modes)} scenes, modes: {modes}")
            return script
        except (KeyError, AssertionError, json.JSONDecodeError) as e:
            print(f"[script] invalid script JSON (attempt {attempt + 1}): {e}")
    raise RuntimeError("Could not obtain a valid script after 3 attempts")


def generate_short_script(cfg: dict, topic: str, api_key: str,
                          learnings: str = "", done: list | None = None) -> dict:
    """Script for a vertical Short/Reel: one idea, loop-friendly. Length is
    ADAPTIVE inside [min_seconds, max_seconds]: the story's promise decides,
    not a fixed clock — a checkpoint journey needs more runway than one fact
    (the #1 viewer complaint on fixed-length shorts was "feels cut off")."""
    done = done if done is not None else []
    scfg = cfg.get("short", {})
    min_seconds = int(scfg.get("min_seconds", scfg.get("target_seconds", 40)))
    max_seconds = int(scfg.get("max_seconds",
                               max(55, int(scfg.get("target_seconds", 30)))))
    # shorts word budget calibrates to the REAL spoken pace (Sarvam Hindi with
    # pauses runs ~95-105 wpm, well below the long-form planning rate)
    wpm = int(scfg.get("wpm", min(_wpm(cfg), 105)))
    min_words = int(min_seconds / 60 * wpm)
    words = int(max_seconds / 60 * wpm)
    short_ai_max = min(_ai_max(cfg), 2)
    learn_block = (f"\nCHANNEL LEARNINGS — apply to hook and pacing:\n{learnings}\n"
                   if learnings else "")
    prompt = f"""You are writing a YouTube SHORT / Instagram REEL script for a
faceless channel (vertical video: voiceover + b-roll + big captions).

TOPIC: {topic}
ONE PROMISE (the hard rule for this format): this Short makes exactly ONE
claim and settles it. A checkpoint or timeline promise ("हर 5 मिनट...",
"1 सेकंड से 1 घंटे तक...", "minute by minute") belongs to a long-form
episode, NOT here — in a Short those checkpoints cannot all appear, so the
video reads as cut off. Measured on this channel: every checkpoint Short
retained under 40% of its runtime; every one-claim Short retained over 55%,
and the best two were replayed end-to-end. Do not write a checkpoint title
and do not structure the scenes as a tour of stages.

LENGTH — the claim decides, inside a hard band:
HARD RANGE: {min_words}-{int(words * 1.05)} spoken words TOTAL
({min_seconds}-{max_seconds} seconds). Use the FEWEST words that COMPLETELY
settle the one claim — a jolting fact can land near the bottom of the band;
a claim needing real evidence uses the top. Never stretch a small idea and
never amputate a big one. Count your words before returning.

PROMISE AUDIT (do this BEFORE writing scenes): state to yourself the ONE
question your title makes the viewer expect. It must be answered on screen,
completely. If you find yourself listing three or more questions the title
raises, the title is too big for this format — rewrite the title smaller
rather than answering two of three. The second-to-last scene must resolve
the CENTRAL question with a clear verdict (what it means / who survives /
what remains), not just another fact.
TONE: {cfg['channel']['tone']}, but faster and punchier than long-form
{learn_block}{_variety_rules(done, len(done), topic)}{_lang_rules(cfg)}{_style_rules()}
Return ONLY valid JSON:
{{
  "title": "<= 80 chars, curiosity gap, no clickbait lies. ONE promise the video can settle — never 'हर N मिनट/मीटर', 'X से Y तक' or a stage-by-stage timeline; those need long-form runtime.",
  "title_options": ["3 alternative Hindi titles, strongest first, each keeping the ONE-promise rule"],
  "thumb_text": "2-4 bold ENGLISH/Hinglish punch words (Latin script)",
  "delivery-note": "each scene also gets \"delivery\": hook | calm | reveal | urgent (scene 1 = hook; the twist scene = reveal); and may use visual_mode \"map\" with \"map\": {{\"lat\": 0.0, \"lon\": 0.0, \"label\": \"हिन्दी\"}} when one specific place is the star (0-1 map scenes)",
  "payoff": "ONE declarative Hindi sentence that ANSWERS the hook's question",
  "meaning": "ONE Hindi sentence: why that answer matters to the viewer",
  "loop_bridge": "optional COMPLETE Hindi sentence that points back to the hook on replay ('' if none; never end on a connector)",
  "description": "1-2 lines in HINDI (Devanagari) that restate the hook as a question. No hashtags here (the pipeline appends them).",
  "tags": ["6-10 tags a HINDI-SPEAKING viewer in India would type. At least 4 in Devanagari, 1-2 Hinglish in Latin script, rest English topic terms."],
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
  built payoff -> meaning -> optional replay cue, in that order.
  * payoff FIRST: a complete declarative sentence answering the hook. A
    question is NOT a payoff. A new topic is NOT a payoff.
  * meaning SECOND: one complete sentence of why it matters ("सीमा हमारी है,
    अंतरिक्ष की नहीं") — this is what the viewer takes away.
  * loop_bridge LAST and OPTIONAL: it must be a COMPLETE standalone sentence
    that points back to the opening without requiring the replay to finish its
    grammar (for example "सवाल फिर वहीं लौटता है।"). The visual loop supplies
    replay energy; never force it with an unfinished spoken fragment.
  * BANNED as final words: "लेकिन...", "लेकिन अगर...", "और अगर...", "तो?",
    "क्या होगा?", "...साबित करते हैं", "तो अगली बार", "इसीलिए" — any
    construction that leaves the sentence hanging. The video must feel
    complete even when autoplay does not replay it.
- Exactly 0 "kinetic" scenes, 0-1 "stat", 0-{short_ai_max} "ai_image"
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
            _enforce_short_hook(script)
            _enforce_short_payoff(script)
            _enforce_title_scope(script, max_seconds)
            _enforce_title_variety(script, done)
            print(f"[script] SHORT '{script['title']}' — "
                  f"{[s['visual_mode'] for s in script['scenes']]}")
            return script
        except (KeyError, AssertionError, json.JSONDecodeError) as e:
            print(f"[script] invalid short JSON (attempt {attempt + 1}): {e}")
    raise RuntimeError("Could not obtain a valid short script after 3 attempts")



# Openings that cost the first seconds — the window a Short lives or dies in.
# The measured failure: the channel's 24s Short averaged 3.6s of view time, so
# viewers were gone before the first sentence finished. `_style_rules` has
# banned these in the prompt since day one; nothing ever checked the output.
_BANNED_OPENER = re.compile(
    r"^\s*(?:"
    r"नमस्कार|नमस्ते|हैलो|हेलो|दोस्तों|स्वागत है|"
    r"क्या आप जानते ह|क्या आपने कभी|आइए जानते ह|आइये जानते ह|"
    r"कल्पना क(?:ीजिए|रें)|चलिए शुरू करते ह|आज हम|इस वीडियो में|"
    r"hello|hi there|hey guys|welcome back|"
    r"have you ever wondered|did you know|imagine a world|let'?s dive in"
    r")\S*[\s,–—-]*", re.I)

_SENT_SPLIT = re.compile(r"(?<=[।.!?])\s+")

HOOK_MAX_WORDS = 12


def _enforce_short_hook(script: dict) -> None:
    """Deterministic opening contract for a Short: no greeting, no stock
    opener, and the hook fits inside HOOK_MAX_WORDS.

    Mirrors `_enforce_short_payoff` at the other end of the script. Both fail
    open — a warned-but-shipped hook beats a crashed pipeline — but the
    banned-opener strip is a true repair, not a warning."""
    scenes = script.get("scenes") or []
    if not scenes:
        return
    first = scenes[0]
    narration = str(first.get("narration") or "").strip()
    if not narration:
        return

    stripped = narration
    while True:
        cut = _BANNED_OPENER.sub("", stripped, count=1).lstrip(" ,–—-")
        if cut == stripped or not cut:
            break
        stripped = cut
    if stripped != narration:
        print(f"[script] hook contract: stripped stock opener "
              f"({narration[:34]!r} -> {stripped[:34]!r})")
        narration = stripped

    words = narration.split()
    if len(words) > HOOK_MAX_WORDS:
        # Safe trim only: keep whole leading sentences while they fit, so we
        # never amputate mid-clause.
        kept, count = [], 0
        for sent in _SENT_SPLIT.split(narration):
            n = len(sent.split())
            if kept and count + n > HOOK_MAX_WORDS:
                break
            kept.append(sent)
            count += n
        trimmed = " ".join(kept).strip()
        if kept and count <= HOOK_MAX_WORDS and trimmed:
            print(f"[script] hook contract: trimmed hook "
                  f"{len(words)} -> {count} words")
            narration = trimmed
        else:
            print(f"[script] WARNING: hook runs {len(words)} words "
                  f"(max {HOOK_MAX_WORDS}) and has no clean sentence break — "
                  f"shipping as-is: {narration[:60]}")

    first["narration"] = narration


def _enforce_title_scope(script: dict, max_seconds: float,
                         shape: str = topic_shape.SINGLE_CLAIM) -> None:
    """The title may not promise more than the format can pay off.

    This is the belt to the topic gate's braces: `pick_topic(shape=...)` keeps
    checkpoint TOPICS out of Shorts, but the model can still invent a
    checkpoint TITLE for a single-claim topic. Both of the channel's
    worst-retaining Shorts failed exactly here — a title promising a
    minute-by-minute hour on a 24-second video (15.0% retention) and one
    promising 90 seconds of stakes in a 78-second video (11.3%).

    Shape is checked before runtime arithmetic: for a Short, ANY checkpoint
    title is wrong even when the beat math happens to fit the band, because
    the format's contract is one claim."""
    def _ok(text: str) -> bool:
        return (topic_shape.classify(text) == shape
                and topic_shape.fits_in(text, max_seconds))

    title = str(script.get("title") or "").strip()
    if not title or _ok(title):
        return
    for alt in (script.get("title_options") or []):
        alt = str(alt).strip()
        if alt and _ok(alt):
            print(f"[script] title scope: {topic_shape.explain(title)} does not "
                  f"fit a {int(max_seconds)}s {shape} — swapped in alternate: "
                  f"{alt[:60]}")
            script["title"] = alt
            return
    print(f"[script] WARNING: title is {topic_shape.explain(title)}, which a "
          f"{int(max_seconds)}s {shape} cannot deliver, and no alternate fits "
          f"— shipping as-is: {title[:60]}")


# Final constructions that leave a short feeling cut off mid-sentence.
_DANGLING_END = re.compile(
    r"(लेकिन|और अगर|अगर|तो|क्या होगा|जानने के लिए|इसीलिए|तो अगली बार)"
    r"[\s.…?!]*$")


def _enforce_short_payoff(script: dict) -> None:
    """Deterministic ending contract: payoff and meaning must finish before an
    optional COMPLETE replay cue. Dangling connectors are removed so the Short
    still feels finished when a platform does not autoplay the loop."""
    scenes = script.get("scenes") or []
    if not scenes:
        return
    payoff = str(script.get("payoff") or "").strip()
    meaning = str(script.get("meaning") or "").strip()
    bridge = str(script.get("loop_bridge") or "").strip()
    if bridge and _DANGLING_END.search(bridge):
        print("[script] ending contract: dropped dangling loop bridge")
        bridge = ""
        script["loop_bridge"] = ""

    last = scenes[-1]
    narration = str(last.get("narration") or "").strip()
    dangling = bool(_DANGLING_END.search(narration))
    has_payoff = bool(payoff) and payoff[:24] in narration
    has_meaning = not meaning or meaning[:24] in narration
    has_bridge = not bridge or bridge[:18] in narration
    needs_rebuild = dangling or not has_payoff or not has_meaning or not has_bridge

    if payoff and needs_rebuild:
        rebuilt = " ".join(x for x in (payoff, meaning, bridge) if x).strip()
        if rebuilt:
            print("[script] ending contract: rebuilt complete final scene")
            last["narration"] = rebuilt
            return

    if dangling:
        # Last-resort repair for older model responses without structured
        # payoff fields: peel off every dangling connector, not just the last
        # word ("लेकिन अगर" needs two passes).
        cleaned = narration
        while cleaned and _DANGLING_END.search(cleaned):
            cleaned = _DANGLING_END.sub("", cleaned).rstrip(" .…?!")
        if cleaned:
            last["narration"] = cleaned + ("" if cleaned.endswith("।") else "।")
            print("[script] ending contract: trimmed dangling final fragment")
        else:
            print("[script] WARNING: could not repair empty final line")


def log_topic_done(topic: str, done_file: str = "topics_done.txt") -> None:
    with open(done_file, "a", encoding="utf-8") as f:
        f.write(topic + "\n")
