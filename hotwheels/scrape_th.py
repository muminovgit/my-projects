"""Collect Hot Wheels Treasure Hunt / Super Treasure Hunt lists and photos
from the Hot Wheels Wiki (hotwheels.fandom.com) via its MediaWiki API.

usage: python3 scrape_th.py OUT_DIR YEAR [YEAR ...]

Writes OUT_DIR/limited.csv and downloads each photo to OUT_DIR/images/.
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request

API = "https://hotwheels.fandom.com/api.php"
UA = {"User-Agent": "hotwheels-catalog-script/1.0 (personal reseller catalog)"}


def api(**params):
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def clean(cell):
    cell = re.sub(r"<br\s*/?>", " ", cell)
    cell = re.sub(r"<[^>]+>", "", cell)
    cell = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", cell)
    cell = cell.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", cell).strip()


def parse_page(year):
    data = api(action="parse", page=f"{year} Treasure Hunts Series", prop="wikitext")
    text = data["parse"]["wikitext"]["*"]
    rows, section = [], "Treasure Hunt"
    for block in re.split(r"\n(?===)|\n\|-", text):
        head = re.match(r"==+\s*(.*?)\s*==+", block.strip())
        if head:
            section = "Super Treasure Hunt" if "super" in head.group(1).lower() else "Treasure Hunt"
        lines = [l for l in block.split("\n") if l.startswith("|") and not l.startswith(("|}", "|+"))]
        cells = [l[1:] for l in lines]
        if len(cells) < 12:
            continue
        photo = next((c for c in cells if "[[File:" in c or "[[Image:" in c), "")
        m = re.search(r"\[\[(?:File|Image):([^|\]]+)", photo)
        rows.append({
            "year": year, "type": section,
            "toy_no": clean(cells[0]), "col_no": clean(cells[1]),
            "series": clean(cells[2]), "model": clean(cells[3]),
            "color": clean(cells[4]), "wheels": clean(cells[9]) if len(cells) > 9 else "",
            "file": m.group(1).strip() if m else "",
        })
    return rows


def resolve_urls(files):
    out = {}
    files = [f for f in set(files) if f]
    for i in range(0, len(files), 40):
        batch = files[i:i + 40]
        data = api(action="query", prop="imageinfo", iiprop="url",
                   titles="|".join("File:" + f for f in batch))
        norm = {n["to"]: n["from"] for n in data["query"].get("normalized", [])}
        for page in data["query"]["pages"].values():
            info = page.get("imageinfo")
            if info:
                title = norm.get(page["title"], page["title"])
                out[title[5:]] = info[0]["url"]
        time.sleep(0.5)
    return out


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")[:80]


def main(out_dir, years):
    os.makedirs(os.path.join(out_dir, "images"), exist_ok=True)
    rows = []
    for y in years:
        r = parse_page(y)
        print(f"{y}: {len(r)} cars")
        rows += r
        time.sleep(0.5)
    urls = resolve_urls(r["file"] for r in rows)
    for r in rows:
        r["image_url"] = urls.get(r["file"], "")
        r["image"] = ""
        if not r["image_url"]:
            continue
        ext = os.path.splitext(r["file"])[1].lower() or ".jpg"
        tag = "STH" if r["type"].startswith("Super") else "TH"
        name = safe_name(f"{r['year']}_{tag}_{r['toy_no']}_{r['model']}") + ext
        path = os.path.join(out_dir, "images", name)
        if not os.path.exists(path):
            req = urllib.request.Request(r["image_url"], headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp, open(path, "wb") as f:
                f.write(resp.read())
            time.sleep(0.3)
        r["image"] = "images/" + name
    fields = ["year", "type", "toy_no", "col_no", "series", "model", "color",
              "wheels", "image", "image_url"]
    with open(os.path.join(out_dir, "limited.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    got = sum(1 for r in rows if r["image"])
    print(f"total {len(rows)} rows, {got} images")


if __name__ == "__main__":
    main(sys.argv[1], [int(y) for y in sys.argv[2:]])
