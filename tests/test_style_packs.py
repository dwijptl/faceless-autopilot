import style_packs


def test_only_documentary_style_remains():
    assert set(style_packs.PACKS) == {"documentary"}
    assert style_packs.select("any topic") == "documentary"
    assert style_packs.base_for("old-style-name") == "documentary"


def test_documentary_image_direction_is_full_frame_and_plain():
    wrapper = style_packs.wrapper_for("anything")
    assert "documentary photography" in wrapper
    assert "full-frame" in wrapper
    assert style_packs.frames_for("documentary") == ()
    assert style_packs.lower_thirds_for("documentary") == ()
