import numpy as np

import tts


def test_sentence_chunking_under_limit():
    assert tts._sentences("एक। दो!") == ["एक।", "दो!"]
    assert all(len(c) <= 5 for c in tts._chunks("एक। दो। तीन।", 5))


def test_sarvam_failure_sets_fallback_flag(monkeypatch, tmp_path):
    tts.reset_run_state()
    monkeypatch.delenv("TTS_NO_FALLBACK", raising=False)
    monkeypatch.setattr(tts, "_synth_sarvam", lambda *args: (_ for _ in ()).throw(RuntimeError("nope")))
    monkeypatch.setattr(tts, "_synth_kokoro", lambda *args: np.ones(100, dtype=np.float32))
    cfg = {"tts": {"engine": "sarvam", "speed": 1, "sarvam_model": "bulbul:v3"},
           "channel": {"language": "hi-IN"}}
    tts.synth_scene("नमस्ते", str(tmp_path / "voice.wav"), cfg)
    assert tts.fallback_used()


def test_tail_seconds_controls_scene_duration(monkeypatch, tmp_path):
    monkeypatch.setattr(tts, "_synth_kokoro",
                        lambda *args: np.ones(tts.SAMPLE_RATE, dtype=np.float32))
    cfg = {"tts": {"engine": "kokoro", "speed": 1},
           "channel": {"language": "hi-IN"}}
    full = tts.synth_scene("x", str(tmp_path / "full.wav"), cfg,
                           tail_seconds=0.35)
    loop = tts.synth_scene("x", str(tmp_path / "loop.wav"), cfg,
                           tail_seconds=0.06)
    assert 0.28 < full - loop < 0.30
