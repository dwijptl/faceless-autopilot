"""Deterministic opening/title contracts for Shorts.

`_enforce_short_payoff` has guarded the END of a Short since the Venus run.
These cover the two ends nobody was checking: the opening (the channel's 24s
Short averaged 3.6s of view time — viewers left before the first sentence
finished) and the title's promise scope.
"""
import pytest

import script_gen
import topic_shape as ts


def _script(hook, **extra):
    s = {"title": "एक दावा", "scenes": [{"n": 1, "narration": hook},
                                        {"n": 2, "narration": "दूसरा सीन"}]}
    s.update(extra)
    return s


@pytest.mark.parametrize("opener", [
    "नमस्कार दोस्तों, आज हम समुद्र की गहराई देखेंगे।",
    "क्या आप जानते हैं कि समुद्र की गहराई 11 किमी है?",
    "आइए जानते हैं समुद्र का सबसे गहरा राज़।",
    "Did you know the trench is 11 km deep?",
    "इस वीडियो में हम गहराई की बात करेंगे।",
])
def test_stock_openers_are_stripped(opener):
    s = _script(opener)
    script_gen._enforce_short_hook(s)
    got = s["scenes"][0]["narration"]
    assert got
    assert not script_gen._BANNED_OPENER.match(got), got


def test_stacked_openers_are_stripped_in_one_pass():
    s = _script("नमस्कार दोस्तों, क्या आप जानते हैं कि दबाव 1100 गुना है?")
    script_gen._enforce_short_hook(s)
    got = s["scenes"][0]["narration"]
    assert "नमस्कार" not in got and "क्या आप जानते" not in got
    assert "1100" in got  # the actual content survives


def test_clean_hook_is_left_alone():
    hook = "ग्यारह किलोमीटर नीचे दबाव 1100 गुना है।"
    s = _script(hook)
    script_gen._enforce_short_hook(s)
    assert s["scenes"][0]["narration"] == hook


def test_long_hook_trims_to_whole_sentences():
    s = _script("दबाव 1100 गुना है। और फिर शरीर का हर हिस्सा एक-एक करके "
                "दबने लगता है जब तक कुछ बचता नहीं।")
    script_gen._enforce_short_hook(s)
    got = s["scenes"][0]["narration"]
    assert got == "दबाव 1100 गुना है।"
    assert len(got.split()) <= script_gen.HOOK_MAX_WORDS


def test_unsplittable_long_hook_ships_with_a_warning(capsys):
    long_hook = " ".join(["शब्द"] * 25)
    s = _script(long_hook)
    script_gen._enforce_short_hook(s)
    assert s["scenes"][0]["narration"] == long_hook  # fail open, never crash
    assert "WARNING" in capsys.readouterr().out


def test_empty_and_missing_scenes_are_safe():
    script_gen._enforce_short_hook({})
    script_gen._enforce_short_hook({"scenes": []})
    s = _script("")
    script_gen._enforce_short_hook(s)  # must not raise


# ── title scope ──────────────────────────────────────────────────────────

def test_overreaching_title_swaps_to_a_fitting_alternate():
    s = _script("दबाव 1100 गुना है।",
                title="11,034 मीटर पर 1 घंटा: हर मिनट शरीर का क्या होगा?",
                title_options=["समुद्र की सबसे गहरी जगह का असली दबाव",
                               "हर 10 मीटर पर क्या बदलता है"])
    script_gen._enforce_title_scope(s, 90)
    assert s["title"] == "समुद्र की सबसे गहरी जगह का असली दबाव"
    assert ts.fits_in(s["title"], 90)


def test_fitting_title_is_untouched():
    title = "समुद्र की सबसे गहरी जगह का असली दबाव"
    s = _script("हुक", title=title, title_options=["कुछ और"])
    script_gen._enforce_title_scope(s, 90)
    assert s["title"] == title


def test_no_fitting_alternate_warns_but_ships(capsys):
    """Every alternate is also checkpoint-shaped, so none may be swapped in."""
    title = "1 सेकंड से 1 घंटे तक: हर 5 मिनट क्या होगा?"
    s = _script("हुक", title=title,
                title_options=["हर 100 मीटर पर दबाव कैसे बदलता है",
                               "मिनट दर मिनट: शरीर का क्या होता है"])
    script_gen._enforce_title_scope(s, 90)
    assert s["title"] == title
    assert "WARNING" in capsys.readouterr().out


def test_checkpoint_alternate_is_never_swapped_in():
    """A shorter checkpoint title is still the wrong shape for a Short."""
    s = _script("हुक", title="1 सेकंड से 1 घंटे तक: हर 5 मिनट क्या होगा?",
                title_options=["हर 10 मीटर पर क्या बदलता है",
                               "समुद्र की सबसे गहरी जगह का असली दबाव"])
    script_gen._enforce_title_scope(s, 90)
    assert s["title"] == "समुद्र की सबसे गहरी जगह का असली दबाव"


def test_the_two_worst_real_titles_are_caught():
    """Both of these shipped, and retained 15.0% and 11.3%."""
    for title, runtime in [
        ("11,034 मीटर गहरे समुद्र में 1 घंटा — हर मिनट शरीर का क्या हाल होगा?", 24),
        ("मंगल ग्रह की सतह पर 1 सेकंड से 1 घंटे तक: हर 5 मिनट क्या होगा?", 78),
    ]:
        assert ts.classify(title) == ts.CHECKPOINT_JOURNEY, title
        assert not ts.fits_in(title, runtime), title
        assert not ts.fits_in(title, 90), title  # even the widened band
