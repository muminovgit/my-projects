"""Render a Hot Wheels-style call-to-action overlay as a transparent 1080x1920 PNG.

Style: heavy italic letters, red-to-orange gradient fill, yellow inner outline,
dark navy outer outline, extra forward slant and a drop shadow.
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/usr/share/fonts/opentype/inter/InterDisplay-BlackItalic.otf"
W, H = 1080, 1920
LINES = [("BUYURTMA UCHUN", 92), ("PASTDAGI LINKNI", 92), ("BOSING", 130)]
SLANT = 0.18   # extra forward lean
YELLOW, NAVY = (255, 214, 0, 255), (12, 20, 60, 255)


def gradient(w, h, top=(255, 40, 20), bottom=(255, 150, 0)):
    g = Image.new("RGBA", (w, h))
    px = g.load()
    for y in range(h):
        k = y / max(1, h - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)) + (255,)
        for x in range(w):
            px[x, y] = c
    return g


def render_line(text, size):
    font = ImageFont.truetype(FONT, size)
    pad = 40
    l, t, r, b = font.getbbox(text)
    w, h = r - l + pad * 2, b - t + pad * 2
    org = (pad - l, pad - t)

    def mask(stroke):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).text(org, text, font=font, fill=255,
                               stroke_width=stroke, stroke_fill=255)
        return m

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", (w, h), NAVY), (0, 0), mask(int(size * 0.17)))
    out.paste(Image.new("RGBA", (w, h), YELLOW), (0, 0), mask(int(size * 0.09)))
    fill = gradient(w, h)
    out.paste(fill, (0, 0), mask(0))
    # glossy highlight on upper half of the letters
    hl = Image.new("L", (w, h), 0)
    ImageDraw.Draw(hl).rectangle([0, 0, w, org[1] + int(size * 0.35)], fill=70)
    hl = Image.composite(hl, Image.new("L", (w, h), 0), mask(0))
    out.paste(Image.new("RGBA", (w, h), (255, 255, 255, 255)), (0, 0), hl)

    # extra slant: shear right
    extra = int(h * SLANT)
    out = out.transform((w + extra, h), Image.AFFINE,
                        (1, SLANT, -extra, 0, 1, 0), Image.BICUBIC)
    return out


def main(path):
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    imgs = [render_line(t, s) for t, s in LINES]
    total = sum(i.height for i in imgs) - 45 * (len(imgs) - 1)
    y = H - total - 300            # keep clear of Instagram's bottom UI
    for img in imgs:
        x = (W - img.width) // 2
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow.putalpha(img.getchannel("A").point(lambda a: int(a * 0.6)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        canvas.alpha_composite(shadow, (x + 10, y + 14))
        canvas.alpha_composite(img, (x, y))
        y += img.height - 45

    # down arrow pointing to the link
    d = ImageDraw.Draw(canvas)
    cx, ay = W // 2, y + 20
    tri = [(cx - 70, ay), (cx + 70, ay), (cx, ay + 90)]
    d.polygon([(px, py + 6) for px, py in tri], fill=NAVY)
    d.polygon(tri, fill=YELLOW, outline=NAVY, width=8)
    canvas.save(path)


if __name__ == "__main__":
    main(sys.argv[1])
