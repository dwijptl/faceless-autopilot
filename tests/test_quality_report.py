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
