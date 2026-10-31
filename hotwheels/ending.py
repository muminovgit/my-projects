"""Render the animated ending overlay as a PNG frame sequence (1080x1920 RGBA).

usage: python3 ending.py LOGO_IMAGE OUT_DIR

Timeline (seconds from the start of the overlay):
  0.00-0.45  logo pops in with an overshoot bounce, then gently floats
  0.70       "BUYURTMA UCHUN" slides in from the left
  1.05       "PASTDAGI LINKNI" slides in from the right
  1.40       "BOSING" punches in (scale overshoot)
  1.80+      arrow bounces toward the link below
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from title import render_line, YELLOW, NAVY  # noqa: E402

W, H, FPS, LENGTH = 1080, 1920, 24, 4.9


def clean_logo(path, width=860):
    """Drop the baked-in checkerboard (grey/white, unsaturated) and add an outline."""
    im = Image.open(path).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, _ = px[x, y]
            if max(r, g, b) - min(r, g, b) < 45:
                px[x, y] = (0, 0, 0, 0)
    im = im.crop(im.getchannel("A").getbbox())
    im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
    pad = 30
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    a = Image.new("L", out.size, 0)
    a.paste(im.getchannel("A"), (pad, pad))
    for size, color in ((25, NAVY), (13, (255, 255, 255, 255))):
        m = a.filter(ImageFilter.MaxFilter(size))
        out.paste(Image.new("RGBA", out.size, color), (0, 0), m)
    out.alpha_composite(im, (pad, pad))
    return out


def ease_out_back(t, s=1.9):
    t = min(max(t, 0), 1) - 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2


def ease_out_cubic(t):
    t = min(max(t, 0), 1)
    return 1 - (1 - t) ** 3


def place(canvas, img, cx, cy, scale=1.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0:
        return
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))),
                         Image.BICUBIC)
    if alpha < 1:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(img.getchannel("A").point(lambda v: int(v * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    x, y = int(cx - img.width / 2), int(cy - img.height / 2)
    canvas.alpha_composite(sh, (x + 10, y + 14)) if x + 10 >= 0 else None
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tmp.paste(img, (x, y), img)
    canvas.alpha_composite(tmp)


def main(logo_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    logo = clean_logo(logo_path)
    lines = [render_line("BUYURTMA UCHUN", 92), render_line("PASTDAGI LINKNI", 92),
             render_line("BOSING", 140)]
    logo_y, ys = 330, [1180, 1295, 1430]
    n = int(LENGTH * FPS)
    for f in range(n):
        t = f / FPS
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # logo: pop with overshoot, then float + slight pulse
        k = ease_out_back(t / 0.45)
        float_y = math.sin(max(0, t - 0.45) * 2.4) * 10
        pulse = 1 + 0.025 * math.sin(max(0, t - 0.45) * 4.8)
        place(c, logo, W / 2, logo_y + float_y, scale=max(0, k) * pulse,
              alpha=min(1, t / 0.15))

        # line 1 from left, line 2 from right
        for i, (start, direction) in enumerate(((0.70, -1), (1.05, 1))):
            p = ease_out_cubic((t - start) / 0.35)
            if t >= start:
                x = W / 2 + direction * (1 - p) * W
                place(c, lines[i], x, ys[i], alpha=min(1, (t - start) / 0.15))

        # BOSING punch-in
        if t >= 1.40:
            k = ease_out_back((t - 1.40) / 0.35, s=2.6)
            place(c, lines[2], W / 2, ys[2], scale=max(0.01, 2.2 - 1.2 * k))

        # bouncing arrow
        if t >= 1.80:
            d = ImageDraw.Draw(c)
            bob = abs(math.sin((t - 1.80) * 5.5)) * 28
            cx, ay = W // 2, ys[2] + 95 + bob
            tri = [(cx - 70, ay), (cx + 70, ay), (cx, ay + 90)]
            d.polygon([(px, py + 6) for px, py in tri], fill=NAVY)
            d.polygon(tri, fill=YELLOW, outline=NAVY, width=8)

        c.save(os.path.join(out_dir, f"f{f:04d}.png"))
    print(n, "frames")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
