"""Final delivery mastering shared by long-form and Shorts."""
import os
import subprocess


def master_delivery(path: str, cfg: dict) -> bool:
    """Normalize the mix and attach Rec.709 delivery metadata, fail-open."""
    settings = cfg.get("audio_mastering", {})
    if not settings.get("enabled", True):
        return False
    target = float(settings.get("target_lufs", -14.0))
    true_peak = float(settings.get("true_peak_db", -1.5))
    lra = float(settings.get("lra", 7.0))
    stem, ext = os.path.splitext(path)
    temp = f"{stem}.mastered{ext or '.mp4'}"
    cmd = [
        "ffmpeg", "-y", "-v", "warning", "-i", path,
        "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
        "-bsf:v", ("h264_metadata=video_full_range_flag=0:colour_primaries=1:"
                   "transfer_characteristics=1:matrix_coefficients=1"),
        "-af", f"loudnorm=I={target}:TP={true_peak}:LRA={lra}",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
        "-color_primaries", "bt709", "-color_trc", "bt709",
        "-colorspace", "bt709", "-color_range", "tv", temp,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=1200)
        if not os.path.exists(temp) or os.path.getsize(temp) < 200_000:
            raise RuntimeError("mastered output missing or too small")
        os.replace(temp, path)
        print(f"[master] {target:g} LUFS, {true_peak:g} dBTP, Rec.709 metadata")
        return True
    except Exception as exc:
        print(f"[master] skipped ({exc}) — preserving original render")
        try:
            if os.path.exists(temp):
                os.remove(temp)
        except OSError:
            pass
        return False
