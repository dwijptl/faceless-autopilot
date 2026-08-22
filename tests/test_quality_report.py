import json

import pytest

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


def test_manifest_audit_catches_frame_level_gap():
    manifest = _manifest()
    manifest["scenes"][0]["visualBeats"][0].update(
        {"fromFrame": 0, "durationFrames": 119})
    manifest["scenes"][0]["visualBeats"][1].update(
        {"fromFrame": 120, "durationFrames": 180})
    report = quality_report.audit_manifest(manifest, {})
    assert report["passed"] is False
    assert any("frame-level beat coverage gap" in error
               for error in report["errors"])


def test_manifest_audit_rejects_gradient_fallback_asset():
    manifest = _manifest()
    manifest["scenes"][0]["visualBeats"][0]["assets"] = [{
        "path": "s01_b00_card.jpg", "kind": "image", "fallback": "gradient",
    }]

    report = quality_report.audit_manifest(manifest, {})

    assert report["passed"] is False
    assert any("blank gradient fallback" in error for error in report["errors"])


def test_manifest_audit_flags_programmatic_fallback_for_review():
    manifest = _manifest()
    manifest["scenes"][0]["visualBeats"][0]["assets"] = [{
        "path": "s01_b00_fallback_graphic", "kind": "graphic",
        "fallback": "programmatic",
    }]

    report = quality_report.audit_manifest(manifest, {})

    assert report["passed"] is False
    assert any("animated evidence fallback requires review" in error
               for error in report["errors"])


def test_manifest_audit_flags_borrowed_visual_for_review():
    manifest = _manifest()
    manifest["scenes"][0]["visualBeats"][0]["assets"] = [{
        "path": "neighbor.jpg", "kind": "image", "borrowedFallback": True,
    }]

    report = quality_report.audit_manifest(manifest, {})

    assert report["passed"] is False
    assert any("borrowed visual requires review" in error
               for error in report["errors"])


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


def test_source_policy_violations_fail_quality_gate():
    manifest = {
        "fps": 30, "width": 1920, "height": 1080, "outroSeconds": 4,
        "scenes": [{"n": 1, "audioDuration": 4, "visualBeats": [
            {"start": 0, "duration": 4, "cue": "c", "searchTerms": ["t"],
             "family": "reconstruct_scene", "sourcePolicy": "custom",
             "assets": [{"path": "wrong-stock.mp4", "kind": "video",
                         "ai": False}]},
        ]}],
    }
    cfg = {"longform_quality": {"render_qc": {"enabled": True}},
           "visual_director": {"enabled": True, "min_custom_ratio": 0.0}}
    report = quality_report.audit_manifest(manifest, cfg)
    assert not report["passed"]
    assert any("custom reconstruction" in e for e in report["errors"])


# ---- India-targeted description + tags (run.build_description/_india_tags) ----

def _meta_ns():
    """Exec just run.py's metadata helpers (importing run.py pulls heavy deps)."""
    import os
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "pipeline", "run.py")).read()
    ns = {}
    exec(src[src.index("INDIA_DESC_HEADER = ("):src.index("def _asset_manifest")], ns)
    return ns


SCRIPT = {"description": "कोलकाता की रातों में पत्थर से हुए कत्लों के पीछे कौन था?",
          "tags": ["कोलकाता स्टोनमैन", "Kolkata Stoneman", "cold case India"]}


def test_description_leads_with_devanagari_and_ends_with_hashtags():
    ns = _meta_ns()
    out = ns["build_description"](SCRIPT, is_short=False, chapters="0:00 शुरुआत")
    assert out.startswith("सुरागनामा")
    assert "सुरागनामा" in out.split("\n")[0]
    assert "कोलकाता की रातों" in out                         # body preserved
    assert "0:00 शुरुआत" in out                             # chapters inline
    assert "सब्सक्राइब" in out                               # Hindi CTA
    assert out.rstrip().split("\n")[-1].startswith("#सुरागनामा")  # brand hashtag first


def test_short_description_has_shorts_hashtag_and_no_chapters():
    ns = _meta_ns()
    out = ns["build_description"](SCRIPT, is_short=True, chapters="0:00 x")
    assert "#shorts" in out
    assert "0:00 x" not in out


def test_tags_are_hindi_first_and_within_youtube_limit():
    ns = _meta_ns()
    tags = ns["_india_tags"](SCRIPT["tags"])
    assert tags[0] == "असली केस"                 # the case-file cluster leads
    assert "कोलकाता स्टोनमैन" in tags             # topic tags preserved
    assert "hindi mystery" in tags
    assert sum(len(t) + 2 for t in tags) <= 500   # YouTube hard limit
    assert len(tags) == len(set(t.lower() for t in tags))  # deduped


def test_short_tags_add_shorts_cluster():
    ns = _meta_ns()
    tags = ns["get_short_tags"](SCRIPT["tags"])
    assert "shorts" in tags and "hindi shorts" in tags
    assert "रहस्य शॉर्ट्स" in tags
    assert "विज्ञान शॉर्ट्स" not in tags


def test_tag_budget_never_exceeded_with_many_long_tags():
    ns = _meta_ns()
    tags = ns["_india_tags"]([f"बहुत लंबा टैग नंबर {i}" for i in range(40)])
    assert sum(len(t) + 2 for t in tags) <= 500


# ── delivered-pixel blank-frame detector ──────────────────────────────────

def _stats(spans, sample_fps=6):
    """Fake ffmpeg signalstats output: one sample per luma span."""
    step = 1.0 / sample_fps
    out = []
    for index, span in enumerate(spans):
        out.append(f"frame:{index} pts:{index} pts_time:{index * step:.4f}")
        out.append("lavfi.signalstats.YMIN=10.0")
        out.append(f"lavfi.signalstats.YMAX={10.0 + span:.1f}")
        out.append("lavfi.signalstats.YAVG=40.0")
    return "\n".join(out) + "\n"


def test_blank_scan_flags_a_sustained_solid_run():
    # 12 flat samples at 6 fps = 2.0s of solid frames between real footage
    spans = [180.0] * 6 + [8.0] * 12 + [200.0] * 6
    runs = quality_report._flat_runs_from_stats(_stats(spans), 6, 32, 0.6)
    assert len(runs) == 1
    start, end = runs[0]
    assert round(start, 2) == 1.0
    assert round(end - start, 2) == 2.0


def test_blank_scan_ignores_a_short_dip():
    # two flat samples (0.33s) — a crossfade, not a missing visual
    spans = [180.0] * 6 + [8.0] * 2 + [180.0] * 6
    assert quality_report._flat_runs_from_stats(_stats(spans), 6, 32, 0.6) == []


def test_blank_scan_reports_a_trailing_run():
    spans = [180.0] * 4 + [5.0] * 8
    runs = quality_report._flat_runs_from_stats(_stats(spans), 6, 32, 0.6)
    assert len(runs) == 1
    assert round(runs[0][1] - runs[0][0], 2) == pytest.approx(1.33, abs=0.01)


def test_blank_scan_finds_every_separate_run():
    spans = ([150.0] * 6 + [6.0] * 9) * 2
    runs = quality_report._flat_runs_from_stats(_stats(spans), 6, 32, 0.6)
    assert len(runs) == 2


def test_blank_scan_disabled_by_config(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("ffmpeg invoked while the scan is disabled")
    monkeypatch.setattr(quality_report.subprocess, "run", explode)
    cfg = {"longform_quality": {"render_qc": {"blank_frames": {"enabled": False}}}}
    assert quality_report._flat_frame_runs("final.mp4", cfg) == ([], "")


def test_blank_scan_fails_open_when_ffmpeg_is_missing(monkeypatch):
    def explode(*args, **kwargs):
        raise FileNotFoundError("ffmpeg")
    monkeypatch.setattr(quality_report.subprocess, "run", explode)
    runs, note = quality_report._flat_frame_runs("final.mp4", {})
    assert runs == []
    assert "blank-frame scan skipped" in note


def test_delivery_audit_drafts_release_on_blank_frames(monkeypatch, tmp_path):
    monkeypatch.setattr(quality_report, "_flat_frame_runs",
                        lambda path, cfg: ([(149.9, 152.77)], ""))
    report = quality_report.audit_delivery(
        "missing.mp4", _manifest(), {}, str(tmp_path / "report.json"))
    assert report["passed"] is False
    assert any("blank/solid frame 149.90s-152.77s" in e for e in report["errors"])
    assert report["delivery"]["blank_frame_spans"] == [[149.9, 152.77]]
