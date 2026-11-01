"""Luxury gold ending overlay for the Porsche premium-reveal video.

usage: python3 ending.py LOGO_IMAGE OUT_DIR
Renders a 1080x1920 RGBA PNG sequence (24 fps, 5 s).
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ending import clean_logo  # noqa: E402

W, H, FPS, LENGTH = 1080, 1920, 24, 5.0
FONT_B = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONT_M = "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf"
GOLD = [(255, 238, 180), (214, 160, 62), (255, 214, 120), (170, 112, 30)]


def ease(t):
    t = min(max(t, 0), 1)
    return 1 - (1 - t) ** 3


def spaced_mask(text, font, spacing):
    widths = [font.getlength(c) for c in text]
    w = int(sum(widths) + spacing * (len(text) - 1)) + 20
    asc, desc = font.getmetrics()
    m = Image.new("L", (w, asc + desc + 20), 0)
    d = ImageDraw.Draw(m)
    x = 10
    for c, cw in zip(text, widths):
        d.text((x, 10), c, font=font, fill=255)
        x += cw + spacing
    return m


def gold_fill(size):
    w, h = size
    g = Image.new("RGB", (1, h))
    for y in range(h):
        k = y / max(1, h - 1) * (len(GOLD) - 1)
        i = min(int(k), len(GOLD) - 2)
        f = k - i
        g.putpixel((0, y), tuple(int(GOLD[i][j] + (GOLD[i + 1][j] - GOLD[i][j]) * f) for j in range(3)))
    return g.resize((w, h)).convert("RGBA")


def text_layer(text, font, spacing, shine=None, color=None):
    m = spaced_mask(text, font, spacing)
    fill = gold_fill(m.size) if color is None else Image.new("RGBA", m.size, color)
    if shine is not None:  # diagonal light band sweeping across, 0..1
        band = Image.new("L", m.size, 0)
        bx = int(-200 + shine * (m.width + 400))
        ImageDraw.Draw(band).polygon([(bx, 0), (bx + 70, 0), (bx + 20, m.height), (bx - 50, m.height)], fill=230)
        band = band.filter(ImageFilter.GaussianBlur(12))
        fill.paste((255, 255, 255, 255), (0, 0), band)
    out = Image.new("RGBA", m.size, (0, 0, 0, 0))
    out.paste(fill, (0, 0), m)
    glow = Image.new("RGBA", m.size, (255, 190, 80, 0))
    glow.putalpha(m.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.45)))
    glow.alpha_composite(out)
    return glow


def put(canvas, img, cx, cy, alpha=1.0, scale=1.0, blur=0):
    if alpha <= 0:
        return
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BICUBIC)
    if blur > 0.3:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 1:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def main(logo_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    logo = clean_logo(logo_path, width=640)
    f_title = ImageFont.truetype(FONT_B, 62)
    f_model = ImageFont.truetype(FONT_M, 30)
    f_cta = ImageFont.truetype(FONT_B, 40)
    model = text_layer("2026  ·  PORSCHE 911 CARRERA RS 2.7", f_model, 4, color=(235, 225, 205, 255))
    cta1 = text_layer("BUYURTMA UCHUN", f_cta, 6, color=(255, 255, 255, 255))
    cta2 = text_layer("PASTDAGI LINKNI BOSING", f_cta, 6)
    y_logo, y_title, y_model, y_cta1, y_cta2, y_arrow = 290, 1385, 1462, 1540, 1598, 1668

    for f in range(int(LENGTH * FPS)):
        t = f / FPS
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)

        k = ease(t / 0.9)
        put(c, logo, W / 2, y_logo + (1 - k) * 20, alpha=k, scale=0.92 + 0.08 * k, blur=(1 - k) * 8)

        # tracking-in title with a shine sweep
        k = ease((t - 0.7) / 0.9)
        if k > 0:
            spacing = int(14 + (1 - k) * 30)
            shine = (t - 1.7) / 0.9 if 1.7 <= t <= 2.6 else None
            put(c, text_layer("SUPER TREASURE HUNT", f_title, spacing, shine=shine), W / 2, y_title, alpha=k)

        # thin gold lines drawing outward from the centre
        k = ease((t - 0.5) / 0.7)
        if k > 0:
            half = int(380 * k)
            for y in (y_title - 52, y_title + 44):
                d.line([(W / 2 - half, y), (W / 2 + half, y)], fill=(214, 160, 62, 220), width=2)

        k = ease((t - 1.2) / 0.6)
        put(c, model, W / 2, y_model, alpha=k)

        for i, (img, y) in enumerate(((cta1, y_cta1), (cta2, y_cta2))):
            k = ease((t - 1.8 - i * 0.2) / 0.6)
            put(c, img, W / 2, y + (1 - k) * 30, alpha=k)

        # pulsing gold chevron
        if t >= 2.4:
            a = min(1, (t - 2.4) / 0.4) * (0.65 + 0.35 * math.sin((t - 2.4) * 4))
            bob = math.sin((t - 2.4) * 4) * 6
            cy = y_arrow + bob
            d.line([(W / 2 - 34, cy - 14), (W / 2, cy + 14), (W / 2 + 34, cy - 14)],
                   fill=(255, 214, 120, int(255 * a)), width=6, joint="curve")

        c.save(os.path.join(out_dir, f"f{f:04d}.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
