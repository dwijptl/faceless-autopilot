import factcheck
import run


def _script():
    return {"scenes": [{"n": 1, "narration": "यह संख्या 100 है।"}]}


def test_factcheck_softens_mocked_unsupported_claim(monkeypatch):
    monkeypatch.setattr(factcheck, "_plain_json", lambda *args: {"claims": [{"scene": 1, "text": "संख्या 100"}]})
    monkeypatch.setattr(factcheck, "_grounded_json", lambda *args: (
        {"results": [{"verdict": "needs_softening", "replacement": "संख्या लगभग सौ", "note": "estimate"}]}, ["https://example.com"]))
    script = _script()
    report = factcheck.check_script(script, {"factcheck": {"enabled": True, "max_claims": 8},
                                             "llm": {"model": "x", "fallback_models": []}}, "key")
    assert report["softened"] == 1
    assert "लगभग सौ" in script["scenes"][0]["narration"]


def test_factcheck_fails_open(monkeypatch):
    monkeypatch.setattr(factcheck, "_plain_json", lambda *args: (_ for _ in ()).throw(RuntimeError("down")))
    script = _script()
    report = factcheck.check_script(script, {"factcheck": {"enabled": True},
                                             "llm": {"model": "x", "fallback_models": []}}, "key")
    assert report["status"].startswith("skipped")
    assert script == _script()


def test_factcheck_verifies_claims_in_bounded_batches(monkeypatch):
    claims = [{"scene": 1, "text": f"claim {i}"} for i in range(17)]
    monkeypatch.setattr(factcheck, "_plain_json", lambda *args: {"claims": claims})
    batches = []

    def grounded(prompt, cfg, key):
        import re
        found = re.findall(r'"text":\s*"claim \d+"', prompt)
        batches.append(len(found))
        return ({"results": [{"verdict": "supported", "replacement": "x",
                               "risk": "normal", "basis": "documented",
                               "note": "ok"} for _ in found]},
                [f"https://example.com/{len(batches)}"])

    monkeypatch.setattr(factcheck, "_grounded_json", grounded)
    report = factcheck.check_script(
        _script(), {"factcheck": {"enabled": True, "max_claims": 24,
                                   "batch_size": 8},
                    "llm": {"model": "x", "fallback_models": []}}, "key")
    assert batches == [8, 8, 1]
    assert report["checked"] == 17
    assert len(report["sources"]) == 3


def test_required_factcheck_failure_blocks_publication():
    cfg = {"factcheck": {"required": True, "gate": True}}
    assert run._fact_requires_review({"status": "skipped (timeout)",
                                      "unsupported": 0}, cfg)
    assert run._fact_requires_review({"status": "ok", "unsupported": 1}, cfg)
    assert not run._fact_requires_review({"status": "ok", "unsupported": 0}, cfg)
