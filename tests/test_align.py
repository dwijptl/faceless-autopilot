import align


def test_read_word_times_offsets_window():
    payload = {"timestamps": {"words": ["एक", "दो"],
                              "start_time_seconds": [0, .5],
                              "end_time_seconds": [.5, 1]}}
    assert align._read_word_times(payload, 10) == [("एक", 10.0, 10.5), ("दो", 10.5, 11.0)]


def test_alignment_fails_open_without_key(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    assert align.scene_word_times({}, {"captions": {"align": True}}) is None
