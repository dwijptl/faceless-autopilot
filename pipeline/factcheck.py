"""Grounded pre-TTS claim review for science and geography scripts.

This is an editorial safety net, not a replacement for expert review. It keeps
the original script on any provider failure and records a visible status for
the human uploader.

Scope: narration AND packaging — the title, thumbnail text and the final
next-video tease are claims too (the "iron vaporizes on Venus" class of error
lived in a tease). Packaging claims are report-only (never auto-rewritten).

Risk tiers: every verdict carries `risk` — "high" for numeric / physical /
safety / geographic-superlative claims that would be embarrassing if wrong,
"normal" otherwise. With config `factcheck.gate: high_risk`, an unsupported
high-risk claim marks the release DRAFT — DO NOT PUBLISH (run.py); softening
still applies to everything either way.
"""
import json
import time

import requests

import script_gen


API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _models(cfg: dict) -> list[str]:
    return [cfg["llm"].get("model", "gemini-2.5-flash")] + list(
        cfg["llm"].get("fallback_models", []))


def _plain_json(prompt: str, cfg: dict, api_key: str) -> dict:
    """Use the existing JSON-capable model path to extract exact claim spans."""
    return script_gen._parse_json(script_gen._gemini(prompt, cfg, api_key))


def _grounded_json(prompt: str, cfg: dict, api_key: str) -> tuple[dict, list[str]]:
    """Ask Gemini with Google Search grounding; parse reply without JSON MIME."""
    last = ""
    for model in _models(cfg):
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.1},
        }
        for attempt in range(2):
            response = requests.post(
                f"{API_BASE}/{model}:generateContent?key={api_key}",
                json=body, timeout=120)
            if response.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            if response.status_code in (400, 404):
                last = response.text[:300]
                break
            response.raise_for_status()
            data = response.json()
            candidate = data["candidates"][0]
            text = candidate["content"]["parts"][0]["text"]
            chunks = candidate.get("groundingMetadata", {}).get("groundingChunks", [])
            urls = []
            for chunk in chunks:
                url = (chunk.get("web") or {}).get("uri")
                if url and url not in urls:
                    urls.append(url)
            return script_gen._parse_json(text), urls
    raise RuntimeError(f"Grounded Gemini failed: {last or 'no usable model'}")


def _claim_prompt(script: dict, max_claims: int) -> str:
    scenes = [{"n": s.get("n"), "narration": s.get("narration", "")}
              for s in script.get("scenes", [])]
    packaging = {
        "title": script.get("title", ""),
        "thumb_text": script.get("thumb_text", ""),
        "thumb_headline": script.get("thumb_headline", ""),
        "next_video_tease": script.get("next_tease_topic", ""),
    }
    scenes.append({"n": 0, "narration": "PACKAGING (title / thumbnail / "
                   "next-video tease — these are public claims too): "
                   + json.dumps(packaging, ensure_ascii=False)})
    return f"""Extract at most {max_claims} high-risk factual claims from this
Hindi documentary script. Include numbers, dates, rankings, geographic or
scientific classifications, causal explanations, and risk claims. Claims may
also come from the PACKAGING entry (scene 0) — a wrong number in a title,
thumbnail or tease is worse than one in narration. The `text` must be an
exact contiguous substring of its narration, not a paraphrase.
Return ONLY JSON: {{"claims":[{{"scene":1,"text":"exact span"}}]}}.

SCRIPT: {json.dumps(scenes, ensure_ascii=False)}"""


def _verify_prompt(claims: list[dict]) -> str:
    return f"""Use Google Search to fact-check the following Hindi documentary
claims. Prefer primary scientific or government sources. For every claim return
one item in the same order with: `verdict` (`supported`, `needs_softening`, or
`unsupported`), `replacement` (an accurate Hindi replacement; use original text
when supported), `risk` (`high` when the claim states a specific number,
physical mechanism, safety consequence or geographic superlative that would
seriously mislead viewers if wrong; else `normal`), and a short `note`.
Do not invent sources. Return ONLY JSON:
{{"results":[{{"verdict":"supported","replacement":"…","risk":"normal","note":"…"}}]}}.

CLAIMS: {json.dumps(claims, ensure_ascii=False)}"""


def _replace_once(text: str, old: str, new: str) -> str:
    if old and new and old in text:
        return text.replace(old, new, 1)
    return text


def check_script(script: dict, cfg: dict, api_key: str) -> dict:
    """Apply conservative claim softening and return a reviewer-facing report."""
    fc = cfg.get("factcheck", {})
    report = {"status": "disabled", "checked": 0, "softened": 0,
              "unsupported": 0, "high_risk_unsupported": [],
              "sources": [], "items": []}
    if not fc.get("enabled", True):
        return report
    try:
        extracted = _plain_json(_claim_prompt(script, int(fc.get("max_claims", 8))),
                                cfg, api_key)
        claims = extracted.get("claims") or []
        if not claims:
            report["status"] = "no-checkable-claims"
            return report
        verified, sources = _grounded_json(_verify_prompt(claims), cfg, api_key)
        results = verified.get("results") or []
        if len(results) != len(claims):
            raise ValueError("grounded response changed claim count")
        scenes = {int(s.get("n", i + 1)): s for i, s in enumerate(script.get("scenes", []))}
        for claim, result in zip(claims, results):
            verdict = str(result.get("verdict", "unsupported")).lower()
            replacement = str(result.get("replacement", "")).strip()
            risk = str(result.get("risk", "normal")).lower()
            risk = risk if risk in ("high", "normal") else "normal"
            item = {"scene": claim.get("scene"), "claim": claim.get("text", ""),
                    "verdict": verdict, "risk": risk,
                    "note": str(result.get("note", ""))}
            if verdict in ("needs_softening", "unsupported"):
                # packaging claims (scene 0) are report-only — no auto-rewrite
                try:
                    scene = scenes.get(int(claim.get("scene") or 0))
                except (TypeError, ValueError):
                    scene = None
                if scene and replacement:
                    before = scene["narration"]
                    scene["narration"] = _replace_once(before, str(claim.get("text", "")), replacement)
                    if scene["narration"] != before:
                        report["softened"] += 1
                if verdict == "unsupported":
                    report["unsupported"] += 1
                    if risk == "high":
                        report["high_risk_unsupported"].append(
                            str(claim.get("text", ""))[:120])
            report["items"].append(item)
        report.update({"status": "ok", "checked": len(claims), "sources": sources})
        print(f"[factcheck] {report['checked']} checked, "
              f"{report['softened']} softened, "
              f"{len(report['high_risk_unsupported'])} high-risk unsupported")
        return report
    except Exception as exc:
        report.update({"status": f"skipped ({exc})"})
        print(f"[factcheck] {report['status']}")
        return report


def markdown(report: dict) -> str:
    if report.get("status") != "ok":
        return f"Fact-check: {report.get('status', 'unknown')}"
    line = (f"Fact-check: {report['checked']} checked, "
            f"{report['softened']} softened, {report['unsupported']} unsupported")
    hru = report.get("high_risk_unsupported") or []
    if hru:
        line += ("\n\n> ⚠️ **HIGH-RISK UNSUPPORTED CLAIMS** — verify or remove "
                 "before publishing:\n"
                 + "\n".join(f"> - {c}" for c in hru[:5]))
    if report.get("sources"):
        links = "\n".join(f"- {url}" for url in report["sources"][:8])
        return f"{line}\n\n### Grounded sources\n{links}"
    return line
