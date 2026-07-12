import os

import postprocess


def test_master_delivery_normalizes_audio_and_preserves_video(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"original")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        with open(cmd[-1], "wb") as output:
            output.write(b"m" * 250_000)

    monkeypatch.setattr(postprocess.subprocess, "run", fake_run)
    assert postprocess.master_delivery(str(video), {"audio_mastering": {
        "enabled": True, "target_lufs": -14, "true_peak_db": -1.5, "lra": 7}})
    assert os.path.getsize(video) == 250_000
    command = " ".join(captured["cmd"])
    assert "loudnorm=I=-14.0:TP=-1.5:LRA=7.0" in command
    assert "-c:v copy" in command
    assert "h264_metadata" in command
    assert "bt709" in command


def test_master_delivery_fails_open(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"original")

    def fail(*args, **kwargs):
        raise RuntimeError("ffmpeg unavailable")

    monkeypatch.setattr(postprocess.subprocess, "run", fail)
    assert postprocess.master_delivery(str(video), {}) is False
    assert video.read_bytes() == b"original"
