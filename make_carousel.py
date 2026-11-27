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
            axes = f.get_variation_axes()
            vals = []
            for a in axes:
                nm = a.get("name", b"")
                nm = nm.decode() if isinstance(nm, bytes) else str(nm)
                if "eight" in nm or nm.lower().startswith("wght"):
                    vals.append(max(a["minimum"], min(a["maximum"], weight)))
                else:
                    vals.append(a.get("default", a["maximum"]))
            f.set_variation_by_axes(vals)
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


def _arrow_font(f):
    for p in (os.path.join(FONTS, "Montserrat.ttf"), "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return font(p, int(f.size * 1.1), 700)
    return f


def put(d, xy, t, f, fill, tracking=0, anchor="l"):
    t = clean(t)
    x, y = xy
    width = tw(d, t, f, tracking)
    if anchor == "c":
        x -= width / 2
    elif anchor == "r":
        x -= width
    if not tracking and "→" not in t:
        d.text((x, y), t, font=f, fill=fill)
        return
    for ch in t:
        ff = f
        if ch == "→":
            ff = _arrow_font(f)
        d.text((x, y), ch, font=ff, fill=fill)
        x += d.textlength(ch, font=ff) + tracking


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
        kw = s["keyword"] if s.get("keep_case") else s["keyword"].upper()
        kwid = tw(d, kw, fk, 4)
        d.rounded_rectangle([W / 2 - kwid / 2 - 45, y - 10, W / 2 + kwid / 2 + 45, y + 95], 50, fill=BRAND["orange"])
        put(d, (W / 2, y + 2), kw, fk, (255, 255, 255), 4, "c")
        y += 130
        if s.get("cta_after"):
            fa, al, as_ = fit(d, s["cta_after"], BRAND["body"], W - 2 * M, 140, 38, 28, 500, 1.3)
            y = block(d, W / 2, y, al, fa, as_, BRAND["ink"], 1.3, "c") + 10
    if s.get("cta") and not s.get("keyword"):
        fc, cl, cs = fit(d, s["cta"], BRAND["head"], W - 2 * M, 200, 46, 32, 650, 1.3)
        y = block(d, W / 2, y + 10, cl, fc, cs, BRAND["ink"], 1.3, "c") + 20
    if s.get("source"):
        room = max(60, H - 135 - (y + 15))
        fsrc, srl, srs = fit(d, s["source"], BRAND["body"], W - 2 * M + 40, min(room, 150), 24, 16, 500, 1.3)
        src_h = len(srl) * srs * 1.3
        block(d, W / 2, H - 135 - src_h, srl, fsrc, srs, BRAND["ink"], 1.3, "c")
    put(d, (W / 2, H - 80), BRAND["handle"], font(BRAND["body"], 28, 500), BRAND["ink"], 3, "c")
    return img


def s_still(s, base, i, n):
    """Кадр (фото на весь слайд) з підписом унизу."""
    img = cover_crop(base / s["photo"], W, H, s.get("focus", 0.5))
    g = Image.new("L", (1, H))
    for y in range(H):
        p = max(0, (y / H - 0.62) / 0.38)
        g.putpixel((0, y), int(215 * p))
    g = g.resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), (30, 20, 15)), img, g)
    d = ImageDraw.Draw(img)
    y = H - 300
    if s.get("caption"):
        f, lines, sz = fit(d, s["caption"], BRAND["italic"], W - 2 * M, 150, 46, 30, 500, 1.3)
        y = block(d, M, y, lines, f, sz, (255, 255, 255), 1.3)
    if i < n:
        arrow_button(d, W - M - 40, H - 150, col=(255, 255, 255), text_col=(255, 255, 255))
    return img


# ─────────── МІНІМАЛІСТИЧНИЙ СТИЛЬ (шаблон «7 бар'єрів») ───────────
MIN = {
    "cream": (255, 248, 240), "pale": (241, 244, 247), "tan": (196, 148, 116),
    "sans": _pick("OpenSans.ttf", "Montserrat.ttf"),
    "serif": _pick("EBGaramond.ttf", "Lora.ttf"),
    "serif_it": _pick("Lora-Italic.ttf"),
    "site": "https://larysarybyk.com.ua",
    "name": "Лариса Рибик",
    "role": "Голова Міжнародної асоціації психологів по роботі з горем та тяжкою втратою",
}


def m_frame(img, i, n, footer=True, header=True):
    d = ImageDraw.Draw(img)
    fs = font(MIN["sans"], 24, 400)
    if header:
        put(d, (60, 50), BRAND["handle"], fs, MIN["tan"])
        put(d, (W - 60, 50), MIN["site"], fs, MIN["tan"], anchor="r")
        d.line([(W - 60 - tw(d, MIN["site"], fs), 80), (W - 60, 80)], fill=MIN["tan"], width=1)
    if footer:
        ap = BASE / "assets" / "avatar.jpg"
        if ap.exists():
            av = Image.open(ap).convert("RGB").resize((76, 76), Image.LANCZOS)
            mask = Image.new("L", (76, 76), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, 75, 75], fill=255)
            img.paste(av, (50, H - 120), mask)
        put(d, (140, H - 116), MIN["name"], font(MIN["sans"], 26, 500), MIN["tan"])
        fr, rl, rs = fit(d, MIN["role"], MIN["sans"], 420, 50, 15, 13, 400, 1.25)
        block(d, 140, H - 82, rl, fr, rs, MIN["tan"], 1.25)
        if i < n:
            put(d, (W - 60, H - 100), "Swipe →", font(MIN["sans"], 26, 400), MIN["tan"], anchor="r")
    return d


def s_m_cover(s, base, i, n):
    img = Image.new("RGB", (W, H), MIN["cream"])
    d = m_frame(img, i, n)
    f, lines, sz = fit(d, s["title"], MIN["serif_it"], W - 220, 900, 92, 50, 600, 1.32)
    h = len(lines) * sz * 1.32
    block(d, W / 2, (H - h) / 2 - 40, lines, f, sz, MIN["tan"], 1.32, "c")
    return img


def s_m_point(s, base, i, n):
    img = Image.new("RGB", (W, H), MIN["pale"])
    d = m_frame(img, i, n)
    fn = font(MIN["serif"], 92, 500)
    fh, hl, hs = fit(d, s["heading"], MIN["sans"], W - 240, 360, 56, 38, 750, 1.2)
    hb = len(hl) * hs * 1.2
    fb, bl, bs = (None, [], 0)
    if s.get("body"):
        fb, bl, bs = fit(d, s["body"], MIN["sans"], W - 280, 520, 48, 32, 400, 1.38)
    bb = len(bl) * bs * 1.38
    total = 110 + 50 + hb + (60 + bb if bl else 0)
    y = max(170, (H - total) / 2 - 30)
    put(d, (W / 2, y), s.get("num", f"#{i - 1}"), fn, MIN["tan"], anchor="c")
    y += 160
    y = block(d, W / 2, y, hl, fh, hs, MIN["tan"], 1.2, "c") + 60
    if bl:
        block(d, W / 2, y, bl, fb, bs, MIN["tan"], 1.38, "c")
    return img


def s_m_final(s, base, i, n):
    img = Image.new("RGB", (W, H), MIN["cream"])
    d = m_frame(img, i, n, footer=False, header=False)
    f, lines, sz = fit(d, s["text"], MIN["serif"], W - 260, 650, 50, 34, 450, 1.32)
    y = block(d, W / 2, 230, lines, f, sz, MIN["tan"], 1.32, "c") + 140
    if s.get("question"):
        fq, ql, qs = fit(d, s["question"], MIN["sans"], W - 300, 220, 40, 28, 500, 1.35)
        y = block(d, W / 2, y, ql, fq, qs, MIN["tan"], 1.35, "c") + 70
    if s.get("keyword"):
        cta = s.get("cta", "Напишіть у коментарях слово")
        y = block(d, W / 2, y, [cta], font(MIN["sans"], 32, 500), 32, MIN["tan"], 1.3, "c") + 10
        fk = font(MIN["sans"], 54, 750)
        kw = s["keyword"] if s.get("keep_case") else s["keyword"].upper()
        kwid = tw(d, kw, fk, 3)
        d.rounded_rectangle([W / 2 - kwid / 2 - 40, y - 8, W / 2 + kwid / 2 + 40, y + 82], 45, fill=MIN["tan"])
        put(d, (W / 2, y + 2), kw, fk, (255, 255, 255), 3, "c")
        y += 115
        if s.get("cta_after"):
            fa, al, as_ = fit(d, s["cta_after"], MIN["sans"], W - 260, 130, 30, 24, 400, 1.3)
            block(d, W / 2, y, al, fa, as_, MIN["tan"], 1.3, "c")
    put(d, (W / 2, H - 80), BRAND["handle"], font(MIN["sans"], 26, 400), MIN["tan"], anchor="c")
    return img


# ─────────── КІНО-СТИЛЬ (субота, шаблон Лариси) ───────────
FILM = {
    "bg": (243, 241, 239), "ink": (55, 50, 48), "orange": (242, 152, 72),
    "sans": _pick("Montserrat.ttf"), "sans_bi": _pick("Montserrat-Italic.ttf", "Montserrat.ttf"),
}


def rich_layout(d, text, size, max_w):
    """Текст з **жирним курсивом**. Повертає рядки: [(слово, bold), ...]."""
    fr = font(FILM["sans"], size, 400)
    fb = font(FILM["sans_bi"], size, 700)
    lines = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append([])
            continue
        words, bold = [], False
        for k, part in enumerate(para.split("**")):
            bold = k % 2 == 1
            for w in part.split():
                if words and w[0] in ".,;:!?…»)" and part.startswith(w):
                    pw, pb = words.pop()
                    words.append((pw, pb, w, bold))
                else:
                    words.append((w, bold))
        cur, cur_w = [], 0
        for item in words:
            w, b = item[0], item[1]
            ww = d.textlength(w, font=fb if b else fr)
            if len(item) == 4:
                ww += d.textlength(item[2], font=fb if item[3] else fr)
            sp = d.textlength(" ", font=fr) if cur else 0
            if cur and cur_w + sp + ww > max_w:
                lines.append(cur)
                cur, cur_w = [], 0
                sp = 0
            cur.append(item)
            cur_w += sp + ww
        lines.append(cur)
    return lines, fr, fb


def rich_draw(d, text, cx, cy, max_w, max_h, start=44, minimum=28, lh=1.42, fill=None):
    fill = fill or FILM["ink"]
    size = start
    while True:
        lines, fr, fb = rich_layout(d, text, size, max_w)
        h = len(lines) * size * lh
        if h <= max_h or size <= minimum:
            break
        size -= 2
    y = cy - h / 2
    for ln in lines:
        def wid(it):
            v = d.textlength(it[0], font=fb if it[1] else fr)
            if len(it) == 4:
                v += d.textlength(it[2], font=fb if it[3] else fr)
            return v
        widths = [wid(it) for it in ln]
        sp = d.textlength(" ", font=fr)
        total = sum(widths) + sp * max(len(ln) - 1, 0)
        x = cx - total / 2
        for it, ww in zip(ln, widths):
            f1 = fb if it[1] else fr
            d.text((x, y), it[0], font=f1, fill=fill)
            if len(it) == 4:
                d.text((x + d.textlength(it[0], font=f1), y), it[2], font=fb if it[3] else fr, fill=fill)
            x += ww + sp
        y += size * lh
    return y


def film_strip(size=170, angle=28):
    im = Image.new("RGBA", (size * 2, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col, fill = (110, 85, 70, 255), (236, 225, 212, 255)
    w, h = size * 2 - 20, int(size * 0.55)
    y0 = (size - h) // 2
    d.rounded_rectangle([10, y0, 10 + w, y0 + h], 10, fill=fill, outline=col, width=4)
    for x in range(22, w, 26):
        d.rectangle([x, y0 + 8, x + 12, y0 + 18], fill=col)
        d.rectangle([x, y0 + h - 18, x + 12, y0 + h - 8], fill=col)
    for x in range(10 + 18, w, 78):
        d.rectangle([x, y0 + 26, x + 60, y0 + h - 26], outline=col, width=3)
    return im.rotate(angle, expand=True, resample=Image.BICUBIC)


def ticket(text_big, text_small, color, w=380, h=170, angle=-8):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark = tuple(max(0, c - 60) for c in color) + (255,)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 18, fill=color + (255,))
    r = 24
    d.ellipse([-r, h / 2 - r, r, h / 2 + r], fill=(0, 0, 0, 0))
    d.ellipse([w - r, h / 2 - r, w + r, h / 2 + r], fill=(0, 0, 0, 0))
    d.rounded_rectangle([12, 12, w - 13, h - 13], 12, outline=dark, width=4)
    for y in range(22, h - 22, 16):
        d.line([(w - 90, y), (w - 90, y + 8)], fill=dark, width=4)
    put(d, ((w - 90) / 2 + 6, h * 0.16), text_small, font(FILM["sans"], int(h * 0.15), 800), dark, 3, "c")
    put(d, ((w - 90) / 2 + 6, h * 0.34), text_big, font(FILM["sans"], int(h * 0.42), 900), dark, 2, "c")
    d.ellipse([w - 68, h / 2 - 22, w - 24, h / 2 + 22], outline=dark, width=4)
    return im.rotate(angle, expand=True, resample=Image.BICUBIC)


def clapper(size=56):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([2, size * 0.38, size - 3, size - 3], fill=(40, 40, 40, 255))
    d.polygon([(2, size * 0.32), (size - 6, size * 0.08), (size - 3, size * 0.26), (5, size * 0.48)], fill=(40, 40, 40, 255))
    for k in range(4):
        x = 10 + k * size * 0.22
        d.line([(x, size * 0.29 - k * 3), (x + 8, size * 0.42 - k * 3)], fill=(240, 240, 240, 255), width=4)
    for k in range(4):
        x = 6 + k * size * 0.24
        d.line([(x, size * 0.62), (x + 9, size * 0.48)], fill=(240, 240, 240, 255), width=4)
    return im


def film_frame(img, i, n):
    d = ImageDraw.Draw(img)
    fs = font(FILM["sans"], 26, 500)
    put(d, (W / 2, H - 92), BRAND["handle"], fs, (140, 130, 125), anchor="c")
    if i < n:
        put(d, (W - 80, H - 92), "далі →", fs, (140, 130, 125), anchor="r")
    return d


def s_f_cover(s, base, i, n):
    img = cover_crop(base / s["photo"], W, H, s.get("focus", 0.5)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # плашка «Фільм на вихідні» з хлопавкою
    fh = font(FILM["sans"], 64, 800)
    label = s.get("label", "Фільм на вихідні")
    lw = tw(d, label, fh)
    x0 = (W - lw - 110) / 2
    d.rounded_rectangle([x0 - 40, 80, x0 + lw + 120, 210], 40, fill=(255, 255, 255, 205))
    put(d, (x0, 104), label, fh, (25, 25, 25))
    ov.alpha_composite(clapper(66), (int(x0 + lw + 30), 112))
    # квитки
    t1 = ticket("КІНО", "ВХІДНИЙ", (250, 190, 50), w=330, h=150, angle=-10)
    t2 = ticket("КІНО", "ВХІДНИЙ", (240, 110, 60), w=330, h=150, angle=-4)
    ov.alpha_composite(t1, (W - t1.size[0] - 40, 235))
    ov.alpha_composite(t2, (W - t2.size[0] - 10, 420))
    # нижня непрозора плашка з назвою
    bx0, bx1 = 70, W - 70
    title = s["title"]
    sub = s.get("subtitle", "")
    ft = font(FILM["sans_bi"], 54, 800)
    fsub, sl, ss = fit(d, sub, FILM["sans"], bx1 - bx0 - 90, 130, 38, 28, 500, 1.3)
    tl = wrap(d, title, ft, bx1 - bx0 - 90)
    th = len(tl) * 54 * 1.2 + (len(sl) * ss * 1.3 + 18 if sub else 0)
    by1 = H - 70
    by0 = by1 - th - 80
    d.rounded_rectangle([bx0, by0, bx1, by1], 34, fill=FILM["orange"] + (245,))
    y = block(d, W / 2, by0 + 40, tl, ft, 54, (30, 22, 18), 1.2, "c")
    if sub:
        block(d, W / 2, y + 18, sl, fsub, ss, (30, 22, 18), 1.3, "c")
    return Image.alpha_composite(img, ov).convert("RGB")


def s_f_text(s, base, i, n):
    img = Image.new("RGB", (W, H), FILM["bg"]).convert("RGBA")
    strip = film_strip(130)
    img.alpha_composite(strip, (W - strip.size[0] - 70, 60))
    img = img.convert("RGB")
    d = film_frame(img, i, n)
    rich_draw(d, s["text"], W / 2, H / 2 + 30, W - 220, 820, s.get("size", 46), 30)
    return img


RENDER = {"f_cover": s_f_cover, "f_text": s_f_text, "m_cover": s_m_cover, "m_point": s_m_point, "m_final": s_m_final, "still": s_still, "cover": s_cover, "hook": s_hook, "content": s_content, "text": s_text,
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
