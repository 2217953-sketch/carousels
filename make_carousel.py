#!/usr/bin/env python3
"""
Генератор Instagram-каруселей у стилі @larisa_rybyk.

    python3 make_carousel.py posts/<slug>.json  ->  out/<slug>/01.jpg … (1080x1350) + caption.txt + meta.json

Типи слайдів (поле "type"):
  cover    – фото Лариси, заголовок великими літерами, підзаголовок в овалі, кнопка «ЧИТАТИ»
             {"photo": "photos/x.jpg", "title": "...", "subtitle": "...", "side": "right"|"left", "focus": 0.5}
  hook     – 2-й слайд: другий заголовок-гачок по центру на приглушеному фото
             {"text": "...", "photo": "photos/bg.jpg" (необов'язково)}
  content  – пункт: жирний заголовок + курсивна мітка + текст
             {"heading": "...", "label": "Навіщо питати:", "body": "..."}
  text     – абзац по центру {"text": "..."}
  list     – {"heading": "...", "items": ["...", "..."]}
  quote    – {"text": "...", "author": "..."}
  final    – стікер «Зберігайте…», висновок в овалі, кодове слово, джерело
             {"sticker": "...", "text": "...", "keyword": "ПРИВ'ЯЗАНІСТЬ", "cta": "...", "source": "..."}
Шляхи до фото — від кореня репозиторію (CAROUSEL_BASE).
"""
import json, math, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

FONTS = os.environ.get("CAROUSEL_FONTS", "fonts")


def _pick(*names):
    for n in names:
        p = os.path.join(FONTS, n)
        if os.path.exists(p):
            return p
    return os.path.join(FONTS, names[-1])


# ─────────── БРЕНД ───────────
BRAND = {
    "handle": "@larisa_rybyk",
    "bg": (246, 240, 232),          # кремовий
    "ink": (110, 42, 22),           # коричнево-теракотовий текст
    "title": (181, 73, 31),         # заголовок на обкладинці
    "orange": (240, 138, 92),       # овали, хвилі, стрілки
    "sticker": (255, 222, 77),      # жовтий стікер
    "head": _pick("Lora.ttf"),
    "body": _pick("EBGaramond.ttf", "Lora.ttf"),
    "italic": _pick("EBGaramond-Italic.ttf", "Lora-Italic.ttf"),
}
W, H = 1080, 1350
M = 130


def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def wrap(d, text, f, max_w, tracking=0):
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        if not words:
            lines.append("")
            continue
        for w in words:
            t = (cur + " " + w).strip()
            if tw(d, t, f, tracking) <= max_w:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def tw(d, t, f, tracking=0):
    return d.textlength(t, font=f) + tracking * max(len(t) - 1, 0)


def clean(t):
    return "".join(ch for ch in t if ord(ch) < 0x2190 or 0x2190 <= ord(ch) <= 0x2BFF and False or ord(ch) in (0x2014, 0x2013, 0x2026, 0x00AB, 0x00BB, 0x2019, 0x02BC)).strip() if any(ord(c) > 0x2BFF for c in t) else t


def put(d, xy, t, f, fill, tracking=0, anchor="l"):
    t = clean(t)
    x, y = xy
    width = tw(d, t, f, tracking)
    if anchor == "c":
        x -= width / 2
    elif anchor == "r":
        x -= width
    if not tracking:
        d.text((x, y), t, font=f, fill=fill)
        return
    for ch in t:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tracking


def fit(d, text, path, max_w, max_h, start, minimum, weight=None, lh=1.3, tracking=0):
    size = start
    while size >= minimum:
        f = font(path, size, weight)
        lines = wrap(d, text, f, max_w, tracking * size / 40)
        if len(lines) * size * lh <= max_h:
            return f, lines, size
        size -= 2
    f = font(path, minimum, weight)
    return f, wrap(d, text, f, max_w, tracking * minimum / 40), minimum


def block(d, x, y, lines, f, size, fill, lh=1.3, anchor="l", tracking=0):
    for ln in lines:
        put(d, (x, y), ln, f, fill, tracking * size / 40, anchor)
        y += size * lh
    return y


def waves(d, x, y, w=110, n=3, gap=22, col=None):
    col = col or BRAND["orange"]
    for k in range(n):
        pts = [(x + i, y + k * gap + 7 * math.sin(i / w * 4 * math.pi)) for i in range(0, w + 1, 2)]
        d.line(pts, fill=col, width=3, joint="curve")


def decor(d):
    waves(d, W - 190, 75)
    waves(d, 0, H - 230)


def arrow_button(d, cx, cy, label="ДАЛІ", col=None, text_col=None):
    col = col or BRAND["orange"]
    d.ellipse([cx - 62, cy - 42, cx + 62, cy + 42], outline=(246, 196, 170), width=3)
    d.line([(cx - 32, cy), (cx + 32, cy)], fill=col, width=3)
    d.line([(cx + 18, cy - 9), (cx + 32, cy), (cx + 18, cy + 9)], fill=col, width=3)
    f = font(BRAND["body"], 26, 500)
    put(d, (cx, cy + 62), label, f, text_col or col, tracking=7, anchor="c")


def oval(d, box, width=10):
    d.ellipse(box, outline=BRAND["orange"], width=width)


def cover_crop(path, w, h, focus=0.5):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return ImageOps.fit(img, (w, h), Image.LANCZOS, centering=(focus, 0.35))


BASE = Path(".")


def canvas():
    bgp = BASE / "assets" / "bg.jpg"
    if bgp.exists():
        tex = cover_crop(bgp, W, H)
        return Image.blend(tex, Image.new("RGB", (W, H), BRAND["bg"]), 0.45)
    img = Image.new("RGB", (W, H), BRAND["bg"])
    # м'яке світло, як на прикладі
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([-300, -200, W * 0.9, H * 0.7], fill=60)
    glow = glow.filter(ImageFilter.GaussianBlur(200))
    img = Image.composite(Image.new("RGB", (W, H), (252, 249, 244)), img, glow)
    return img


# ─────────── СЛАЙДИ ───────────
def s_cover(s, base, i, n):
    img = cover_crop(base / s["photo"], W, H, s.get("focus", 0.5)).convert("RGBA")
    side = s.get("side", "top")
    if side == "top":
        x0, col_w, ty0, ty1 = M - 40, W - 2 * M + 80, 170, 560
    else:
        col_w = 470
        x0 = W - col_w - 50 if side == "right" else 50
        ty0, ty1 = 200, 720
    # світла підкладка під заголовком для читабельності
    wash = Image.new("L", (W, H), 0)
    ImageDraw.Draw(wash).rounded_rectangle([x0 - 30, ty0 - 60, x0 + col_w + 30, ty1], 60, fill=s.get("wash", 150))
    wash = wash.filter(ImageFilter.GaussianBlur(70))
    img = Image.composite(Image.new("RGBA", (W, H), BRAND["bg"] + (255,)), img, wash)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    put(d, (70, 70), BRAND["handle"], font(BRAND["body"], 28, 500), BRAND["ink"], tracking=2)
    waves(d, W - 190, 75)
    waves(d, 0, H - 230)
    title = s["title"].upper()
    f, lines, sz = fit(d, title, BRAND["head"], col_w, ty1 - ty0 - 40, 72 if side == "top" else 64, 38, 700, 1.22, tracking=1)
    cx = x0 + col_w / 2
    block(d, cx, ty0, lines, f, sz, BRAND["title"], 1.22, "c", tracking=1)
    if s.get("subtitle"):
        fs, sl, ss = fit(d, s["subtitle"], BRAND["italic"], 470, 170, 44, 30, 500, 1.3)
        if side == "top":
            ex, ey = W / 2, s.get("subtitle_y", 1010)
        else:
            ex, ey = (W / 2 if side == "right" else W - 330), 930
        h = len(sl) * ss * 1.3
        d.ellipse([ex - 340, ey - h / 2 - 70, ex + 340, ey + h / 2 + 70], fill=(70, 35, 20, 110))
        oval(d, [ex - 340, ey - h / 2 - 70, ex + 340, ey + h / 2 + 70], 11)
        block(d, ex, ey - h / 2, sl, fs, ss, (255, 255, 255), 1.3, "c")
        arrow_button(d, ex, min(ey + h / 2 + 150, H - 120), "ЧИТАТИ", text_col=(255, 255, 255))
    return Image.alpha_composite(img, ov).convert("RGB")


def s_hook(s, base, i, n):
    img = canvas()
    photo = s.get("photo") or ("assets/hook.jpg" if (base / "assets/hook.jpg").exists() else None)
    if photo:
        ph = cover_crop(base / photo, W, H).filter(ImageFilter.GaussianBlur(2))
        img = Image.blend(ph, Image.new("RGB", (W, H), BRAND["bg"]), 0.78)
    d = ImageDraw.Draw(img)
    decor(d)
    f, lines, sz = fit(d, s["text"], BRAND["head"], W - 2 * M, 760, 66, 40, 650, 1.32, tracking=1)
    h = len(lines) * sz * 1.32
    block(d, W / 2, (H - h) / 2 - 60, lines, f, sz, BRAND["ink"], 1.32, "c", tracking=1)
    arrow_button(d, W / 2, H - 230)
    return img


def s_content(s, base, i, n):
    img = canvas()
    d = ImageDraw.Draw(img)
    decor(d)
    max_w = W - 2 * M - 30
    fh, hl, hs = fit(d, s["heading"], BRAND["head"], max_w, 360, 54, 38, 700, 1.22)
    parts = [(hl, fh, hs, 1.22, BRAND["ink"])]
    rest = 950 - len(hl) * hs * 1.22
    if s.get("label"):
        fl = font(BRAND["italic"], hs, 400)
        parts.append(([s["label"]], fl, hs, 1.3, BRAND["ink"]))
        rest -= hs * 1.3 + 60
    if s.get("body"):
        fb, bl, bs = fit(d, s["body"], BRAND["body"], max_w, rest, 50, 32, 400, 1.32)
        parts.append((bl, fb, bs, 1.32, BRAND["ink"]))
    total = sum(len(p[0]) * p[2] * p[3] for p in parts) + 55 * (len(parts) - 1)
    y = max(260, (H - total) / 2 - 40)
    for k, (ls, f, sz, lh, col) in enumerate(parts):
        y = block(d, M, y, ls, f, sz, col, lh) + 55
    arrow_button(d, W / 2, H - 230)
    return img


def s_text(s, base, i, n):
    img = canvas()
    d = ImageDraw.Draw(img)
    decor(d)
    f, lines, sz = fit(d, s["text"], BRAND["body"], W - 2 * M, 850, 54, 34, 500, 1.4)
    h = len(lines) * sz * 1.4
    block(d, W / 2, (H - h) / 2 - 60, lines, f, sz, BRAND["ink"], 1.4, "c")
    if i < n:
        arrow_button(d, W / 2, H - 230)
    return img


def s_list(s, base, i, n):
    img = canvas()
    d = ImageDraw.Draw(img)
    decor(d)
    max_w = W - 2 * M
    fh, hl, hs = fit(d, s["heading"], BRAND["head"], max_w, 300, 54, 38, 700, 1.22)
    y = block(d, M, 260, hl, fh, hs, BRAND["ink"], 1.22) + 50
    avail = H - y - 330
    size = 46
    while size > 30:
        fb = font(BRAND["body"], size, 400)
        blocks = [wrap(d, it, fb, max_w - 70) for it in s["items"]]
        if sum(len(b) * size * 1.3 + 28 for b in blocks) <= avail:
            break
        size -= 2
    for b in blocks:
        d.ellipse([M + 4, y + size * 0.42, M + 20, y + size * 0.42 + 16], fill=BRAND["orange"])
        y = block(d, M + 60, y, b, fb, size, BRAND["ink"], 1.3) + 28
    arrow_button(d, W / 2, H - 230)
    return img


def s_quote(s, base, i, n):
    img = canvas()
    d = ImageDraw.Draw(img)
    decor(d)
    f, lines, sz = fit(d, s["text"], BRAND["italic"], W - 2 * M - 80, 640, 60, 36, 500, 1.35)
    h = len(lines) * sz * 1.35
    y0 = (H - h) / 2 - 80
    oval(d, [M - 70, y0 - 110, W - M + 70, y0 + h + 110])
    block(d, W / 2, y0, lines, f, sz, BRAND["ink"], 1.35, "c")
    if s.get("author"):
        put(d, (W / 2, y0 + h + 150), "— " + s["author"], font(BRAND["body"], 34, 500), BRAND["ink"], 3, "c")
    arrow_button(d, W / 2, H - 230)
    return img


def s_final(s, base, i, n):
    img = canvas()
    d = ImageDraw.Draw(img)
    decor(d)
    y = 120
    # жовтий стікер
    st_text = s.get("sticker", "Зберігайте в закладки, щоб мати під рукою").upper()
    st = Image.new("RGBA", (660, 300), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.rectangle([0, 0, 659, 299], fill=BRAND["sticker"])
    fs, sl, ss = fit(sd, st_text, BRAND["head"], 560, 230, 46, 30, 700, 1.3, tracking=2)
    sh = len(sl) * ss * 1.3
    block(sd, 330, (300 - sh) / 2, sl, fs, ss, BRAND["ink"], 1.3, "c", tracking=2)
    st = st.rotate(4, expand=True, resample=Image.BICUBIC)
    shadow = Image.new("RGBA", st.size, (0, 0, 0, 0))
    shadow.paste((90, 60, 40, 50), mask=st.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    base_rgba = img.convert("RGBA")
    sx = (W - st.size[0]) // 2 + 40
    base_rgba.alpha_composite(shadow, (sx + 8, y + 12))
    base_rgba.alpha_composite(st, (sx, y))
    img = base_rgba.convert("RGB")
    d = ImageDraw.Draw(img)
    y += st.size[1] + 40
    # висновок в овалі
    if s.get("text"):
        f, lines, sz = fit(d, s["text"], BRAND["italic"], 640, 280, 44, 30, 500, 1.3)
        h = len(lines) * sz * 1.3
        oval(d, [W / 2 - 420, y, W / 2 + 420, y + h + 130], 11)
        block(d, W / 2, y + 65, lines, f, sz, BRAND["ink"], 1.3, "c")
        y += h + 130 + 50
    # кодове слово для чат-бота
    if s.get("keyword"):
        cta = s.get("cta", "Напишіть у коментарях слово")
        fc, cl, cs = fit(d, cta, BRAND["body"], W - 2 * M, 130, 40, 30, 500, 1.3)
        y = block(d, W / 2, y, cl, fc, cs, BRAND["ink"], 1.3, "c") + 15
        fk = font(BRAND["head"], 64, 700)
        kw = s["keyword"].upper()
        kwid = tw(d, kw, fk, 4)
        d.rounded_rectangle([W / 2 - kwid / 2 - 45, y - 10, W / 2 + kwid / 2 + 45, y + 95], 50, fill=BRAND["orange"])
        put(d, (W / 2, y + 2), kw, fk, (255, 255, 255), 4, "c")
        y += 130
        if s.get("cta_after"):
            fa, al, as_ = fit(d, s["cta_after"], BRAND["body"], W - 2 * M, 140, 38, 28, 500, 1.3)
            y = block(d, W / 2, y, al, fa, as_, BRAND["ink"], 1.3, "c") + 10
    if s.get("source"):
        room = max(60, H - 135 - (y + 15))
        fsrc, srl, srs = fit(d, s["source"], BRAND["body"], W - 2 * M + 40, min(room, 150), 24, 16, 500, 1.3)
        src_h = len(srl) * srs * 1.3
        block(d, W / 2, H - 135 - src_h, srl, fsrc, srs, BRAND["ink"], 1.3, "c")
    put(d, (W / 2, H - 80), BRAND["handle"], font(BRAND["body"], 28, 500), BRAND["ink"], 3, "c")
    return img


RENDER = {"cover": s_cover, "hook": s_hook, "content": s_content, "text": s_text,
          "list": s_list, "quote": s_quote, "final": s_final}


def build(post_path):
    post_path = Path(post_path)
    global BASE
    base = BASE = Path(os.environ.get("CAROUSEL_BASE", post_path.parent))
    post = json.loads(post_path.read_text(encoding="utf-8"))
    slides = post["slides"]
    if not 2 <= len(slides) <= 20:
        sys.exit("Instagram дозволяє від 2 до 20 слайдів у каруселі.")
    out = base / "out" / post.get("slug", post_path.stem)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    files = []
    for i, s in enumerate(slides, 1):
        img = RENDER[s["type"]](s, base, i, len(slides))
        p = out / f"{i:02d}.jpg"
        img.save(p, "JPEG", quality=92)
        files.append(p)
    (out / "caption.txt").write_text(post.get("caption", ""), encoding="utf-8")
    meta = {"publish_at": post.get("publish_at"), "slides": [f.name for f in files]}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Готово: {out} ({len(files)} слайдів)")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        build(p)
