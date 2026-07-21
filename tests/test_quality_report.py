import json

import quality_report


def _manifest():
    return {
        "fps": 30, "width": 1920, "height": 1080, "xfadeFrames": 12,
        "outroSeconds": 4,
        "scenes": [{
            "n": 1, "audioDuration": 10,
            "visualBeats": [
                {"start": 0, "duration": 4, "cue": "एक", "searchTerms": ["earth"],
                 "assets": [{"path": "earth.mp4", "kind": "video"}]},
                {"start": 4, "duration": 6, "cue": "दो", "searchTerms": ["moon"],
                 "assets": [{"path": "moon.mp4", "kind": "video"}]},
            ],
        }],
    }


def test_manifest_audit_passes_complete_semantic_coverage():
    report = quality_report.audit_manifest(_manifest(), {})
    assert report["passed"] is True
    assert report["metrics"]["visual_beats"] == 2
    assert report["metrics"]["semantic_coverage"] == 1


def test_manifest_audit_catches_timing_gap():
    manifest = _manifest()
    manifest["scenes"][0]["visualBeats"][1]["start"] = 5
    report = quality_report.audit_manifest(manifest, {})
    assert report["passed"] is False
    assert any("coverage gap" in error for error in report["errors"])


def test_delivery_probe_is_fail_open_and_writes_report(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"video")

    def fail(*args, **kwargs):
        raise RuntimeError("ffprobe missing")

    monkeypatch.setattr(quality_report.subprocess, "run", fail)
    destination = tmp_path / "quality_report.json"
    report = quality_report.audit_delivery(str(video), _manifest(), {}, str(destination))
    assert report["passed"] is True
    assert "skipped" in report["warnings"][-1]
    assert json.loads(destination.read_text())["metrics"]["visual_beats"] == 2


# ---- India-targeted description + tags (run.build_description/_india_tags) ----

def _meta_ns():
    """Exec just run.py's metadata helpers (importing run.py pulls heavy deps)."""
    import os
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "pipeline", "run.py")).read()
    ns = {}
    exec(src[src.index("INDIA_DESC_HEADER = ("):src.index("def _asset_manifest")], ns)
    return ns


SCRIPT = {"description": "मंगल पर पहला कदम — फिर क्या होता है?",
          "tags": ["मंगल ग्रह", "mars surface", "अंतरिक्ष विज्ञान"]}


def test_description_leads_with_devanagari_and_ends_with_hashtags():
    ns = _meta_ns()
    out = ns["build_description"](SCRIPT, is_short=False, chapters="0:00 शुरुआत")
    assert out.startswith("\U0001F1EE\U0001F1F3")          # 🇮🇳 first
    assert "TERRA INCOGNITA" in out.split("\n")[0]
    assert "मंगल पर पहला कदम" in out                        # body preserved
    assert "0:00 शुरुआत" in out                             # chapters inline
    assert "सब्सक्राइब" in out                               # Hindi CTA
    assert out.rstrip().split("\n")[-1].startswith("#हिंदी")  # hashtags last


def test_short_description_has_shorts_hashtag_and_no_chapters():
    ns = _meta_ns()
    out = ns["build_description"](SCRIPT, is_short=True, chapters="0:00 x")
    assert "#shorts" in out
    assert "0:00 x" not in out


def test_tags_are_hindi_first_and_within_youtube_limit():
    ns = _meta_ns()
    tags = ns["_india_tags"](SCRIPT["tags"])
    assert tags[0] == "हिंदी में विज्ञान"        # evergreen Hindi leads
    assert "मंगल ग्रह" in tags                    # topic tags preserved
    assert "hindi science" in tags
    assert sum(len(t) + 2 for t in tags) <= 500   # YouTube hard limit
    assert len(tags) == len(set(t.lower() for t in tags))  # deduped


def test_short_tags_add_shorts_cluster():
    ns = _meta_ns()
    tags = ns["get_short_tags"](SCRIPT["tags"])
    assert "shorts" in tags and "hindi shorts" in tags


def test_tag_budget_never_exceeded_with_many_long_tags():
    ns = _meta_ns()
    tags = ns["_india_tags"]([f"बहुत लंबा टैग नंबर {i}" for i in range(40)])
    assert sum(len(t) + 2 for t in tags) <= 500
