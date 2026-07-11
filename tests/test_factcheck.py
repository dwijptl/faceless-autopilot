import factcheck


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
