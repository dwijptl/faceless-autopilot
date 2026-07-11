import captions


def test_caption_timings_are_monotonic_and_bounded():
    scenes = [{"narration": "यह एक छोटा परीक्षण वाक्य है।",
               "audio_duration": 4.0, "start": 1.0}]
    events, _ = captions.build_captions(scenes, 12)
    assert events
    assert all(1.0 <= start < end <= 5.0 for start, end, _ in events)


def test_caption_uses_word_timings_when_counts_match():
    scene = {"narration": "एक दो तीन चार", "audio_duration": 4.0, "start": 10.0,
             "word_times": [("एक", 0, .5), ("दो", .5, 1),
                            ("तीन", 1, 1.5), ("चार", 1.5, 2)]}
    events, _ = captions.build_captions([scene], 7)
    assert events[0][0] == 10.0
    assert events[-1][1] == 12.0


def test_caption_rejects_mismatched_transcript_timings():
    scene = {"narration": "एक दो तीन चार", "audio_duration": 4.0, "start": 0,
             "word_times": [("एक", 0, .5)]}
    events, _ = captions.build_captions([scene], 30)
    assert events[0][1] > 3.0  # heuristic path covers the scene
