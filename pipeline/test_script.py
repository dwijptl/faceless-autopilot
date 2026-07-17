"""Script-only test bench — the full writing pipeline with ZERO media spend.

Runs topic -> script (Claude when ANTHROPIC_API_KEY works, else Gemini) ->
critique -> word budget -> retention audit -> visual beat plan -> factcheck,
then prints a human-readable preview straight into the workflow log and
uploads script.json + script_preview.md as an artifact.

Costs a few rupees of LLM at most. No TTS, no stock, no AI images, no render.
Side-effect free: topics_done.txt is NOT written, so the tested topic (or the
locked NEXT: tease) is still available for the real scheduled run.

Actions -> Test Script -> Run workflow (optionally force a topic).
"""
import json
import os
import sys
import time

import yaml

sys.path.insert(0, os.path.dirname(__file__))
import calibration                  # noqa: E402
import factcheck                    # noqa: E402
import script_gen                   # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    t0 = time.time()
    with open(os.path.join(REPO_ROOT, "config.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        sys.exit("Missing GEMINI_API_KEY")
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("[test] NOTE: ANTHROPIC_API_KEY not set — Gemini will write")

    learnings = script_gen.load_learnings(REPO_ROOT)
    measured = calibration.measured_wpm(
        REPO_ROOT, int(cfg["channel"].get("wpm", 130)), kind="long")
    if measured:
        cfg["channel"]["wpm_measured"] = measured
        print(f"[calib] word budget uses measured pace: {measured} wpm")

    topic = script_gen.pick_topic(
        cfg, gemini_key, os.path.join(REPO_ROOT, "topics_done.txt"), learnings)
    script = script_gen.generate_script(cfg, topic, gemini_key, learnings)
    fact = factcheck.check_script(script, cfg, gemini_key)

    outdir = os.path.join(REPO_ROOT, "out", "script_test")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
    with open(os.path.join(outdir, "claims.json"), "w", encoding="utf-8") as f:
        json.dump(fact, f, indent=2, ensure_ascii=False)

    report = script.get("retention_report") or {}
    wb = script.get("word_budget") or {}
    plan = script.get("retention_plan") or {}
    provider = script_gen.PROVIDER_USED or "unknown"

    lines = [
        f"# {script['title']}",
        "",
        f"**Writer:** {provider}  ·  **Words:** {wb.get('actual')}/"
        f"{wb.get('target')} (ok={wb.get('ok')})  ·  "
        f"**Story audit:** {'PASSED' if report.get('passed') else 'FAILED'} "
        f"({len(report.get('violations', []))} open violations)  ·  "
        f"**Fact-check:** {fact.get('status')} "
        f"({fact.get('unsupported', 0)} unsupported, "
        f"{len(fact.get('high_risk_unsupported', []))} high-risk)",
        "",
        f"**Core question:** {plan.get('core_question', '')}",
        f"**Viewer assumption:** {plan.get('viewer_assumption', '')}",
        f"**Main reveal (scene {plan.get('main_reveal_scene')}):** "
        f"{plan.get('main_reveal', '')}",
        "",
        "| # | role | mode | delivery | reward |",
        "|---|------|------|----------|--------|",
    ]
    for s in script["scenes"]:
        rw = s.get("reward") or {}
        lines.append(f"| {s['n']} | {s.get('narrative_role', '')} | "
                     f"{s.get('visual_mode', '')} | {s.get('delivery', '')} | "
                     f"{rw.get('type', '')} {rw.get('strength', '')} |")
    lines.append("")
    for s in script["scenes"]:
        lines.append(f"## Scene {s['n']} — {s.get('title', '')} "
                     f"[{s.get('narrative_role', '?')}/"
                     f"{s.get('visual_mode', '?')}]")
        lines.append(s.get("narration", ""))
        if s.get("question_out"):
            lines.append(f"*→ pull: {s['question_out']}*")
        lines.append("")
    for v in report.get("violations", []):
        lines.append(f"- ⚠️ [{v.get('code')}] {v.get('detail')}")
    md = "\n".join(lines)
    with open(os.path.join(outdir, "script_preview.md"), "w",
              encoding="utf-8") as f:
        f.write(md)

    print("\n" + "=" * 72)
    print(f"SCRIPT PREVIEW (written by {provider}, "
          f"{time.time() - t0:.0f}s total)")
    print("=" * 72)
    print(md)
    print("=" * 72)
    print("[test] artifact: script.json + script_preview.md + claims.json")


if __name__ == "__main__":
    main()
