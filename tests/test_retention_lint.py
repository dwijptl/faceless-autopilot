import copy

import retention_lint


def _scene(n, narration, role="", strength=0.7, milestone=None, stat=None,
           question_out="आगे क्या?"):
    s = {"n": n, "narration": narration, "narrative_role": role,
         "reward": {"type": "fact", "strength": strength},
         "question_out": question_out, "visual_mode": "broll"}
    if milestone is not None:
        s["milestone"] = {"value": milestone, "label": "DEPTH", "unit": "km"}
    if stat is not None:
        s["stat"] = {"value": stat, "suffix": "", "label": "x"}
    return s


def _healthy_script():
    """10 scenes, ~40 words each; reveal in scene 8 (~70%); loops open/close;
    milestones escalate; re-hook roles near 25/50/75%. Narration per scene is
    deliberately DISTINCT so the repetition detector stays quiet."""
    topics = [
        "सतह पर सब कुछ शांत दिखता है लेकिन पत्थरों के नीचे कुछ अजीब चल रहा है",
        "वैज्ञानिकों ने सेंसर उतारे और रीडिंग ने सबको चौंका दिया इतनी नमी यहां क्यों",
        "इस इलाके की चट्टानें ज्वालामुखी से बनीं और उनमें बारीक दरारों का जाल फैला है",
        "एक पुराना नक्शा बताता है कि यहां कभी नदी बहती थी जो अचानक गायब हो गई",
        "पहला जवाब मिला दरारों में सचमुच पानी रिस रहा है मगर मात्रा बहुत छोटी है",
        "दबाव और तापमान मिलकर खनिजों की बनावट बदल देते हैं जिससे पानी फंस जाता है",
        "जितना नीचे जाओ संकेत उतने तेज़ होते जाते हैं उपकरण अब चरम पर काम कर रहे हैं",
        "यही है असली जवाब नीचे बहता हुआ एक पूरा महासागर जो चट्टान के अंदर कैद है",
        "इसका मतलब धरती का जल चक्र हमारी सोच से कहीं बड़ा और पुराना निकला",
        "अगली बार उस जगह चलेंगे जहां यह छिपा पानी बाहर निकलने का रास्ता खोजता है",
    ]
    roles = ["hook", "question", "context", "discovery", "mini_reveal",
             "explanation", "escalation", "main_reveal", "implication",
             "next_curiosity"]
    scenes = []
    for i, (role, body) in enumerate(zip(roles, topics)):
        depth = (i + 1) * 100
        narration = (f"अब आप {depth} मीटर नीचे हैं। {body}। " + body[::-1][:0]
                     + f" {body}।")
        scenes.append(_scene(i + 1, narration, role, strength=0.75,
                             milestone=depth,
                             question_out=("" if i == len(roles) - 1
                                           else "अब आगे क्या होगा?")))
    return {
        "title": "t", "scenes": scenes,
        "retention_plan": {
            "core_question": "नीचे क्या छिपा है?",
            "viewer_assumption": "नीचे सिर्फ चट्टान है",
            "first_reversal": "चट्टान बहती है",
            "main_reveal": "नीचे बहता हुआ एक पूरा महासागर",
            "main_reveal_scene": 8,
            "open_loops": [
                {"question": "पानी कहां से आया?", "opens_scene": 1,
                 "partial_scene": 5, "closes_scene": 8},
                {"question": "क्या यह ऊपर आ सकता है?", "opens_scene": 4,
                 "partial_scene": None, "closes_scene": 9},
            ],
        },
    }


CFG = {"retention": {"enabled": True}}


def test_healthy_script_passes():
    report = retention_lint.lint(_healthy_script(), CFG)
    assert report["passed"], report["violations"]
    assert report["metrics"]["reveal_fraction"] is not None


def test_early_answer_and_early_reveal_fail():
    script = _healthy_script()
    # payoff text spoken in scene 1 (the Venus failure mode)
    script["scenes"][0]["narration"] += " नीचे बहता हुआ एक पूरा महासागर है"
    codes = {v["code"] for v in retention_lint.lint(script, CFG)["violations"]}
    assert "early_answer" in codes

    script2 = _healthy_script()
    script2["retention_plan"]["main_reveal_scene"] = 2
    codes2 = {v["code"] for v in
              retention_lint.lint(script2, CFG)["violations"]}
    assert "reveal_placement" in codes2


def test_flat_milestones_fail():
    script = _healthy_script()
    # ALTITUDE hits its destination at scene 4 and never moves again
    for s in script["scenes"][3:]:
        s["milestone"] = {"value": 0, "label": "ALT", "unit": "km"}
    codes = {v["code"] for v in retention_lint.lint(script, CFG)["violations"]}
    assert "engine_flat" in codes or "engine_stops_early" in codes


def test_role_runs_and_reward_gap_fail():
    script = _healthy_script()
    for s in script["scenes"][2:6]:
        s["narrative_role"] = "explanation"
        s["reward"] = {"type": "", "strength": 0.0}
    codes = {v["code"] for v in retention_lint.lint(script, CFG)["violations"]}
    assert "role_run" in codes
    assert "reward_gap" in codes


def test_claim_display_mismatch_fails():
    script = _healthy_script()
    script["scenes"][4]["stat"] = {"value": 92, "suffix": "बार", "label": "दबाव"}
    # narration never says 92
    codes = {v["code"] for v in retention_lint.lint(script, CFG)["violations"]}
    assert "claim_display_mismatch" in codes
    # saying the number fixes it
    script["scenes"][4]["narration"] += " दबाव 92 बार तक पहुंच जाता है"
    codes2 = {v["code"] for v in
              retention_lint.lint(script, CFG)["violations"]}
    assert "claim_display_mismatch" not in codes2


def test_repeated_meaning_fails():
    script = _healthy_script()
    script["scenes"][8]["narration"] = script["scenes"][2]["narration"]
    script["scenes"][8]["milestone"] = script["scenes"][2]["milestone"].copy()
    codes = {v["code"] for v in retention_lint.lint(script, CFG)["violations"]}
    assert "repeated_meaning" in codes


def test_too_many_open_loops_fail():
    script = _healthy_script()
    script["retention_plan"]["open_loops"] = [
        {"question": f"सवाल {k}?", "opens_scene": 1, "partial_scene": None,
         "closes_scene": 9} for k in range(3)]
    codes = {v["code"] for v in retention_lint.lint(script, CFG)["violations"]}
    assert "too_many_loops" in codes


def test_repair_prompt_lists_violations():
    script = _healthy_script()
    script["retention_plan"]["main_reveal_scene"] = 2
    report = retention_lint.lint(script, CFG)
    prompt = retention_lint.repair_prompt(script, report, CFG)
    assert "reveal_placement" in prompt
    assert "Return ONLY the full corrected JSON" in prompt


def test_lint_never_mutates_script():
    script = _healthy_script()
    before = copy.deepcopy(script)
    retention_lint.lint(script, CFG)
    assert script == before


# ---- deterministic C9 reconcile (script_gen._reconcile_display_numbers) ----

def _c9_script():
    return {"scenes": [
        {"n": 1, "narration": "सूरज से बड़ा तारा गिरता है।",
         "visual_mode": "broll",
         "milestone": {"value": 1000000000.0, "label": "YEARS", "unit": "yr"}},
        {"n": 2, "narration": "ब्लैक होल 9,200 मीटर तक फैलता है।",
         "visual_mode": "stat",
         "stat": {"value": 9200, "suffix": "m", "label": "size"}},
    ]}


def test_reconcile_drops_unspoken_milestone_keeps_spoken_stat():
    import script_gen
    cfg = {}
    script = _c9_script()
    report = {"violations": [{"code": "claim_display_mismatch"}]}
    script_gen._reconcile_display_numbers(script, report, cfg)
    assert script["scenes"][0]["milestone"] == {}          # unspoken -> hidden
    assert script["scenes"][1]["stat"]["value"] == 9200    # spoken -> kept
    assert script["scenes"][1]["visual_mode"] == "stat"


def test_reconcile_stat_without_spoken_number_falls_back_to_broll():
    import script_gen
    script = {"scenes": [
        {"n": 1, "narration": "दबाव हर सांस को कुचल देता है।",
         "visual_mode": "stat",
         "stat": {"value": 1100, "suffix": "atm", "label": "pressure"}}]}
    report = {"violations": [{"code": "claim_display_mismatch"}]}
    script_gen._reconcile_display_numbers(script, report, {})
    assert script["scenes"][0]["stat"] == {}
    assert script["scenes"][0]["visual_mode"] == "broll"


def test_reconcile_noop_without_c9_violation():
    import script_gen
    script = _c9_script()
    report = {"violations": [{"code": "engine_flat"}]}
    out = script_gen._reconcile_display_numbers(script, report, {})
    assert script["scenes"][0]["milestone"]["value"] == 1000000000.0
    assert out is report


# ---- variety engine (inauthentic-content policy, bucket 1) ----------------

def test_frame_signature_collapses_templated_titles():
    import script_gen as sg
    a = "11,034 मीटर की गहराई पर 1 घंटा: हर मिनट आपके शरीर के साथ क्या होगा?"
    b = "मंगल ग्रह की सतह पर 1 घंटा: हर 5 मिनट आपके शरीर के साथ क्या होगा?"
    c = "वैज्ञानिक इस जीव को बनाने से क्यों डरते हैं"
    assert sg._frame_signature(a) == sg._frame_signature(b)   # same template
    assert sg._frame_signature(c) != sg._frame_signature(a)   # different shape


def test_title_form_and_skeleton_rotate():
    import script_gen as sg, retention_lint as rl
    forms = {sg._title_form(i)[0] for i in range(len(sg.TITLE_FORMS))}
    assert len(forms) == len(sg.TITLE_FORMS)          # every form is reachable
    assert sg._title_form(0) != sg._title_form(1)     # consecutive differ
    skels = [rl.skeleton_for(i) for i in range(3)]
    assert len(set(skels)) == 3                       # three distinct shapes
    assert rl.skeleton_for(0) == rl.skeleton_for(3)   # deterministic cycle


def test_enforce_title_variety_swaps_templated_title():
    import script_gen as sg
    done = ["शुक्र ग्रह पर 1 घंटा: हर 5 मिनट आपके शरीर के साथ क्या होगा?"]
    script = {"title": "मंगल पर 1 घंटा: हर 5 मिनट आपके शरीर के साथ क्या होगा?",
              "title_options": ["वैज्ञानिक मंगल की मिट्टी से डरते हैं"]}
    sg._enforce_title_variety(script, done)
    assert script["title"] == "वैज्ञानिक मंगल की मिट्टी से डरते हैं"


def test_enforce_title_variety_leaves_distinct_title_alone():
    import script_gen as sg
    done = ["शुक्र ग्रह पर 1 घंटा: हर 5 मिनट आपके शरीर के साथ क्या होगा?"]
    script = {"title": "ब्लैक होल मरने के बाद उल्टा लौटता है",
              "title_options": ["कुछ और"]}
    sg._enforce_title_variety(script, done)
    assert script["title"] == "ब्लैक होल मरने के बाद उल्टा लौटता है"


def test_overused_family_is_detected():
    import script_gen as sg
    done = ["शरीर के साथ क्या होगा 1", "शरीर के साथ क्या होगा 2",
            "शरीर के साथ क्या होगा 3", "समुद्र का रहस्य"]
    assert "survival_timeline" in sg._overused_families(done)
    varied = ["समुद्र का रहस्य", "ब्रह्मांड की तुलना",
              "वैज्ञानिक बहस", "शरीर के साथ क्या होगा"]
    assert sg._overused_families(varied) == []


def test_skeleton_changes_the_reveal_window():
    import retention_lint as rl
    scenes = [{"narration": "w " * 12, "narrative_role": "hook"},
              {"narration": "w " * 12, "narrative_role": "main_reveal"},
              {"narration": "w " * 12, "narrative_role": "implication"},
              {"narration": "w " * 12, "narrative_role": "escalation"}]
    cfg = {}
    early = rl.lint({"skeleton": "reveal_first", "scenes": scenes,
                     "retention_plan": {"core_question": "q"}}, cfg)
    late = rl.lint({"skeleton": "journey", "scenes": scenes,
                    "retention_plan": {"core_question": "q"}}, cfg)
    codes_early = {v["code"] for v in early["violations"]}
    codes_late = {v["code"] for v in late["violations"]}
    # a reveal at 25% is valid for reveal_first, misplaced for journey
    assert "reveal_placement" not in codes_early
    assert "reveal_placement" in codes_late
    assert early["skeleton"] == "reveal_first"
