"""The rename must survive every renderer and every future asset rebuild."""
from pathlib import Path

import yaml
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_brand_config_is_complete_and_consistent():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    brand = cfg["brand"]
    assert brand["name"] == "SURAAGNAMA"
    assert brand["hindi_name"] == "सुरागनामा"
    assert brand["handle"] == "@suraagnama"
    assert brand["closing_line"] == "फ़ाइल अभी बंद नहीं हुई।"


def test_every_renderer_has_an_end_name_contract():
    main = (ROOT / "remotion/src/Main.tsx").read_text(encoding="utf-8")
    short = (ROOT / "remotion/src/ShortMain.tsx").read_text(encoding="utf-8")
    fallback = (ROOT / "pipeline/render.py").read_text(encoding="utf-8")
    assert "brandName={m.brandName || 'SURAAGNAMA'}" in main
    assert "<ShortEndBrand" in short
    assert "brandName={m.brandName || 'SURAAGNAMA'}" in short
    assert "_brand_outro(cfg, w, h)" in fallback
    assert 'brand.get("name") or "SURAAGNAMA"' in fallback


def test_approved_assets_have_youtube_dimensions_and_alpha():
    banner = Image.open(ROOT / "brand/banner.png")
    avatar = Image.open(ROOT / "brand/avatar.png")
    watermark = Image.open(ROOT / "brand/yt_watermark.png")
    assert banner.size == (2560, 1440)
    assert avatar.size == (800, 800)
    assert watermark.size == (150, 150)
    assert watermark.mode == "RGBA"
    assert watermark.getpixel((0, 0))[3] == 0


def test_generator_cannot_restore_the_old_ti_identity():
    generator = (ROOT / "brand/generate_brand.py").read_text(encoding="utf-8")
    assert "source-avatar.png" in generator
    assert '"T · I"' not in generator
    assert "compass" not in generator.lower()
