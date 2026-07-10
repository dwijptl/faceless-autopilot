"""Manual smoke test — synthesizes one Hindi line with the configured voice.

Run from the Actions tab → "Test Voice" → Run workflow. The finished WAV is
attached to the run as an artifact so you can listen before a full video.

The workflow sets TTS_NO_FALLBACK=1, so this FAILS LOUDLY on Sarvam problems
(bad key, empty credits, wrong speaker ID) instead of silently using Kokoro.
"""
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(__file__))
import tts as tts_mod  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TEXT = (
    "नमस्ते! यह टेरा इनकॉग्निटा की आवाज़ की जाँच है। "
    "धरती पर कुछ जगहें ऐसी हैं, जो हर नक्शे से बाहर रह जाती हैं। "
    "अगर यह आवाज़ आपकी अपनी क्लोन आवाज़ जैसी लगती है, तो सब कुछ तैयार है।"
)


def main() -> None:
    with open(os.path.join(REPO_ROOT, "config.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    text = os.environ.get("TEST_TEXT", "").strip() or DEFAULT_TEXT
    outdir = os.path.join(REPO_ROOT, "out", "voice_test")
    os.makedirs(outdir, exist_ok=True)
    wav = os.path.join(outdir, "voice_test.wav")

    dur = tts_mod.synth_scene(text, wav, cfg)
    print(f"[test] OK — {dur:.1f}s of audio -> {wav}")
    print(f"[test] {tts_mod.usage_summary()}")


if __name__ == "__main__":
    main()
