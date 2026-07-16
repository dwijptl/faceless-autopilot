"""Deterministic pre-TTS retention audit (zero LLM calls).

quality_report.py asks "did it render correctly?" — this module asks "will a
viewer keep watching?". It runs BEFORE voice synthesis so a failed script can
be repaired for free (one Gemini/Claude call) instead of wasting Sarvam
credits on a story that leaks its payoff in scene 1.

Checks are word-fraction based (seconds don't exist yet pre-TTS). Every rule
maps to a measured failure of a real render (the Venus run: payoff spent in
the cold open, ALTITUDE flat from scene 7, repeated heat/pressure claims) or
to the structure shared by the studied reference videos (SciMyth journey,
GetSetFly Dark Oxygen, Veritasium GPS: staged reveals, main answer at
~55-85%, loops opened early and closed late).

Fail-open by design: `lint()` only reports. Gating policy lives in run.py
(config `retention.gate`: off | draft | block).
"""
import re

ROLES = ("hook", "question", "context", "discovery", "explanation",
         "comparison", "reversal", "evidence", "escalation", "partial_answer",
         "mini_reveal", "main_reveal", "implication", "conclusion",
         "next_curiosity")

# roles that count as a mid-video re-hook (they renew or pay the open
# question — a reveal is itself the strongest re-hook)
REHOOK_ROLES = {"question", "reversal", "escalation", "mini_reveal",
                "discovery", "partial_answer", "main_reveal"}

_WORD_RE = re.compile(r"[\wऀ-ॿ]+")


def _tokens(text) -> list:
    return [t.casefold() for t in _WORD_RE.findall(str(text or ""))]


def _num_variants(value) -> list:
    """Spoken-form variants of a numeric display value ("9200" / "9,200" /
    "9.2")."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return []
    out = []
    if v == int(v):
        i = int(v)
        out.append(str(i))
        if abs(i) >= 10000:
            out.append(f"{i:,}")
    else:
        out.append(f"{v:g}")
        out.append(str(int(v)))
    return out


def _scene_words(scene) -> int:
    return len(_tokens(scene.get("narration", "")))


def _fractions(scenes) -> list:
    """[(start_frac, end_frac)] per scene, by cumulative word position."""
    counts = [_scene_words(s) for s in scenes]
    total = max(sum(counts), 1)
    out, cursor = [], 0
    for c in counts:
        out.append((cursor / total, (cursor + c) / total))
        cursor += c
    return out


def _overlap(needle_tokens, haystack_tokens) -> float:
    if not needle_tokens:
        return 0.0
    hs = set(haystack_tokens)
    return sum(1 for t in needle_tokens if t in hs) / len(needle_tokens)


def _jaccard(a, b) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def lint(script: dict, cfg: dict) -> dict:
    """Return {"passed": bool, "violations": [...], "metrics": {...}}."""
    rcfg = cfg.get("retention", {}) if isinstance(cfg, dict) else {}
    reveal_min = float(rcfg.get("reveal_min_frac", 0.55))
    reveal_max = float(rcfg.get("reveal_max_frac", 0.85))
    max_open = int(rcfg.get("max_open_loops", 2))
    max_gap_words = int(rcfg.get("max_reward_gap_words", 60))
    max_role_run = int(rcfg.get("max_same_role_run", 2))
    engine_until = float(rcfg.get("engine_active_until", 0.75))
    rehook_tol = float(rcfg.get("rehook_tolerance", 0.12))

    scenes = script.get("scenes") or []
    n = len(scenes)
    violations = []

    def add(code, detail, scene=None):
        violations.append({"code": code, "scene": scene, "detail": detail})

    if n < 4:
        add("structure", f"only {n} scenes — cannot audit")
        return {"passed": False, "violations": violations, "metrics": {}}

    fracs = _fractions(scenes)
    plan = script.get("retention_plan") or {}

    # ---- C1: hook opens, core question exists ------------------------------
    if scenes[0].get("narrative_role") not in ("hook", ""):
        add("hook_role", "scene 1 narrative_role must be 'hook'", 1)
    if not str(plan.get("core_question", "")).strip():
        add("core_question", "retention_plan.core_question is missing")

    # ---- C2: main reveal exists and lands at 55-85% of the words -----------
    reveal_idx = None
    mr_scene = plan.get("main_reveal_scene")
    if isinstance(mr_scene, (int, float)) and 1 <= int(mr_scene) <= n:
        reveal_idx = int(mr_scene) - 1
    else:
        for i, s in enumerate(scenes):
            if s.get("narrative_role") == "main_reveal":
                reveal_idx = i
                break
    if reveal_idx is None:
        add("main_reveal", "no scene carries narrative_role 'main_reveal' "
                           "and retention_plan.main_reveal_scene is unset")
    else:
        start = fracs[reveal_idx][0]
        if not reveal_min <= start <= reveal_max:
            add("reveal_placement",
                f"main reveal starts at {start:.0%} of the script — must land "
                f"between {reveal_min:.0%} and {reveal_max:.0%}",
                reveal_idx + 1)

    # ---- C3: the payoff must not be spent early ----------------------------
    reveal_text = _tokens(plan.get("main_reveal", ""))
    if len(reveal_text) >= 4 and reveal_idx is not None:
        for i in range(reveal_idx):
            if _overlap(reveal_text, _tokens(scenes[i].get("narration", ""))) >= 0.6:
                add("early_answer",
                    f"scene {i + 1} already states the main reveal — the "
                    "opening may frame the question, never answer it", i + 1)
                break

    # ---- C4: promise ladder / open loops -----------------------------------
    loops = [lp for lp in (plan.get("open_loops") or []) if isinstance(lp, dict)]
    if not loops:
        add("open_loops", "retention_plan.open_loops is empty — at least one "
                          "question must stay open across scenes")
    valid_loops = []
    for k, lp in enumerate(loops):
        o, c = lp.get("opens_scene"), lp.get("closes_scene")
        if not (isinstance(o, int) and isinstance(c, int)
                and 1 <= o < c <= n):
            add("loop_bounds",
                f"loop {k + 1} ('{str(lp.get('question', ''))[:40]}') needs "
                f"1 <= opens_scene < closes_scene <= {n}")
            continue
        p = lp.get("partial_scene")
        if isinstance(p, int) and not (o < p < c):
            add("loop_partial", f"loop {k + 1} partial_scene must sit between "
                                f"open ({o}) and close ({c})")
        valid_loops.append((o, c))
    for i in range(1, n + 1):
        open_now = sum(1 for o, c in valid_loops if o <= i < c)
        if open_now > max_open:
            add("too_many_loops",
                f"{open_now} major loops open at scene {i} — maximum "
                f"{max_open}; close one before opening another", i)
            break

    # ---- C5: reward gaps ----------------------------------------------------
    gap = 0
    for i, s in enumerate(scenes):
        strength = 0.0
        rw = s.get("reward") or {}
        try:
            strength = float(rw.get("strength", 0.0))
        except (TypeError, ValueError):
            pass
        if strength < 0.3:
            gap += _scene_words(s)
            if gap > max_gap_words:
                add("reward_gap",
                    f"~{gap} consecutive words (scenes up to {i + 1}) with no "
                    f"meaningful reward (strength >= 0.3) — max {max_gap_words}",
                    i + 1)
                gap = 0
        else:
            gap = 0

    # ---- C6: role rotation ---------------------------------------------------
    run_role, run_len = None, 0
    for i, s in enumerate(scenes):
        role = s.get("narrative_role") or ""
        if role and role == run_role:
            run_len += 1
            if run_len > max_role_run:
                add("role_run",
                    f"{run_len} consecutive '{role}' scenes ending at scene "
                    f"{i + 1} — rotate roles (max {max_role_run})", i + 1)
                run_len = 0
                run_role = None
        else:
            run_role, run_len = role, 1

    # ---- C7: re-hooks near 25 / 50 / 75% ------------------------------------
    for mark in (0.25, 0.50, 0.75):
        hit = any(scenes[i].get("narrative_role") in REHOOK_ROLES
                  and abs(fracs[i][0] - mark) <= rehook_tol
                  for i in range(n))
        if not hit:
            add("rehook_missing",
                f"no question/reversal/escalation/mini_reveal scene near the "
                f"{mark:.0%} mark (±{rehook_tol:.0%})")

    # ---- C8: the progress engine must not go flat ----------------------------
    values = []
    for s in scenes:
        m = s.get("milestone") or {}
        values.append(m.get("value") if isinstance(m.get("value"),
                                                   (int, float)) else None)
    with_val = [v for v in values if v is not None]
    if len(with_val) >= max(3, n // 2):
        climax = reveal_idx if reveal_idx is not None else n - 1
        flat_run, last_v = 1, None
        for i, v in enumerate(values[:climax + 1]):
            if v is None:
                continue
            if last_v is not None and v == last_v:
                flat_run += 1
                if flat_run > 2:
                    add("engine_flat",
                        f"milestone value stuck at {v} for {flat_run} scenes "
                        f"ending at scene {i + 1} — the visible journey "
                        "stopped before the story did; keep the variable "
                        "moving or hand off to a second engine "
                        "(investigation / failure chain)", i + 1)
                    flat_run = 1
            else:
                flat_run = 1
            last_v = v
        changes = [i for i in range(1, n) if values[i] is not None
                   and values[i - 1] is not None and values[i] != values[i - 1]]
        if changes and fracs[changes[-1]][0] < engine_until:
            add("engine_stops_early",
                f"last milestone change happens at {fracs[changes[-1]][0]:.0%} "
                f"of the script — the engine must stay active until "
                f"~{engine_until:.0%}")

    # ---- C9: spoken numbers must match displayed numbers ---------------------
    for i, s in enumerate(scenes):
        narration = str(s.get("narration", ""))
        for label, value in (("stat", (s.get("stat") or {}).get("value")),
                             ("compare", (s.get("compare") or {}).get("value")),
                             ("milestone", (s.get("milestone") or {}).get("value"))):
            variants = _num_variants(value)
            if not variants or float(value) == 0:
                continue
            if not any(v in narration for v in variants):
                add("claim_display_mismatch",
                    f"scene {i + 1} displays {label} value {value} but the "
                    f"narration never says it — screen and voice must agree",
                    i + 1)

    # ---- C10: repeated meaning ------------------------------------------------
    token_cache = [_tokens(s.get("narration", "")) for s in scenes]
    for i in range(n):
        for j in range(i + 2, n):
            if min(len(token_cache[i]), len(token_cache[j])) < 12:
                continue
            if _jaccard(token_cache[i], token_cache[j]) >= 0.55:
                add("repeated_meaning",
                    f"scenes {i + 1} and {j + 1} say substantially the same "
                    "thing — a later restatement must add a NEW function "
                    "(proof, scale, consequence), not repetition", j + 1)

    # ---- C11: forward pull ------------------------------------------------------
    missing_q = sum(1 for s in scenes[:-1]
                    if not str(s.get("question_out", "")).strip())
    if missing_q > (n - 1) * 0.4:
        add("question_out",
            f"{missing_q}/{n - 1} scenes have no question_out — most scenes "
            "must leave a question that pulls into the next scene")

    metrics = {
        "scenes": n,
        "total_words": sum(_scene_words(s) for s in scenes),
        "reveal_fraction": (round(fracs[reveal_idx][0], 3)
                            if reveal_idx is not None else None),
        "open_loops": len(valid_loops),
        "violations": len(violations),
    }
    return {"passed": not violations, "violations": violations,
            "metrics": metrics}


def repair_prompt(script: dict, report: dict, cfg: dict,
                  lang_rules: str = "") -> str:
    """One machine-readable revision request for the script model."""
    import json as _json
    issues = "\n".join(
        f"- [{v['code']}]"
        + (f" (scene {v['scene']})" if v.get("scene") else "")
        + f" {v['detail']}"
        for v in report.get("violations", []))
    return f"""You are the story editor of a Hindi science documentary channel.
The draft below FAILED the channel's deterministic retention audit.
Fix EVERY listed violation while keeping the same JSON schema, scene count,
visual_mode, search_terms and all visual payloads (stat/card/glass/map)
intact unless a violation explicitly requires changing them (for example
'engine_flat' requires new escalating milestone values).

AUDIT VIOLATIONS (all must be fixed):
{issues}

Repair rules:
- Move or rewrite content; never pad with filler.
- The opening may FRAME the main reveal but must not state it.
- If the journey variable finishes early, hand the story to a second engine
  (an investigation, a failure chain, a countdown) with its own milestones.
- Every scene keeps: narrative_role, reward(type,strength), question_out.
{lang_rules}
Return ONLY the full corrected JSON.

DRAFT:
{_json.dumps(script, ensure_ascii=False)}"""
