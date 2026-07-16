import analytics


CURVE_CSV = """Video position (%),Absolute audience retention (%)
0,100
10,80
20,70
50,50
80,40
100,30
"""

BEATS_DOC = {
    "stamp": "2026-07-20_0830",
    "title": "test video",
    "style": "noir",
    "beats": [
        {"n": 1, "title": "hook", "start": 0.0, "end": 30.0,
         "narrativeRole": "hook", "visualMode": "broll", "delivery": "hook"},
        {"n": 2, "title": "middle", "start": 30.0, "end": 60.0,
         "narrativeRole": "explanation", "visualMode": "stat",
         "delivery": "calm"},
        {"n": 3, "title": "end", "start": 60.0, "end": 100.0,
         "narrativeRole": "main_reveal", "visualMode": "glass",
         "delivery": "reveal"},
    ],
}


def _curve(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text(CURVE_CSV, encoding="utf-8")
    return analytics.parse_retention_csv(str(p))


def test_parse_retention_csv_normalizes(tmp_path):
    curve = _curve(tmp_path)
    assert curve[0] == (0.0, 1.0)
    assert curve[-1] == (1.0, 0.3)
    assert all(0 <= p <= 1 for p, _ in curve)


def test_parse_retention_csv_rejects_garbage(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("hello,world\nfoo,bar\n", encoding="utf-8")
    assert analytics.parse_retention_csv(str(p)) == []


def test_interpolation():
    curve = [(0.0, 1.0), (0.5, 0.5), (1.0, 0.3)]
    assert analytics._retention_at(curve, 0.25) == 0.75
    assert analytics._retention_at(curve, 0.75) == 0.4
    assert analytics._retention_at(curve, 2.0) == 0.3


def test_join_retention_computes_drop(tmp_path):
    joined = analytics.join_retention(BEATS_DOC, _curve(tmp_path))
    assert len(joined) == 3
    hook = joined[0]
    # scene 1 covers positions 0 -> 0.3: retention 1.0 -> ~0.64
    assert hook["retentionIn"] == 1.0
    assert 0.6 < hook["retentionOut"] < 0.7
    assert hook["dropPerMinute"] > joined[2]["dropPerMinute"]
    assert joined[1]["narrativeRole"] == "explanation"


def test_join_handles_empty_inputs():
    assert analytics.join_retention({"beats": []}, [(0, 1), (1, 0.5)]) == []
    assert analytics.join_retention(BEATS_DOC, []) == []


def test_retention_brief_and_min_sample_guard():
    videos = []
    for k in range(3):  # below MIN_VIDEOS_PER_PATTERN
        scenes = [{"n": 1, "title": "x", "start": 0, "end": 30,
                   "narrativeRole": "hook", "visualMode": "broll",
                   "delivery": "hook", "rewardType": "",
                   "retentionIn": 1.0, "retentionOut": 0.6,
                   "dropPerMinute": 0.8}]
        videos.append({"stamp": f"s{k}", "title": "t", "style": "noir",
                       "scenes": scenes, "worst_scene": scenes[0]})
    joins = {"videos": videos, "aggregates": {"narrativeRole": {}},
             "min_videos_per_pattern": analytics.MIN_VIDEOS_PER_PATTERN}
    brief = analytics.retention_brief(joins)
    assert "worst scene 1" in brief
    assert "BEAT-LEVEL RETENTION JOIN (3 video(s)" in brief
    assert analytics.retention_brief({"videos": []}) == ""
