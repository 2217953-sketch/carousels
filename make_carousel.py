#!/usr/bin/env python3
"""
Генератор Instagram-каруселей для «Освітнього центру Лариси Рибик».

Використання:
    python3 make_carousel.py post.json            -> папка out/<slug>/ з PNG 1080x1350 + caption.txt

post.json (Claude складає його зі статті та фото):
{
  "slug": "ambiguous-loss-1",
  "publish_at": "2026-12-01 10:00",          # необов'язково, для розкладу
  "caption": "Текст під постом + хештеги",
  "slides": [
    {"type": "cover", "photo": "photos/1.jpg", "title": "...", "subtitle": "..."},
    {"type": "text",  "heading": "...", "body": "..."},
    {"type": "photo_text", "photo": "photos/2.jpg", "heading": "...", "body": "..."},
    {"type": "quote", "text": "...", "author": "..."},
    {"type": "list",  "heading": "...", "items": ["...", "..."]},
    {"type": "cta",   "title": "...", "body": "...", "button": "Посилання в шапці профілю"}
  ]
}
Шляхи до фото — відносно post.json.
"""
import json, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

FONTS = os.environ.get("CAROUSEL_FONTS", "fonts")

# ─────────── БРЕНД (змініть під себе) ───────────
BRAND = {
    "handle": "@larisa_rybyk",                   # ваш нік в Instagram
    "name": "Лариса Рибик · психологиня втрати",
    "bg": (246, 241, 234),          # теплий кремовий
    "ink": (43, 38, 35),            # майже чорний, теплий
    "muted": (122, 110, 100),
    "accent": (150, 98, 74),        # теракота
    "accent_soft": (226, 210, 196),
    "font_head": os.path.join(FONTS, "Lora.ttf"),
    "font_head_italic": os.path.join(FONTS, "Lora-Italic.ttf"),
    "font_body": os.path.join(FONTS, "Montserrat.ttf"),
}
W, H = 1080, 1350
M = 96  # поля


def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def wrap(draw, text, fnt, max_w):
    """Перенос по словах із збереженням абзаців."""
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        if not words:
            lines.append("")
            continue
        for w in words:
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=fnt) <= max_w:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def fit(draw, text, path, max_w, max_h, start, minimum, weight=None, lh=1.3):
    """Підбирає найбільший розмір шрифту, щоб текст влізв у блок."""
    size = start
    while size >= minimum:
        f = font(path, size, weight)
        lines = wrap(draw, text, f, max_w)
        h = len(lines) * size * lh
        if h <= max_h:
            return f, lines, size
        size -= 2
    f = font(path, minimum, weight)
    return f, wrap(draw, text, f, max_w), minimum


def draw_lines(draw, xy, lines, f, size, fill, lh=1.3):
    x, y = xy
    for ln in lines:
        draw.text((x, y), ln, font=f, fill=fill)
        y += size * lh
    return y


def cover_crop(path, w, h):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    return ImageOps.fit(img, (w, h), Image.LANCZOS, centering=(0.5, 0.4))


def footer(draw, idx, total, dark=False):
    col = (255, 255, 255) if dark else BRAND["muted"]
    f = font(BRAND["font_body"], 26, 500)
    draw.text((M, H - 80), BRAND["handle"], font=f, fill=col)
    t = f"{idx}/{total}"
    draw.text((W - M - draw.textlength(t, font=f), H - 80), t, font=f, fill=col)
    if idx < total:  # стрілка «гортай»
        ax, ay = W - M - draw.textlength(t, font=f) - 60, H - 66
        draw.line([(ax - 30, ay), (ax, ay)], fill=col, width=3)
        draw.line([(ax - 10, ay - 9), (ax, ay), (ax - 10, ay + 9)], fill=col, width=3)


def gradient(img, start=0.35):
    """Темний градієнт знизу для читабельності тексту на фото."""
    g = Image.new("L", (1, H))
    for y in range(H):
        p = max(0, (y / H - start) / (1 - start))
        g.putpixel((0, y), int(230 * p ** 1.2))
    g = g.resize((W, H))
    black = Image.new("RGB", (W, H), (20, 16, 14))
    return Image.composite(black, img, g)


# ─────────── ТИПИ СЛАЙДІВ ───────────
def s_cover(s, base, i, n):
    img = gradient(cover_crop(base / s["photo"], W, H), 0.3)
    d = ImageDraw.Draw(img)
    f, lines, sz = fit(d, s["title"], BRAND["font_head"], W - 2 * M, 460, 86, 48, 600, 1.15)
    sub = s.get("subtitle", "")
    sub_h = 0
    if sub:
        fs, sl, ss = fit(d, sub, BRAND["font_body"], W - 2 * M, 200, 36, 26, 400, 1.4)
        sub_h = len(sl) * ss * 1.4 + 30
    y = H - 170 - sub_h - len(lines) * sz * 1.15
    d.rectangle([M, y - 40, M + 70, y - 34], fill=BRAND["accent_soft"])
    y = draw_lines(d, (M, y), lines, f, sz, (255, 255, 255), 1.15)
    if sub:
        draw_lines(d, (M, y + 30), sl, fs, ss, (235, 225, 215), 1.4)
    footer(d, i, n, dark=True)
    return img


def s_text(s, base, i, n):
    img = Image.new("RGB", (W, H), BRAND["bg"])
    d = ImageDraw.Draw(img)
    y = 150
    if s.get("heading"):
        fh, hl, hs = fit(d, s["heading"], BRAND["font_head"], W - 2 * M, 330, 64, 40, 600, 1.2)
        y = draw_lines(d, (M, y), hl, fh, hs, BRAND["ink"], 1.2) + 20
        d.rectangle([M, y, M + 70, y + 6], fill=BRAND["accent"])
        y += 60
    fb, bl, bs = fit(d, s["body"], BRAND["font_body"], W - 2 * M, H - y - 180, 40, 26, 400, 1.5)
    draw_lines(d, (M, y), bl, fb, bs, BRAND["ink"], 1.5)
    footer(d, i, n)
    return img


def s_photo_text(s, base, i, n):
    img = Image.new("RGB", (W, H), BRAND["bg"])
    ph = 620
    img.paste(cover_crop(base / s["photo"], W, ph), (0, 0))
    d = ImageDraw.Draw(img)
    y = ph + 70
    if s.get("heading"):
        fh, hl, hs = fit(d, s["heading"], BRAND["font_head"], W - 2 * M, 180, 54, 36, 600, 1.2)
        y = draw_lines(d, (M, y), hl, fh, hs, BRAND["ink"], 1.2) + 30
    if s.get("body"):
        fb, bl, bs = fit(d, s["body"], BRAND["font_body"], W - 2 * M, H - y - 160, 34, 24, 400, 1.5)
        draw_lines(d, (M, y), bl, fb, bs, BRAND["ink"], 1.5)
    footer(d, i, n)
    return img


def s_quote(s, base, i, n):
    img = Image.new("RGB", (W, H), BRAND["accent"])
    d = ImageDraw.Draw(img)
    fq = font(BRAND["font_head"], 260, 600)
    d.text((M - 10, 90), "«", font=fq, fill=BRAND["accent_soft"])
    f, lines, sz = fit(d, s["text"], BRAND["font_head_italic"], W - 2 * M, 650, 64, 36, 500, 1.3)
    total_h = len(lines) * sz * 1.3
    y = (H - total_h) / 2 + 20
    y = draw_lines(d, (M, y), lines, f, sz, (255, 255, 255), 1.3)
    if s.get("author"):
        fa = font(BRAND["font_body"], 30, 500)
        d.text((M, y + 40), "— " + s["author"], font=fa, fill=BRAND["accent_soft"])
    footer(d, i, n, dark=True)
    return img


def s_list(s, base, i, n):
    img = Image.new("RGB", (W, H), BRAND["bg"])
    d = ImageDraw.Draw(img)
    fh, hl, hs = fit(d, s["heading"], BRAND["font_head"], W - 2 * M, 260, 60, 40, 600, 1.2)
    y = draw_lines(d, (M, 150), hl, fh, hs, BRAND["ink"], 1.2) + 60
    items = s["items"]
    avail = H - y - 170
    size = 36
    while size > 24:
        fb = font(BRAND["font_body"], size, 400)
        blocks = [wrap(d, it, fb, W - 2 * M - 90) for it in items]
        need = sum(len(b) * size * 1.45 + 34 for b in blocks)
        if need <= avail:
            break
        size -= 2
    fn = font(BRAND["font_head"], size + 8, 600)
    for k, b in enumerate(blocks, 1):
        d.text((M, y - 4), f"{k:02d}", font=fn, fill=BRAND["accent"])
        y = draw_lines(d, (M + 90, y), b, fb, size, BRAND["ink"], 1.45) + 34
    footer(d, i, n)
    return img


def s_cta(s, base, i, n):
    img = Image.new("RGB", (W, H), BRAND["ink"])
    d = ImageDraw.Draw(img)
    f, lines, sz = fit(d, s.get("title", "Збережіть, щоб повернутися"), BRAND["font_head"],
                       W - 2 * M, 360, 72, 44, 600, 1.2)
    y = 380
    y = draw_lines(d, (M, y), lines, f, sz, (255, 255, 255), 1.2) + 40
    if s.get("body"):
        fb, bl, bs = fit(d, s["body"], BRAND["font_body"], W - 2 * M, 300, 36, 26, 400, 1.5)
        y = draw_lines(d, (M, y), bl, fb, bs, (220, 210, 200), 1.5) + 50
    if s.get("button"):
        fbt = font(BRAND["font_body"], 32, 600)
        tw = d.textlength(s["button"], font=fbt)
        d.rounded_rectangle([M, y, M + tw + 80, y + 84], radius=42, fill=BRAND["accent"])
        d.text((M + 40, y + 22), s["button"], font=fbt, fill=(255, 255, 255))
    fn = font(BRAND["font_body"], 28, 500)
    d.text((M, H - 200), BRAND["name"], font=fn, fill=BRAND["accent_soft"])
    footer(d, i, n, dark=True)
    return img


RENDER = {"cover": s_cover, "text": s_text, "photo_text": s_photo_text,
          "quote": s_quote, "list": s_list, "cta": s_cta}


def build(post_path):
    post_path = Path(post_path)
    # фото й результат — відносно кореня репозиторію (або папки з post.json локально)
    base = Path(os.environ.get("CAROUSEL_BASE", post_path.parent))
    post = json.loads(post_path.read_text(encoding="utf-8"))
    slides = post["slides"]
    if not 2 <= len(slides) <= 20:
        sys.exit("Instagram дозволяє від 2 до 20 слайдів у каруселі.")
    out = base / "out" / post.get("slug", post_path.stem)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for i, s in enumerate(slides, 1):
        img = RENDER[s["type"]](s, base, i, len(slides))
        p = out / f"{i:02d}.jpg"
        img.save(p, "JPEG", quality=93)   # Instagram API приймає лише JPEG
        files.append(p)
    (out / "caption.txt").write_text(post.get("caption", ""), encoding="utf-8")
    meta = {"publish_at": post.get("publish_at"), "slides": [f.name for f in files]}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Готово: {out} ({len(files)} слайдів)")
    return out


if __name__ == "__main__":
    for p in sys.argv[1:] or ["post.json"]:
        build(p)
