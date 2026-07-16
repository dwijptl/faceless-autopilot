import json
import os

import calibration


def test_record_and_measure(tmp_path):
    root = str(tmp_path)
    assert calibration.measured_wpm(root, 130, "long") is None  # no data
    calibration.record(root, "long", 600, 240.0, "a")   # 150 wpm
    assert calibration.measured_wpm(root, 130, "long") is None  # 1 entry
    calibration.record(root, "long", 620, 240.0, "b")   # 155 wpm
    calibration.record(root, "long", 580, 240.0, "c")   # 145 wpm
    got = calibration.measured_wpm(root, 130, "long")
    assert got == 150  # median

    # kinds are separate
    assert calibration.measured_wpm(root, 100, "short") is None


def test_clamped_to_configured_band(tmp_path):
    root = str(tmp_path)
    calibration.record(root, "long", 1000, 240.0, "a")  # 250 wpm (absurd)
    calibration.record(root, "long", 1000, 240.0, "b")
    got = calibration.measured_wpm(root, 130, "long")
    assert got == int(130 * 1.25)  # clamped, never trusted blindly


def test_bad_measurements_ignored(tmp_path):
    root = str(tmp_path)
    assert calibration.record(root, "long", 0, 240.0) is None
    assert calibration.record(root, "long", 500, 5.0) is None
    assert calibration.measured_wpm(root, 130, "long") is None


def test_file_stays_bounded(tmp_path):
    root = str(tmp_path)
    for i in range(80):
        calibration.record(root, "long", 600, 240.0, str(i))
    with open(os.path.join(root, calibration.FILENAME), encoding="utf-8") as f:
        assert len(json.load(f)) <= calibration.MAX_ENTRIES
