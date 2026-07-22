"""style_packs (python) <-> styles.ts (renderer) stay in sync, and the
topic-driven selector behaves: deterministic, topic-affine, no-repeat."""
import pathlib
import re

import motion
import style_packs


ROOT = pathlib.Path(__file__).resolve().parents[1]
STYLES_TS = (ROOT / "remotion" / "src" / "styles.ts").read_text(encoding="utf-8")
ELEMENTS_TSX = (ROOT / "remotion" / "src" / "elements.tsx").read_text(encoding="utf-8")
FONTS_TS = (ROOT / "remotion" / "src" / "fonts.ts").read_text(encoding="utf-8")
MAIN_TSX = (ROOT / "remotion" / "src" / "Main.tsx").read_text(encoding="utf-8")


def _ts_union(type_name: str) -> set[str]:
    match = re.search(rf"export type {type_name} =(.*?);", STYLES_TS, re.S)
    assert match, f"missing TS union {type_name}"
    return set(re.findall(r"'([\w-]+)'", match.group(1)))


def _pack_field(field: str) -> dict[str, str]:
    """Map pack name -> field value by walking the STYLE_PACKS literal."""
    result = {}
    blocks = re.split(r"\n\s+name: '([\w-]+)',", STYLES_TS)
    # blocks: [prefix, name1, body1, name2, body2, ...]
    for i in range(1, len(blocks) - 1, 2):
        name, body = blocks[i], blocks[i + 1]
        m = re.search(rf"{field}: '([\w-]+)'", body)
        if m:
            result[name] = m.group(1)
    return result


TS_PACK_NAMES = set(re.findall(r"\n\s+name: '([\w-]+)',", STYLES_TS))


def test_registries_stay_in_sync():
    assert TS_PACK_NAMES == set(style_packs.PACKS)


def test_enough_distinct_looks():
    assert len(style_packs.PACKS) >= 25


def test_pack_metadata_is_complete_and_valid():
    wrappers, cameras = set(), set()
    for name, pack in style_packs.PACKS.items():
        assert pack["base"] in ("documentary", "kinetic", "editorial", "noir")
        assert len(pack["wrapper"]) > 40, name
        assert len(pack["camera"]) > 10, name
        wrappers.add(pack["wrapper"])
        cameras.add(pack["camera"])
        assert pack["frames"], name
        assert set(pack["frames"]) <= set(motion.FRAME_VARIANTS), name
        assert pack["lower_thirds"], name
        assert set(pack["lower_thirds"]) <= set(motion.LOWER_THIRD_VARIANTS), name
    # every pack photographs and moves differently
    assert len(wrappers) == len(style_packs.PACKS)
    assert len(cameras) == len(style_packs.PACKS)


def test_ts_caption_variants_are_all_implemented():
    union = _ts_union("CaptionVariant")
    used = set(_pack_field("captionVariant").values())
    assert used <= union
    for variant in union - {"pop"}:  # 'pop' is the default branch
        assert f"v === '{variant}'" in ELEMENTS_TSX, variant
    # the system actually uses a wide spread of caption treatments
    assert len(used) >= 10


def test_ts_textures_and_transitions_are_valid():
    tex_union = _ts_union("TextureKind")
    tr_union = _ts_union("TransitionBias")
    assert set(_pack_field("texture").values()) <= tex_union
    biases = set(_pack_field("transitionBias").values())
    assert biases <= tr_union
    for bias in tr_union - {"mixed"}:  # 'mixed' is the default branch
        assert f"case '{bias}':" in MAIN_TSX, bias


def test_pack_fonts_are_registered_and_varied():
    loaders = set(re.findall(r"(\w+): \(\) => require\('@remotion/google-fonts/(\w+)'\)",
                             FONTS_TS))
    assert all(key == module for key, module in loaders)
    registered = {key for key, _ in loaders}
    headings = _pack_field("fontHeading")
    bodies = _pack_field("fontBody")
    assert set(headings) == TS_PACK_NAMES and set(bodies) == TS_PACK_NAMES
    assert set(headings.values()) <= registered
    assert set(bodies.values()) <= registered
    # meaningful typographic variety across the catalog
    assert len(set(headings.values())) >= 12
    assert len(set(bodies.values())) >= 12


def test_selection_is_topic_driven():
    assert style_packs.select("चांद पर अंतरिक्ष यात्री का रहस्य नहीं, ब्लैक होल") == "cosmos"
    assert style_packs.select("आपके शरीर के अंदर दिमाग और खून का खेल") == "medical"
    assert style_packs.select("समुद्र की गहराई में व्हेल का गाना") == "abyss"
    assert style_packs.select("ज्वालामुखी का लावा और तबाही") == "ember"
    assert style_packs.select("मुग़ल इतिहास का भूला हुआ राजा") == "archive"


def test_selection_is_deterministic_and_respects_history():
    title = "अंतरिक्ष में ब्लैक होल का रहस्य और तारे"
    first = style_packs.select(title)
    assert first == style_packs.select(title)
    # excluded when recently used -> a different pack steps in
    alt = style_packs.select(title, history=[first])
    assert alt != first
    # when EVERY pack is recent, selection still succeeds
    all_used = list(style_packs.PACKS)
    assert style_packs.select(title, history=all_used) in style_packs.PACKS


def test_unmatched_topic_still_spreads_across_catalog():
    picks = {style_packs.select(f"एक अनोखी बात {i}") for i in range(40)}
    assert len(picks) >= 8  # hash tie-break spreads generic topics widely


def test_history_roundtrip(tmp_path):
    path = tmp_path / "styles_used.txt"
    for name in ("cosmos", "noir", "abyss"):
        style_packs.record_style(str(path), name)
    assert style_packs.recent_styles(str(path)) == ["cosmos", "noir", "abyss"]
    assert style_packs.recent_styles(str(path), n=2) == ["noir", "abyss"]
    assert style_packs.recent_styles(str(tmp_path / "missing.txt")) == []


def test_render_jitter_bounds_and_determinism():
    a = style_packs.render_jitter("वही शीर्षक")
    b = style_packs.render_jitter("वही शीर्षक")
    c = style_packs.render_jitter("दूसरा शीर्षक")
    assert a == b and a != c
    assert 0.80 <= a["xfade_mul"] <= 1.25
    assert 0.85 <= a["max_shot_mul"] <= 1.20
    assert 0.88 <= a["overlay_mul"] <= 1.15
    assert abs(a["caption_y_off"]) <= 0.02
    assert abs(a["watermark_off"]) <= 0.02


def test_legacy_base_helpers_fail_open():
    assert style_packs.base_for("no-such-pack") == "documentary"
    assert style_packs.wrapper_for("no-such-pack")
    assert style_packs.camera_for("no-such-pack")
    assert style_packs.frames_for("cosmos") == ("focus", "aperture")
    assert style_packs.lower_thirds_for("bazaar") == ("pill", "rail")


# ── Layout + motion DNA (structural variety, not just palettes) ─────────

def _pack_float(field: str) -> dict[str, float]:
    result = {}
    blocks = re.split(r"\n\s+name: '([\w-]+)',", STYLES_TS)
    for i in range(1, len(blocks) - 1, 2):
        m = re.search(rf"{field}: ([0-9.]+)", blocks[i + 1])
        if m:
            result[blocks[i]] = float(m.group(1))
    return result


def test_every_pack_has_layout_and_motion_dna():
    for field, union_name in (("captionAlign", "CaptionAlign"),
                              ("lowerThird", "LowerThirdPos"),
                              ("overlayAnchor", "OverlayAnchor"),
                              ("watermark", "WatermarkCorner"),
                              ("progress", "ProgressStyle"),
                              ("entry", "CaptionEntry"),
                              ("spring", "Springiness")):
        values = _pack_field(field)
        assert set(values) == TS_PACK_NAMES, field
        assert set(values.values()) <= _ts_union(union_name), field
    cap_y = _pack_float("captionY")
    kb = _pack_float("kenBurns")
    assert set(cap_y) == TS_PACK_NAMES and set(kb) == TS_PACK_NAMES
    assert all(0.65 <= v <= 0.85 for v in cap_y.values())
    assert all(0.5 <= v <= 1.6 for v in kb.values())


def test_layouts_are_structurally_varied():
    aligns = _pack_field("captionAlign")
    lts = _pack_field("lowerThird")
    anchors = _pack_field("overlayAnchor")
    wms = _pack_field("watermark")
    progress = _pack_field("progress")
    entries = _pack_field("entry")
    springs = _pack_field("spring")
    assert len(set(aligns.values())) >= 3
    assert len(set(lts.values())) >= 3
    assert len(set(anchors.values())) >= 3
    assert len(set(wms.values())) >= 4
    assert len(set(progress.values())) >= 4
    assert len(set(entries.values())) >= 4
    assert len(set(springs.values())) >= 3
    # the full layout signature rarely repeats across the catalog
    combos = {(aligns[n], lts[n], anchors[n], wms[n], progress[n],
               entries[n], springs[n]) for n in TS_PACK_NAMES}
    assert len(combos) >= 20


def test_pacing_dna_bounds_and_coverage():
    assert set(style_packs.PACING) == set(style_packs.PACKS)
    for name, p in style_packs.PACING.items():
        assert 0.6 <= p["pace"] <= 1.4, name
        assert 0.7 <= p["chunk"] <= 1.3, name
    paces = {p["pace"] for p in style_packs.PACING.values()}
    assert len(paces) >= 6  # real rhythm spread, not one tempo


def test_apply_pacing_bends_config_within_bounds():
    cfg = {"video": {"max_shot_seconds": 5, "crossfade": 0.4},
           "captions": {"max_chars": 30}}
    style_packs.apply_pacing(cfg, "ember")           # fastest pack
    assert cfg["video"]["max_shot_seconds"] == 3.5   # 5 * 0.7
    assert cfg["video"]["crossfade"] == 0.32         # 0.4 * 0.8 floor
    assert cfg["captions"]["max_chars"] == 24        # 30 * 0.8

    cfg = {"video": {"max_shot_seconds": 5, "crossfade": 0.4},
           "captions": {"max_chars": 30}}
    style_packs.apply_pacing(cfg, "manuscript")      # slowest pack
    assert cfg["video"]["max_shot_seconds"] == 6.5   # 5 * 1.3
    assert cfg["video"]["crossfade"] == 0.5          # 0.4 * 1.25 cap
    assert cfg["captions"]["max_chars"] == 34        # 30 * 1.15, half-even

    cfg = {"video": {"max_shot_seconds": 2.4, "crossfade": 0.25},
           "captions": {"max_chars": 24}}
    style_packs.apply_pacing(cfg, "glacier", is_short=True)
    assert 1.4 <= cfg["video"]["max_shot_seconds"] <= 3.6
    assert 12 <= cfg["captions"]["max_chars"] <= 30


def test_hinglish_topics_route_by_meaning():
    # Latin-script (Hinglish) topics — how the owner types forced topics
    assert style_packs.select("NASA Ko Earth Ke Andar Se Signal Mila") == "ember"
    assert style_packs.select("sharir ke andar dimag kaise kaam karta hai") == "medical"
    assert style_packs.select("samundar ki gehrai mein titanic ka raaz") == "abyss"
    assert style_packs.select("ISRO ka naya rocket aur black hole") == "cosmos"
    assert style_packs.select("purani sabhyata ki khudai mein mila pyramid") == "relic"
