"""Uy plani: qo'lda chizilgan eskizdan raqamli dizayn (SVG) yaratadi.

Ishga tushirish:  python3 uy-plani/generate.py
Natija:           uy-plani/uy-plani.svg (1-qavat), uy-plani-2qavat.svg (2-qavat)
"""
from pathlib import Path

S = 60            # 1 metr = 60 px
M = 130           # chetdagi bo'sh joy (px)
W, H = 7.6, 16.5  # uy o'lchami (m)
TO, TI = 0.4, 0.2 # tashqi / ichki devor qalinligi (m)
B = 3.5           # darvozaxona qismi (eskizda yo'q), uyning shimoliy uchida
TER = 2.6         # hovli tomondagi ayvon (terassa) chuqurligi

out = []


def px(v):
    return M + v * S


def rect(x, y, w, h, **a):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    out.append(f'<rect x="{px(x):.1f}" y="{px(y):.1f}" width="{w*S:.1f}" height="{h*S:.1f}" {attrs}/>')


def line(x1, y1, x2, y2, **a):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    out.append(f'<line x1="{px(x1):.1f}" y1="{px(y1):.1f}" x2="{px(x2):.1f}" y2="{px(y2):.1f}" {attrs}/>')


def text(x, y, s, size=15, weight=400, fill="#2b2b2b", anchor="middle", rot=None):
    t = f' transform="rotate({rot} {px(x):.1f} {px(y):.1f})"' if rot else ""
    out.append(f'<text x="{px(x):.1f}" y="{px(y):.1f}" font-size="{size}" font-weight="{weight}" '
               f'fill="{fill}" text-anchor="{anchor}"{t}>{s}</text>')


# ---------- xonalar (o'q bo'yicha o'lchamlar) ----------
def build(floor):
    out.clear()
    ROOMS1 = [
        # nom, x, y, w, h, rang
        ("Yotoqxona 1", 1.8, 0, 5.8, 3.5, "#f3e9dc"),
        ("Sanuzel", 0, 0, 1.8, 3.5, "#dcebf2"),
        ("Yotoqxona 2", 0, 3.5, 4.0, 3.0, "#f3e9dc"),
        ("Zina", 0, 6.5, 1.5, 3.0, "#e8e8e8"),
        ("Hammom", 1.5, 6.5, 2.5, 1.8, "#dcebf2"),
        ("Dahliz", 1.5, 8.3, 2.5, 1.2, "#efeee9"),
        ("Yotoqxona 3", 0, 9.5, 4.0, 3.5, "#f3e9dc"),
        ("Mehmonxona (zal)", 4.0, 3.5, 3.6, 9.5, "#e9f0e1"),
        ("Ovqatlanish xonasi", 0, 13, 5.0, 3.5, "#f6efd9"),
        ("Oshxona", 5.0, 13, 2.6, 3.5, "#f6efd9"),
    ]
    ROOMS2 = [
        ("Yotoqxona 4", 1.8, 0, 5.8, 3.5, "#f3e9dc"),
        ("Sanuzel", 0, 0, 1.8, 3.5, "#dcebf2"),
        ("Yotoqxona 5", 0, 3.5, 4.0, 3.0, "#f3e9dc"),
        ("Zina", 0, 6.5, 1.5, 3.0, "#e8e8e8"),
        ("Dahliz", 1.5, 6.5, 2.5, 1.2, "#efeee9"),
        ("Hammom", 1.5, 7.7, 2.5, 1.8, "#dcebf2"),
        ("Yotoqxona 6", 0, 9.5, 4.0, 3.5, "#f3e9dc"),
        ("Oilaviy zal", 4.0, 3.5, 3.6, 9.5, "#e9f0e1"),
        ("Bolalar xonasi", 0, 13, 5.0, 3.5, "#f3e9dc"),
        ("Kabinet", 5.0, 13, 2.6, 3.5, "#f6efd9"),
    ]
    ROOMS = ROOMS1 if floor == 1 else ROOMS2
    for _, x, y, w, h, c in ROOMS:
        rect(x, y, w, h, fill=c)

    # pol plitkasi (ho'l xonalar)
    for _, x, y, w, h, c in ROOMS:
        if c == "#dcebf2":
            k = 0.3
            i = x + k
            while i < x + w:
                line(i, y, i, y + h, stroke="#c4d9e3", stroke_width=0.6)
                i += k
            j = y + k
            while j < y + h:
                line(x, j, x + w, j, stroke="#c4d9e3", stroke_width=0.6)
                j += k

    # ---------- devorlar ----------
    WALL = "#3a3a3a"
    rect(0, 0, W, TO, fill=WALL)
    rect(0, H - TO, W, TO, fill=WALL)
    rect(0, 0, TO, H, fill=WALL)
    rect(W - TO, 0, TO, H, fill=WALL)

    # ---------- darvozaxona qismi (y -B..0): 1-qavatda darvoza yo'lagi, 2-qavatda ayvon ----------
    rect(0, -B, W, B, fill="#e4e1da" if floor == 1 else "#efe3cf")
    rect(0, -B, W, TO, fill=WALL)
    rect(0, -B, TO, B, fill=WALL)
    for cx in (0, W):
        rect(min(cx, W - 0.4), -B, 0.4, 0.4, fill="#111")
    if floor == 1:
        # ko'cha tomondagi darvoza (2,8 m)
        rect(0, -B + 0.35, TO, 2.8, fill="#e4e1da")
        line(0.2, -B + 0.35, 1.4, -B + 1.2, stroke="#5a3a24", stroke_width=3)
        line(0.2, -0.35, 1.4, -1.2, stroke="#5a3a24", stroke_width=3)
        out.append(f'<path d="M{px(1.0):.1f},{px(-B/2):.1f} L{px(W-0.6):.1f},{px(-B/2):.1f}" stroke="#888" stroke-width="1.5" stroke-dasharray="6 4" marker-end="url(#arr)"/>')
        text(W / 2, -B / 2 - 0.35, "Darvozaxona (yo'lak)", size=16, weight=700)
        text(W / 2, -B / 2 + 0.55, f"{W*B:.1f} m² · ko'chadan hovliga", size=12, fill="#666")
    else:
        line(W - 0.1, -B + 0.4, W - 0.1, 0, stroke="#5a3a24", stroke_width=4)  # panjara
        text(W / 2, -B / 2 - 0.1, "Ayvon (darvoza ustida)", size=16, weight=700)
        text(W / 2, -B / 2 + 0.22, f"{W*B:.1f} m²", size=13, fill="#666")

    # ---------- hovli tomoni: terassa (1-qavat) / balkon (2-qavat) ----------
    rect(W, 4.6, TER, 6.8, fill="#e7e2d6" if floor == 1 else "#efe3cf", stroke="#555", stroke_width=1.5)
    for cz in (6.0, 10.0):
        out.append(f'<circle cx="{px(W+2.2):.1f}" cy="{px(cz):.1f}" r="{0.17*S:.1f}" fill="#fff" stroke="#333" stroke-width="2"/>')
    if floor == 1:
        for z0, z1 in ((3.0, 4.6), (11.4, 13.0)):   # ikki tomondagi zinalar
            rect(W, z0, TER, z1 - z0, fill="#f1eee8", stroke="#555", stroke_width=1)  # zina eni = ayvon chuqurligi
            for i in range(1, 6):
                zz = z0 + i * (z1 - z0) / 6
                line(W, zz, W + TER, zz, stroke="#888", stroke_width=1)
        text(W + TER / 2, 8.9, "Ayvon", size=14, weight=700, rot=-90)
    else:
        line(W + TER, 4.6, W + TER, 11.4, stroke="#5a3a24", stroke_width=4)
        line(W, 4.6, W + TER, 4.6, stroke="#5a3a24", stroke_width=4)
        line(W, 11.4, W + TER, 11.4, stroke="#5a3a24", stroke_width=4)
        text(W + TER / 2, 9.6, "Balkon", size=14, weight=700, rot=-90)
    text(-1.8, H / 2, "KO'CHA", size=14, weight=800, fill="#888", rot=-90)
    text(W + TER + 0.7, 1.5, "HOVLI", size=14, weight=800, fill="#888", rot=-90)


    def hwall(x1, x2, y):
        rect(x1, y - TI / 2, x2 - x1, TI, fill=WALL)


    def vwall(x, y1, y2):
        rect(x - TI / 2, y1, TI, y2 - y1, fill=WALL)


    # 2-qavat devorlari 1-qavat devorlari ustida turadi (faqat hammom/dahliz to'sig'i boshqacha)
    hwall(0, W, 3.5)
    hwall(0, 4.0, 6.5)
    hwall(1.5, 4.0, 8.3 if floor == 1 else 7.7)
    hwall(0, 4.0, 9.5)
    hwall(0, W, 13)
    vwall(1.8, 0, 3.5)
    vwall(4.0, 3.5, 13)
    vwall(1.5, 6.5 if floor == 1 else 7.7, 9.5)
    vwall(5.0, 13, H)

    # ustunlar (eskizdagi X belgilar)
    for cx, cy in [(0, 0), (4.0, 0), (W, 0), (0, 3.5), (W, 3.5), (0, 6.5), (4.0, 6.5),
                   (0, 9.5), (4.0, 9.5), (0, 13), (W, 13), (0, H), (4.0, H), (W, H)]:
        x = min(max(cx - 0.2, 0), W - 0.4)
        y = min(max(cy - 0.2, 0), H - 0.4)
        rect(x, y, 0.4, 0.4, fill="#111")
        line(x, y, x + 0.4, y + 0.4, stroke="#777", stroke_width=1)
        line(x + 0.4, y, x, y + 0.4, stroke="#777", stroke_width=1)


    # ---------- eshiklar ----------
    def door(orient, pos, a, b, swing, hinge="a", bg="#ffffff"):
        """orient: 'h' (gorizontal devor, y=pos) yoki 'v' (vertikal, x=pos).
        a..b: ochiq oraliq. swing: +1 / -1 ochilish tomoni."""
        t = TO if pos in (0, W, H) else TI
        L = b - a
        if orient == "h":
            y0 = pos - t / 2 if t == TI else (pos if pos == 0 else pos - t)
            rect(a, y0, L, t, fill=bg)
            hx = a if hinge == "a" else b
            fx = b if hinge == "a" else a
            edge = pos
            ey = edge + swing * L
            line(hx, edge, hx, ey, stroke="#222", stroke_width=2.5)
            sweep = 1 if (hinge == "a") == (swing > 0) else 0
            out.append(f'<path d="M{px(fx):.1f},{px(edge):.1f} A{L*S:.1f},{L*S:.1f} 0 0 {sweep} '
                       f'{px(hx):.1f},{px(ey):.1f}" fill="none" stroke="#888" stroke-width="1" stroke-dasharray="4 3"/>')
        else:
            x0 = pos - t / 2 if t == TI else (pos if pos == 0 else pos - t)
            rect(x0, a, t, L, fill=bg)
            hy = a if hinge == "a" else b
            fy = b if hinge == "a" else a
            edge = pos
            ex = edge + swing * L
            line(edge, hy, ex, hy, stroke="#222", stroke_width=2.5)
            sweep = 0 if (hinge == "a") == (swing > 0) else 1
            out.append(f'<path d="M{px(edge):.1f},{px(fy):.1f} A{L*S:.1f},{L*S:.1f} 0 0 {sweep} '
                       f'{px(ex):.1f},{px(hy):.1f}" fill="none" stroke="#888" stroke-width="1" stroke-dasharray="4 3"/>')


    door("h", 3.5, 6.3, 7.2, -1, "b", "#f3e9dc")        # zal -> yotoqxona 1
    door("v", 1.8, 2.5, 3.2, -1, "b", "#dcebf2")        # yotoqxona 1 -> sanuzel
    door("v", 4.0, 5.4, 6.3, -1, "b", "#f3e9dc")        # zal -> yotoqxona 2
    if floor == 1:
        door("h", 8.3, 2.6, 3.3, -1, "a", "#dcebf2")    # dahliz -> hammom
    else:
        door("h", 7.7, 3.1, 3.8, 1, "b", "#dcebf2")     # dahliz -> hammom
    door("v", 4.0, 9.7, 10.6, -1, "a", "#f3e9dc")       # zal -> yotoqxona 3
    door("h", 13, 4.15, 4.95, 1, "a", "#f6efd9")        # zal -> ovqatlanish
    door("h", 13, 5.3, 6.1, 1, "a", "#f6efd9")         # zal -> oshxona
    if floor == 1:
        door("v", 5.0, 14.6, 15.4, -1, "b", "#f6efd9")   # ovqatlanish <-> oshxona
        rect(4.0 - TI / 2, 8.5, TI, 0.9, fill="#e9f0e1")  # zal -> dahliz (ochiq o'tish)
        rect(1.5 - TI / 2, 8.4, TI, 1.0, fill="#efeee9")  # dahliz -> zina
        door("v", W, 7.4, 8.5, -1, "a", "#e9f0e1")       # asosiy kirish eshigi
    else:
        rect(4.0 - TI / 2, 6.6, TI, 0.9, fill="#e9f0e1")  # zal -> dahliz (ochiq o'tish)
        door("h", 0, 2.0, 2.8, -1, "a", "#efe3cf")       # yotoqxona 4 -> ayvon
        door("v", W, 7.5, 8.4, 1, "a", "#e9f0e1")        # zal -> balkon


    # ---------- derazalar ----------
    def window(orient, pos, a, b):
        if orient == "h":
            y0 = 0 if pos == 0 else H - TO
            rect(a, y0, b - a, TO, fill="#ffffff", stroke="#222", stroke_width=1.2)
            line(a, y0 + TO / 2, b, y0 + TO / 2, stroke="#3b82c4", stroke_width=2)
        else:
            x0 = 0 if pos == 0 else W - TO
            rect(x0, a, TO, b - a, fill="#ffffff", stroke="#222", stroke_width=1.2)
            line(x0 + TO / 2, a, x0 + TO / 2, b, stroke="#3b82c4", stroke_width=2)


    window("h", 0, 2.6, 3.6)
    window("h", 0, 5.3, 6.6)
    window("v", W, 0.9, 2.3)
    window("v", 0, 4.3, 5.7)
    window("v", W, 4.4, 6.0)
    window("v", W, 10.3, 11.9)
    window("v", 0, 10.5, 11.9)
    window("v", 0, 14.1, 15.5)
    window("v", W, 14.1, 15.3)
    window("h", H, 1.6, 3.2)
    if floor == 2:
        pass

    # ---------- mebel ----------
    F = dict(fill="#ffffff", stroke="#6b6b6b", stroke_width=1.2, rx=4)


    def bed(x, y, w, h):
        rect(x, y, w, h, **F)
        rect(x + 0.15, y + 0.12, w / 2 - 0.25, 0.45, fill="#eee", stroke="#999", stroke_width=1, rx=6)
        rect(x + w / 2 + 0.1, y + 0.12, w / 2 - 0.25, 0.45, fill="#eee", stroke="#999", stroke_width=1, rx=6)
        line(x, y + 0.8, x + w, y + 0.8, stroke="#aaa", stroke_width=1)


    if floor == 1:
        # Yotoqxona 1
        bed(3.6, 0.5, 1.8, 2.0)
        rect(2.9, 0.5, 0.5, 0.45, **F); rect(5.6, 0.5, 0.5, 0.45, **F)
        rect(2.1, 2.6, 0.6, 0.7, **F)  # kreslo
        rect(6.6, 0.6, 0.6, 1.8, **F)  # shkaf
        # Sanuzel: unitaz, rakovina, dush
        out.append(f'<ellipse cx="{px(0.9):.1f}" cy="{px(1.0):.1f}" rx="{0.22*S:.1f}" ry="{0.3*S:.1f}" fill="#fff" stroke="#6b6b6b" stroke-width="1.2"/>')
        rect(0.65, 0.42, 0.5, 0.22, **F)
        rect(0.5, 2.6, 0.5, 0.45, **F)
        out.append(f'<circle cx="{px(0.75):.1f}" cy="{px(2.82):.1f}" r="{0.14*S:.1f}" fill="none" stroke="#999"/>')
        # Yotoqxona 2
        bed(0.5, 4.0, 1.6, 2.0)
        rect(2.6, 4.0, 1.1, 0.55, **F)  # stol
        # Zina: 9,3 dan 7,3 gacha ko'tariladi, 2-qavatdagi maydonchaga chiqadi
        for i in range(12):
            yy = 7.3 + i * 2.0 / 11
            line(0.45, yy, 1.4, yy, stroke="#777", stroke_width=1)
        out.append(f'<path d="M{px(0.92):.1f},{px(9.2):.1f} L{px(0.92):.1f},{px(7.45):.1f}" stroke="#444" stroke-width="1.5" marker-end="url(#arr)"/>')
        # Hammom: vanna, rakovina
        rect(1.75, 6.75, 0.75, 1.4, **F)
        rect(1.85, 6.85, 0.55, 1.2, fill="#eaf4f8", stroke="#999", stroke_width=1, rx=10)
        rect(3.25, 6.75, 0.5, 0.45, **F)
        # Yotoqxona 3
        bed(0.5, 10.0, 1.6, 2.0)
        rect(0.5, 12.2, 1.8, 0.55, **F)  # shkaf
        rect(2.9, 11.6, 0.8, 1.1, **F)
        # Mehmonxona
        rect(4.35, 5.0, 0.9, 2.4, **F)  # divan
        rect(4.45, 5.1, 0.25, 2.2, fill="#eee", stroke="#999", stroke_width=1, rx=3)
        rect(5.6, 5.6, 0.8, 1.2, fill="#f8f8f8", stroke="#6b6b6b", stroke_width=1.2, rx=4)  # jurnal stoli
        rect(7.0, 4.8, 0.25, 2.6, fill="#555", rx=2)   # TV
        out.append(f'<rect x="{px(4.6):.1f}" y="{px(9.0):.1f}" width="{2.6*S:.1f}" height="{1.7*S:.1f}" fill="#fff" stroke="#6b6b6b" stroke-width="1.2" rx="40"/>')  # dasturxon
        for cx in (5.0, 5.9, 6.8):
            for cy in (8.75, 10.95):
                out.append(f'<circle cx="{px(cx):.1f}" cy="{px(cy):.1f}" r="{0.2*S:.1f}" fill="#fff" stroke="#6b6b6b" stroke-width="1"/>')
        rect(4.35, 11.6, 0.5, 1.1, **F)
        # Ovqatlanish xonasi
        rect(1.0, 13.9, 2.4, 1.0, **F)
        for cx in (1.5, 2.2, 2.9):
            for cy in (13.6, 15.2):
                out.append(f'<circle cx="{px(cx):.1f}" cy="{px(cy):.1f}" r="{0.2*S:.1f}" fill="#fff" stroke="#6b6b6b" stroke-width="1"/>')
        # Oshxona: L shaklidagi stol-usti
        rect(6.6, 13.95, 0.6, 2.15, fill="#fafafa", stroke="#6b6b6b", stroke_width=1.2)
        rect(5.3, 15.5, 1.3, 0.6, fill="#fafafa", stroke="#6b6b6b", stroke_width=1.2)
        for cy in (14.4, 14.9):
            out.append(f'<circle cx="{px(6.9):.1f}" cy="{px(cy):.1f}" r="{0.15*S:.1f}" fill="none" stroke="#777"/>')
        rect(6.7, 15.4, 0.4, 0.35, fill="#eaf4f8", stroke="#888", stroke_width=1)  # moyka
        rect(6.6, 13.25, 0.6, 0.6, **F)  # muzlatgich

    else:
        # Yotoqxona 4
        bed(3.6, 0.5, 1.8, 2.0)
        rect(2.9, 0.5, 0.5, 0.45, **F); rect(5.6, 0.5, 0.5, 0.45, **F)
        rect(2.1, 2.6, 0.6, 0.7, **F)
        rect(6.6, 0.6, 0.6, 1.8, **F)
        # Sanuzel
        out.append(f'<ellipse cx="{px(0.9):.1f}" cy="{px(1.0):.1f}" rx="{0.22*S:.1f}" ry="{0.3*S:.1f}" fill="#fff" stroke="#6b6b6b" stroke-width="1.2"/>')
        rect(0.65, 0.42, 0.5, 0.22, **F)
        rect(0.5, 2.6, 0.5, 0.45, **F)
        out.append(f'<circle cx="{px(0.75):.1f}" cy="{px(2.82):.1f}" r="{0.14*S:.1f}" fill="none" stroke="#999"/>')
        # Yotoqxona 5
        bed(0.5, 4.0, 1.6, 2.0)
        rect(2.6, 4.0, 1.1, 0.55, **F)
        # Zina: maydoncha (6,6–7,3) va pastga tushadigan bo'shliq
        for i in range(12):
            yy = 7.3 + i * 2.0 / 11
            line(0.45, yy, 1.4, yy, stroke="#aaa", stroke_width=1, stroke_dasharray="4 3")
        out.append(f'<path d="M{px(0.92):.1f},{px(7.45):.1f} L{px(0.92):.1f},{px(9.2):.1f}" stroke="#444" stroke-width="1.5" marker-end="url(#arr)"/>')
        line(1.5, 7.3, 1.5, 7.7, stroke="#444", stroke_width=3)  # panjara
        # Hammom: vanna, rakovina
        rect(1.7, 8.7, 1.4, 0.65, **F)
        rect(1.8, 8.78, 1.2, 0.49, fill="#eaf4f8", stroke="#999", stroke_width=1, rx=10)
        rect(3.3, 8.75, 0.5, 0.45, **F)
        # Yotoqxona 6
        bed(0.5, 10.0, 1.6, 2.0)
        rect(0.5, 12.2, 1.8, 0.55, **F)
        rect(2.9, 11.6, 0.8, 1.1, **F)
        # Oilaviy zal
        rect(4.35, 5.0, 0.9, 2.4, **F)
        rect(4.45, 5.1, 0.25, 2.2, fill="#eee", stroke="#999", stroke_width=1, rx=3)
        rect(5.6, 5.6, 0.8, 1.2, fill="#f8f8f8", stroke="#6b6b6b", stroke_width=1.2, rx=4)
        rect(7.0, 4.8, 0.25, 2.6, fill="#555", rx=2)
        rect(6.3, 9.3, 0.75, 0.75, **F); rect(6.3, 10.4, 0.75, 0.75, **F)  # kreslolar
        out.append(f'<circle cx="{px(5.6):.1f}" cy="{px(10.1):.1f}" r="{0.35*S:.1f}" fill="#fff" stroke="#6b6b6b" stroke-width="1.2"/>')
        rect(4.35, 11.6, 0.5, 1.1, **F)  # kitob javoni
        # Bolalar xonasi: ikkita bir kishilik karavot, shkaf, stol
        for bx in (0.5, 1.8):
            rect(bx, 13.4, 0.9, 1.9, **F)
            rect(bx + 0.12, 13.5, 0.66, 0.4, fill="#eee", stroke="#999", stroke_width=1, rx=6)
        rect(0.5, 15.45, 1.6, 0.6, **F)
        rect(3.2, 15.45, 1.3, 0.6, **F)
        out.append(f'<circle cx="{px(3.85):.1f}" cy="{px(15.1):.1f}" r="{0.2*S:.1f}" fill="#fff" stroke="#6b6b6b" stroke-width="1"/>')
        # Kabinet
        rect(5.4, 15.4, 1.4, 0.65, **F)
        out.append(f'<circle cx="{px(6.1):.1f}" cy="{px(15.0):.1f}" r="{0.2*S:.1f}" fill="#fff" stroke="#6b6b6b" stroke-width="1"/>')
        rect(6.65, 13.3, 0.55, 1.6, **F)

    # ---------- xona nomlari ----------
    LABELS = {
        "Yotoqxona 1": (4.4, 3.0), "Sanuzel": (0.9, 1.85), "Yotoqxona 2": (3.05, 5.3),
        "Zina": None, "Hammom": (3.35, 7.55), "Dahliz": (2.75, 9.05),
        "Yotoqxona 3": (3.0, 11.1), "Mehmonxona (zal)": (5.8, 8.0),
        "Ovqatlanish xonasi": (2.2, 15.72), "Oshxona": (5.8, 14.6),
    } if floor == 1 else {
        "Yotoqxona 4": (4.4, 3.0), "Sanuzel": (0.9, 1.85), "Yotoqxona 5": (3.05, 5.3),
        "Dahliz": (2.75, 7.1), "Hammom": (2.3, 8.2), "Yotoqxona 6": (3.0, 11.1),
        "Oilaviy zal": (5.8, 8.0), "Bolalar xonasi": (3.6, 14.3), "Kabinet": (5.9, 14.3),
    }
    for name, x, y, w, h, _ in ROOMS:
        pos = LABELS.get(name)
        if not pos:
            continue
        lx, ly = pos
        small = w < 2.6 or h < 1.5
        text(lx, ly, name, size=12 if small else 16, weight=700)
        text(lx, ly + 0.32, f"{w*h:.1f} m²", size=11 if small else 13, fill="#666")
    text(1.0, 8.4, "ZINA", size=11, weight=700, rot=-90)

    if floor == 1:
        # kirish belgisi
        out.append(f'<path d="M{px(W+2.0):.1f},{px(7.95):.1f} L{px(W+0.45):.1f},{px(7.95):.1f}" stroke="#c0392b" stroke-width="3" marker-end="url(#arrR)"/>')
        text(W + 1.25, 7.6, "KIRISH", size=13, weight=700, fill="#c0392b")


    # ---------- o'lcham chiziqlari ----------
    def dim_h(x1, x2, y, label):
        line(x1, y, x2, y, stroke="#333", stroke_width=1)
        for xx in (x1, x2):
            line(xx, y - 0.15, xx, y + 0.15, stroke="#333", stroke_width=1)
            line(xx - 0.1, y + 0.1, xx + 0.1, y - 0.1, stroke="#333", stroke_width=1.6)
        text((x1 + x2) / 2, y - 0.12, label, size=13, weight=600)


    def dim_v(y1, y2, x, label):
        line(x, y1, x, y2, stroke="#333", stroke_width=1)
        for yy in (y1, y2):
            line(x - 0.15, yy, x + 0.15, yy, stroke="#333", stroke_width=1)
            line(x - 0.1, yy + 0.1, x + 0.1, yy - 0.1, stroke="#333", stroke_width=1.6)
        text(x - 0.15, (y1 + y2) / 2, label, size=13, weight=600, rot=-90)


    dim_h(0, 4.0, -B - 0.6, "4,00")
    dim_h(4.0, W, -B - 0.6, "3,60")
    dim_h(0, W, -B - 1.2, "7,60")
    dim_v(-B, 0, -0.6, "3,50")
    acc = 0
    for d in (3.5, 3.0, 3.0, 3.5, 3.5):
        dim_v(acc, acc + d, -0.6, f"{d:.2f}".replace(".", ","))
        acc += d
    dim_v(-B, H, -1.3, "20,00")

    # ---------- yig'ish ----------
    VW = 2 * M + (W + TER) * S + 150
    VH = M + (H + B) * S + 210
    header = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{VW:.0f}" height="{VH:.0f}" viewBox="0 0 {VW:.0f} {VH:.0f}" font-family="Inter, Segoe UI, Arial, sans-serif">
    <defs>
      <marker id="arr" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#444"/></marker>
      <marker id="arrR" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#c0392b"/></marker>
    </defs>
    <rect width="100%" height="100%" fill="#fbfaf7"/>
    <text x="{VW/2:.0f}" y="38" font-size="24" font-weight="800" text-anchor="middle" fill="#222">UY PLANI — {floor}-QAVAT</text>
    <text x="{VW/2:.0f}" y="62" font-size="13" text-anchor="middle" fill="#666">7,60 × 20,00 m (darvozaxona bilan) · M 1:100</text>
    <g transform="translate(0,{60 + B * S:.0f})">
    '''
    footer = f'''<g transform="translate({px(W + TER)+40:.0f},{px(H)-150:.0f})" font-size="12" fill="#333">
      <text font-weight="700">Belgilar</text>
      <rect y="12" width="26" height="8" fill="{WALL}"/><text x="34" y="20">Devor</text>
      <rect y="30" width="26" height="8" fill="#fff" stroke="#222"/><line x1="0" y1="34" x2="26" y2="34" stroke="#3b82c4" stroke-width="2"/><text x="34" y="38">Deraza</text>
      <rect y="48" width="10" height="10" fill="#111"/><text x="34" y="57">Ustun</text>
      <path d="M0,86 L0,66 A20,20 0 0 1 20,86" fill="none" stroke="#888" stroke-dasharray="4 3"/><line x1="0" y1="86" x2="0" y2="66" stroke="#222" stroke-width="2.5"/><text x="34" y="80">Eshik</text>
    </g>
    </g>
    </svg>'''

    name = "uy-plani.svg" if floor == 1 else "uy-plani-2qavat.svg"
    Path(__file__).with_name(name).write_text(header + "\n".join(out) + "\n" + footer, encoding="utf-8")
    print(name, "yaratildi")


for fl in (1, 2):
    build(fl)
