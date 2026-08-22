"""Fail-open automated quality report for long-form manifests and delivery."""
from __future__ import annotations

import json
import os
import re
import subprocess

import families as families_mod

# families whose repetition is legitimate (continuous chains)
_CHAIN_FAMILIES = {"descend", "ascend_return", "timeline_advance",
                   "penetrate_layers"}


def _audit_director(manifest: dict, cfg: dict,
                    errors: list, warnings: list) -> dict:
    """Narrative-intent semantic audit — replaces checkbox coverage with
    questions a human editor would ask: does every beat have a story
    function, is the episode custom-visual first (AI + programmatic vs raw
    stock), and does any family drone on? Fail-open: warnings by default."""
    vd = (cfg or {}).get("visual_director", {}) or {}
    beat_total = 0
    tagged = 0
    media = {"ai": 0, "graphic": 0, "stock_video": 0, "stock_image": 0}
    prev_family, run_len = None, 0
    for scene in manifest.get("scenes", []):
        for beat in scene.get("visualBeats") or []:
            beat_total += 1
            family = str(beat.get("family", ""))
            if family:
                tagged += 1
            if family and family == prev_family:
                run_len += 1
                if run_len == 3 and family not in _CHAIN_FAMILIES:
                    warnings.append(
                        f"family '{family}' repeats 3+ beats in a row "
                        f"(scene {scene.get('n')}) — vary the story function")
            else:
                prev_family, run_len = family, 1
            for asset in beat.get("assets") or []:
                kind = str(asset.get("kind", ""))
                if kind == "graphic":
                    media["graphic"] += 1
                elif asset.get("ai"):
                    media["ai"] += 1
                elif kind == "video":
                    media["stock_video"] += 1
                else:
                    media["stock_image"] += 1
            policy = str(beat.get("sourcePolicy", ""))
            beat_assets = beat.get("assets") or []
            if policy == "custom" and not any(
                    a.get("ai") or a.get("kind") == "graphic"
                    for a in beat_assets):
                errors.append(
                    f"scene {scene.get('n')}: custom reconstruction beat "
                    "fell back to generic stock/card")
            if policy == "primary":
                if any(a.get("ai") for a in beat_assets):
                    errors.append(
                        f"scene {scene.get('n')}: primary-source beat uses AI")
                if any(str(a.get("path", "")).endswith("_card.jpg")
                       for a in beat_assets):
                    errors.append(
                        f"scene {scene.get('n')}: primary-source beat has no "
                        "authentic asset")
    total_assets = max(sum(media.values()), 1)
    custom_ratio = (media["ai"] + media["graphic"]) / total_assets
    coverage = tagged / max(beat_total, 1)
    if beat_total:
        min_cov = float(vd.get("min_family_coverage", 0.85))
        if coverage < min_cov:
            warnings.append(f"only {coverage:.0%} of beats carry a "
                            f"narrative-intent family (want {min_cov:.0%})")
        min_custom = float(vd.get("min_custom_ratio", 0.45))
        if custom_ratio < min_custom:
            message = (f"custom visuals (AI + programmatic) are only "
                       f"{custom_ratio:.0%} of beat assets "
                       f"(want {min_custom:.0%}) — episode leans stock-first")
            (errors if vd.get("strict_custom_ratio", False)
             else warnings).append(message)
    return {"family_coverage": round(coverage, 3),
            "custom_visual_ratio": round(custom_ratio, 3),
            "media_mix": media}


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
        fps = max(int(manifest.get("fps", 30)), 1)
        scene_frames = max(int(duration * fps + 0.5), 1)
        beats = scene.get("visualBeats") or []
        if duration > 12 and not beats:
            errors.append(f"scene {scene.get('n')}: no semantic visual beats")
        cursor = 0.0
        frame_cursor = 0
        for beat in beats:
            beat_count += 1
            start = float(beat.get("start", 0))
            length = float(beat.get("duration", 0))
            if abs(start - cursor) > 0.08:
                errors.append(f"scene {scene.get('n')}: beat coverage gap")
            cursor = start + length
            if "fromFrame" in beat or "durationFrames" in beat:
                from_frame = int(beat.get("fromFrame", -1))
                frame_length = int(beat.get("durationFrames", 0))
                if from_frame != frame_cursor or frame_length < 1:
                    errors.append(
                        f"scene {scene.get('n')}: frame-level beat coverage gap")
                frame_cursor = from_frame + frame_length
            if beat.get("cue") and beat.get("searchTerms"):
                aligned_beats += 1
            if not beat.get("assets"):
                warnings.append(f"scene {scene.get('n')}: beat has fallback-only visual")
            for asset in beat.get("assets", []):
                key = os.path.basename(str(asset.get("path", "")))
                asset_uses[key] = asset_uses.get(key, 0) + 1
                if (asset.get("fallback") == "gradient"
                        or key.endswith("_card.jpg")):
                    errors.append(
                        f"scene {scene.get('n')}: blank gradient fallback "
                        "reached render manifest")
                elif asset.get("fallback") == "programmatic":
                    errors.append(
                        f"scene {scene.get('n')}: media lookup failed; "
                        "animated evidence fallback requires review")
                elif asset.get("borrowedFallback"):
                    errors.append(
                        f"scene {scene.get('n')}: media lookup failed; "
                        "borrowed visual requires review")
        if beats and abs(cursor - duration) > 0.12:
            errors.append(f"scene {scene.get('n')}: beats do not cover narration")
        if (beats and any("fromFrame" in beat or "durationFrames" in beat
                          for beat in beats) and frame_cursor != scene_frames):
            errors.append(
                f"scene {scene.get('n')}: frame beats do not cover narration")

    repeat_limit = int(settings.get("max_asset_uses", 2))
    repeated = {k: v for k, v in asset_uses.items() if k and v > repeat_limit}
    if repeated:
        warnings.append(f"assets reused more than {repeat_limit} times: {repeated}")
    coverage = aligned_beats / max(beat_count, 1)
    if beat_count and coverage < float(settings.get("min_semantic_coverage", 0.9)):
        errors.append(f"semantic beat coverage only {coverage:.0%}")

    metrics = {"visual_beats": beat_count,
               "semantic_coverage": round(coverage, 3),
               "unique_assets": len(asset_uses)}
    if families_mod.enabled(cfg):
        metrics["director"] = _audit_director(manifest, cfg, errors, warnings)

    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


# ── delivered-pixel blank-frame detector ──────────────────────────────────
# The manifest guards (run._validate_scene_assets and
# run._assert_render_visual_coverage) stop a blank visual before Remotion is
# ever invoked.  This is the last line of defence, and the only one that reads
# the frames a viewer would actually see: a shot that renders as nothing —
# a missing still, a beat left uncovered, a solid-colour card from an older
# manifest — leaves the scene background exposed as a flat frame.
_BLANK_DEFAULTS = {
    "enabled": True,
    "sample_fps": 6,        # 6 samples/s resolves any run >= min_seconds
    "max_luma_span": 32,    # 8-bit Y range inside the crop; real footage >> 100
    "min_seconds": 0.6,     # longer than the 0.4s scene crossfade
}

# Crop away the burned-in HUD (top bar, corner brackets, caption band, counter)
# so chrome drawn over an empty scene cannot disguise it as a busy frame.
_BLANK_CROP = "crop=iw*0.6:ih*0.45:iw*0.2:ih*0.12"


def _blank_settings(cfg: dict) -> dict:
    settings = dict(_BLANK_DEFAULTS)
    override = ((cfg or {}).get("longform_quality", {})
                .get("render_qc", {}).get("blank_frames", {})) or {}
    settings.update(override)
    return settings


def _flat_runs_from_stats(stats: str, sample_fps: float, max_span: float,
                          min_seconds: float) -> list[tuple[float, float]]:
    """Group consecutive flat samples into (start, end) second ranges.

    Pure parser over ffmpeg ``signalstats`` metadata so the run-grouping rules
    stay unit-testable without invoking ffmpeg.
    """
    times: list[float] = []
    spans: list[float] = []
    current: dict[str, float] = {}

    def flush() -> None:
        if "t" in current and "YMIN" in current and "YMAX" in current:
            times.append(current["t"])
            spans.append(current["YMAX"] - current["YMIN"])

    for line in stats.splitlines():
        line = line.strip()
        match = re.match(r"^frame:\d+\s+pts:\S+\s+pts_time:([\d.]+)", line)
        if match:
            flush()
            current = {"t": float(match.group(1))}
            continue
        if current and line.startswith("lavfi.signalstats."):
            key, _, value = line.partition("=")
            key = key.replace("lavfi.signalstats.", "")
            if key in ("YMIN", "YMAX"):
                try:
                    current[key] = float(value)
                except ValueError:
                    pass
    flush()

    step = 1.0 / max(float(sample_fps), 0.001)
    runs: list[tuple[float, float]] = []
    start: float | None = None
    previous = 0.0
    for moment, span in zip(times, spans):
        if span <= max_span:
            if start is None:
                start = moment
            previous = moment
        elif start is not None:
            runs.append((start, previous + step))
            start = None
    if start is not None:
        runs.append((start, previous + step))
    return [(s, e) for s, e in runs if e - s >= min_seconds]


def _flat_frame_runs(path: str, cfg: dict) -> tuple[list[tuple[float, float]], str]:
    """Scan the delivered file for runs of flat/solid frames.

    Returns the offending ranges plus a note when the scan could not run —
    an ffmpeg that is missing or unhappy must not fail an otherwise good
    render, so the caller records a warning instead.
    """
    settings = _blank_settings(cfg)
    if not settings.get("enabled", True):
        return [], ""
    sample_fps = float(settings.get("sample_fps", 6))
    filters = (f"fps={sample_fps:g},{_BLANK_CROP},scale=160:90,"
               "signalstats,metadata=print:file=-")
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", path, "-an", "-vf", filters,
             "-f", "null", "-"],
            capture_output=True, text=True, check=True, timeout=1800)
    except Exception as exc:
        return [], f"blank-frame scan skipped: {exc}"
    return _flat_runs_from_stats(
        result.stdout, sample_fps,
        float(settings.get("max_luma_span", 32)),
        float(settings.get("min_seconds", 0.6))), ""


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

    blank_runs, blank_note = _flat_frame_runs(path, cfg)
    if blank_note:
        report["warnings"].append(blank_note)
    for start, end in blank_runs:
        report["errors"].append(
            f"delivery shows a blank/solid frame {start:.2f}s-{end:.2f}s "
            f"({end - start:.2f}s) — a visual failed to reach the render")
    report.setdefault("delivery", {})["blank_frame_spans"] = [
        [round(start, 2), round(end, 2)] for start, end in blank_runs]

    report["passed"] = not report["errors"]
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(f"[quality] {'PASS' if report['passed'] else 'REVIEW'} — "
          f"{report['metrics']['visual_beats']} semantic beats, "
          f"{len(report['errors'])} errors, {len(report['warnings'])} warnings")
    return report
