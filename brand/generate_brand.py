"""Regenerate the approved Suraagnama brand kit deterministically.

The two source masters are intentionally versioned beside this script:
  source-avatar.png  — folder/S clue mark on the navy archive disc
  source-banner.png  — approved all-device-safe YouTube banner

Run: python brand/generate_brand.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


OUT = Path(__file__).resolve().parent
SOURCE_AVATAR = OUT / "source-avatar.png"
SOURCE_BANNER = OUT / "source-banner.png"

AMBER = (255, 176, 32)
AMBER_SOFT = (255, 200, 92)
TEXT = (244, 247, 251)

FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONTS:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _source(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing approved source master: {path}. Do not substitute an old logo."
        )
    return Image.open(path).convert("RGBA")


def _square(size: int) -> Image.Image:
    return _source(SOURCE_AVATAR).resize((size, size), Image.Resampling.LANCZOS)


def _circular(size: int) -> Image.Image:
    image = _square(size)
    mask = Image.new("L", (size, size), 0)
    inset = max(round(size * 0.012), 1)
    ImageDraw.Draw(mask).ellipse(
        (inset, inset, size - inset - 1, size - inset - 1), fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(max(size / 300, 0.45)))
    image.putalpha(mask)
    return image


def make_banner() -> None:
    banner = _source(SOURCE_BANNER).resize((2560, 1440), Image.Resampling.LANCZOS)
    banner.convert("RGB").save(OUT / "banner.png", optimize=True)


def make_avatar() -> None:
    _square(800).convert("RGB").save(OUT / "avatar.png", optimize=True)


def make_logo_mark() -> None:
    _square(1024).save(OUT / "logo_mark.png", optimize=True)


def make_logo() -> None:
    image = Image.new("RGBA", (2000, 500), (0, 0, 0, 0))
    mark = _circular(420)
    image.alpha_composite(mark, (28, 40))
    draw = ImageDraw.Draw(image)
    title_font = font(128)
    title = "SURAAGNAMA"
    draw.text((505, 105), title, font=title_font, fill=TEXT)
    title_width = draw.textlength(title, font=title_font)
    draw.rounded_rectangle((505, 270, 505 + title_width, 282), radius=6, fill=AMBER)
    sub_font = font(40)
    draw.text((510, 320), "REAL CASES · REAL EVIDENCE · UNSOLVED QUESTIONS",
              font=sub_font, fill=AMBER_SOFT)
    image.save(OUT / "logo.png", optimize=True)


def make_watermarks() -> None:
    # Internal Remotion/MoviePy corner watermark: larger source for clean video edges.
    _circular(600).save(OUT / "watermark.png", optimize=True)
    # YouTube Studio branding watermark: exact small upload asset, transparent corners.
    _circular(150).save(OUT / "yt_watermark.png", optimize=True)


if __name__ == "__main__":
    make_logo()
    make_logo_mark()
    make_banner()
    make_avatar()
    make_watermarks()
    print("Suraagnama brand kit written to", OUT)
