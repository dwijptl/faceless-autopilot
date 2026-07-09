"""Terra Incognita brand kit generator (deep navy + amber).

Regenerates every static brand asset deterministically with PIL:
  logo.png (2000x500 transparent)  logo_mark.png (1024)  banner.png (2560x1440)
  avatar.png (800x800)             watermark.png (600, white alpha)
  yt_watermark.png (300, YouTube video watermark)

Run: python brand/generate_brand.py   (writes into brand/)
Video-side branding (Inter typography, captions, lower-thirds, outro) lives
in remotion/src/styles.ts — hex palette must match this file.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

NAVY = (10, 20, 40)
PANEL = (19, 36, 65)
AMBER = (255, 176, 32)
AMBER_SOFT = (255, 200, 92)
TEXT = (244, 247, 251)
OUT = os.path.dirname(os.path.abspath(__file__))

FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for f in FONTS:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def draw_mark(size: int, color=AMBER, ring=TEXT, bg=None) -> Image.Image:
    """The mark: a compass ring with an offset 'uncharted' arc + star point."""
    img = Image.new("RGBA", (size, size), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, r = size / 2, size * 0.42
    w = max(int(size * 0.045), 3)
    # outer ring with a deliberate gap (the unknown)
    d.arc([c - r, c - r, c + r, c + r], start=300, end=210, fill=ring, width=w)
    # inner latitude arcs
    r2 = r * 0.62
    d.arc([c - r2, c - r2 * 0.45, c + r2, c + r2 * 0.45], 200, 340, fill=ring,
          width=max(w // 2, 2))
    d.arc([c - r2, c - r2 * 0.45, c + r2, c + r2 * 0.45], 20, 160, fill=ring,
          width=max(w // 2, 2))
    # compass needle / star
    n = r * 0.78
    pts = [(c, c - n), (c + n * 0.18, c - n * 0.18), (c + n, c),
           (c + n * 0.18, c + n * 0.18), (c, c + n), (c - n * 0.18, c + n * 0.18),
           (c - n, c), (c - n * 0.18, c - n * 0.18)]
    d.polygon(pts, fill=color)
    # north tip highlight
    d.polygon([(c, c - n), (c + n * 0.18, c - n * 0.18), (c, c - n * 0.28),
               (c - n * 0.18, c - n * 0.18)], fill=TEXT)
    return img


def vertical_gradient(w: int, h: int, top, bottom) -> Image.Image:
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)],
               fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def add_grid(img: Image.Image, alpha=16, step=90) -> None:
    """Faint map-graticule grid."""
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=(244, 247, 251, alpha))
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=(244, 247, 251, alpha))


def wordmark(d: ImageDraw.ImageDraw, xy, size: int, spacing: int = None):
    x, y = xy
    f1 = font(size)
    spacing = spacing if spacing is not None else int(size * 0.28)
    for ch in "TERRA INCOGNITA":
        d.text((x, y), ch, font=f1, fill=TEXT)
        x += d.textlength(ch, font=f1) + spacing
    return x


def make_logo():
    img = Image.new("RGBA", (2000, 500), (0, 0, 0, 0))
    mark = draw_mark(420)
    img.paste(mark, (30, 40), mark)
    d = ImageDraw.Draw(img)
    end_x = wordmark(d, (520, 150), 130)
    d.rectangle([520, 330, end_x - 36, 342], fill=AMBER)
    f2 = font(44)
    d.text((524, 368), "MAPPING THE WORLD'S HIDDEN PLACES", font=f2,
           fill=AMBER_SOFT)
    img.save(os.path.join(OUT, "logo.png"))


def make_logo_mark():
    img = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    grad = vertical_gradient(1024, 1024, PANEL, NAVY).convert("RGBA")
    m = Image.new("L", (1024, 1024), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, 1024, 1024], radius=180, fill=255)
    img.paste(grad, (0, 0), m)
    add_grid(img, alpha=14, step=128)
    mark = draw_mark(760)
    img.paste(mark, (132, 132), mark)
    img.save(os.path.join(OUT, "logo_mark.png"))


def make_banner():
    W, H = 2560, 1440
    img = vertical_gradient(W, H, (13, 26, 50), NAVY).convert("RGBA")
    add_grid(img, alpha=12, step=120)
    d = ImageDraw.Draw(img, "RGBA")
    # horizon glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W * 0.15, H * 0.52, W * 0.85, H * 1.15],
                                 fill=(255, 176, 32, 46))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(img, "RGBA")
    # safe area (1546x423 centered) content
    cx, cy = W // 2, H // 2
    mark = draw_mark(240)
    img.paste(mark, (cx - 120, cy - 205), mark)
    f1 = font(92)
    text = "TERRA INCOGNITA"
    spacing = 26
    total = sum(d.textlength(ch, font=f1) + spacing for ch in text) - spacing
    x = cx - total / 2
    for ch in text:
        d.text((x, cy + 55), ch, font=f1, fill=TEXT)
        x += d.textlength(ch, font=f1) + spacing
    d.rectangle([cx - 160, cy + 180, cx + 160, cy + 188], fill=AMBER)
    f2 = font(38)
    sub = "THE WORLD'S HIDDEN PLACES · MON | WED | FRI"
    d.text((cx - d.textlength(sub, font=f2) / 2, cy + 210), sub, font=f2,
           fill=(255, 200, 92, 255))
    img.convert("RGB").save(os.path.join(OUT, "banner.png"))


def make_avatar():
    S = 800
    img = vertical_gradient(S, S, PANEL, NAVY).convert("RGBA")
    add_grid(img, alpha=14, step=100)
    d = ImageDraw.Draw(img)
    ring_w = 14
    d.ellipse([ring_w, ring_w, S - ring_w, S - ring_w], outline=AMBER,
              width=ring_w)
    mark = draw_mark(520)
    img.paste(mark, (140, 110), mark)
    f = font(86)
    text = "T · I"
    d.text(((S - d.textlength(text, font=f)) / 2, S - 175), text, font=f,
           fill=TEXT)
    img.convert("RGB").save(os.path.join(OUT, "avatar.png"))


def make_watermarks():
    # in-video corner watermark: white mark, transparent bg
    mark = draw_mark(600, color=(255, 255, 255, 235), ring=(255, 255, 255, 235))
    mark.save(os.path.join(OUT, "watermark.png"))
    # YouTube "video watermark" (branding setting): amber on navy disc
    S = 300
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, S, S], fill=PANEL + (255,))
    d.ellipse([6, 6, S - 6, S - 6], outline=AMBER, width=8)
    m = draw_mark(210)
    img.paste(m, (45, 45), m)
    img.save(os.path.join(OUT, "yt_watermark.png"))


if __name__ == "__main__":
    make_logo()
    make_logo_mark()
    make_banner()
    make_avatar()
    make_watermarks()
    print("brand kit written to", OUT)
