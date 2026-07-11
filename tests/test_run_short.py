import pytest

import run_short


def test_main_initializes_short_config_before_key_validation(monkeypatch):
    """Guard against local variables shadowing the short_cfg helper."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="Missing GEMINI_API_KEY or PEXELS_API_KEY"):
        run_short.main()
