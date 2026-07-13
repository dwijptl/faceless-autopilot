"""Fail-open automated quality report for long-form manifests and delivery."""
from __future__ import annotations

import json
import os
import subprocess


def _expected_duration(manifest: dict) -> float:
    scenes = manifest.get("scenes", [])
    xfade = float(manifest.get("xfadeFrames", 0)) / max(float(manifest.get("fps", 30)), 1)
    return (sum(float(s.get("audioDuration", 0)) for s in scenes)
            + float(manifest.get("outroSeconds", 0)) - xfade * len(scenes))


def audit_manifest(manifest: dict, cfg: dict) -> dict:
    settings = cfg.get("longform_quality", {}).get("render_qc", {})
    if not settings.get("enabled", True):
        return {"passed": True, "errors": [], "warnings": ["quality audit disabled"],
                "metrics": {"visual_beats": 0, "semantic_coverage": 0,
                            "unique_assets": 0}}
    errors, warnings = [], []
    asset_uses: dict[str, int] = {}
    beat_count = 0
    aligned_beats = 0

    for scene in manifest.get("scenes", []):
        duration = float(scene.get("audioDuration", 0))
        beats = scene.get("visualBeats") or []
        if duration > 12 and not beats:
            errors.append(f"scene {scene.get('n')}: no semantic visual beats")
        cursor = 0.0
        for beat in beats:
            beat_count += 1
            start = float(beat.get("start", 0))
            length = float(beat.get("duration", 0))
            if abs(start - cursor) > 0.08:
                errors.append(f"scene {scene.get('n')}: beat coverage gap")
            cursor = start + length
            if beat.get("cue") and beat.get("searchTerms"):
                aligned_beats += 1
            if not beat.get("assets"):
                warnings.append(f"scene {scene.get('n')}: beat has fallback-only visual")
            for asset in beat.get("assets", []):
                key = os.path.basename(str(asset.get("path", "")))
                asset_uses[key] = asset_uses.get(key, 0) + 1
        if beats and abs(cursor - duration) > 0.12:
            errors.append(f"scene {scene.get('n')}: beats do not cover narration")

    repeat_limit = int(settings.get("max_asset_uses", 2))
    repeated = {k: v for k, v in asset_uses.items() if k and v > repeat_limit}
    if repeated:
        warnings.append(f"assets reused more than {repeat_limit} times: {repeated}")
    coverage = aligned_beats / max(beat_count, 1)
    if beat_count and coverage < float(settings.get("min_semantic_coverage", 0.9)):
        errors.append(f"semantic beat coverage only {coverage:.0%}")

    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {"visual_beats": beat_count,
                    "semantic_coverage": round(coverage, 3),
                    "unique_assets": len(asset_uses)},
    }


def audit_delivery(path: str, manifest: dict, cfg: dict, report_path: str) -> dict:
    """Add ffprobe delivery facts, preserving the render if probing fails."""
    report = audit_manifest(manifest, cfg)
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_streams", "-show_format",
            "-of", "json", path,
        ], capture_output=True, text=True, check=True, timeout=120)
        probe = json.loads(result.stdout)
        streams = probe.get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
        actual = float(probe.get("format", {}).get("duration", 0))
        expected = _expected_duration(manifest)
        delivery = {
            "duration": round(actual, 3), "expected_duration": round(expected, 3),
            "width": video.get("width"), "height": video.get("height"),
            "video_codec": video.get("codec_name"), "audio_codec": audio.get("codec_name"),
            "file_bytes": os.path.getsize(path),
        }
        report["delivery"] = delivery
        if not video:
            report["errors"].append("delivery has no video stream")
        if not audio:
            report["errors"].append("delivery has no audio stream")
        if actual and expected and abs(actual - expected) > 1.5:
            report["errors"].append("delivery duration differs from manifest")
        if (video.get("width"), video.get("height")) != (
                int(manifest.get("width", 0)), int(manifest.get("height", 0))):
            report["errors"].append("delivery resolution differs from manifest")
    except Exception as exc:
        report["warnings"].append(f"ffprobe delivery check skipped: {exc}")
    report["passed"] = not report["errors"]
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(f"[quality] {'PASS' if report['passed'] else 'REVIEW'} — "
          f"{report['metrics']['visual_beats']} semantic beats, "
          f"{len(report['errors'])} errors, {len(report['warnings'])} warnings")
    return report
