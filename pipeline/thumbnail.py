"""Stage 5 — thumbnail: best hook-scene frame + big stroked title text (PIL)."""
import os

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
W, H = 1280, 720


def _font(size: int) -> ImageFont.FreeTypeFont:
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def _base_image(first_scene_assets: list[dict]) -> Image.Image:
    for a in first_scene_assets:
        try:
            if a["kind"] == "image":
                return Image.open(a["path"]).convert("RGB")
            from moviepy import VideoFileClip
            with VideoFileClip(a["path"], audio=False) as v:
                frame = v.get_frame(min(1.0, v.duration / 2))
            return Image.fromarray(frame)
        except Exception:
            continue
    return Image.new("RGB", (W, H), (18, 26, 44))


def make_thumbnail(first_scene_assets: list[dict], thumb_text: str, out_path: str) -> str:
    img = _base_image(first_scene_assets)
    scale = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
    left, top = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((left, top, left + W, top + H))
    img = ImageEnhance.Contrast(ImageEnhance.Brightness(img).enhance(0.75)).enhance(1.15)

    d = ImageDraw.Draw(img)
    words = thumb_text.upper().split()
    lines, cur = [], ""
    for w_ in words:
        trial = f"{cur} {w_}".strip()
        if len(trial) > 12 and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = trial
    if cur:
        lines.append(cur)
    lines = lines[:3]

    size = 150 if len(lines) <= 2 else 118
    font = _font(size)
    line_h = size + 14
    y = H - 60 - line_h * len(lines)
    for line in lines:
        tw = d.textlength(line, font=font)
        x = (W - tw) // 2
        d.text((x, y), line, font=font, fill=(255, 224, 60),
               stroke_width=max(6, size // 16), stroke_fill=(0, 0, 0))
        y += line_h

    img.save(out_path, quality=90)
    return out_path
