#!/usr/bin/env python3
"""Extract public business contacts (emails, phones, Telegram) from company sites.

Usage: python3 -I extract_contacts.py URL [URL ...]   -> CSV on stdout
"""
import csv, re, sys, time, urllib.request, urllib.parse

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+?998|\+?7|\+?\d{1,3})[\s().-]*\d{2}[\s().-]*\d{3}[\s().-]*\d{2}[\s().-]*\d{2}")
TG = re.compile(r"(?:https?://)?t\.me/[A-Za-z0-9_]{4,}")
PAGES = ["", "/contact", "/contacts", "/kontakt", "/aloqa", "/about"]
BAD_EMAIL = (".png", ".jpg", ".gif", ".webp", "sentry", "example.")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 lead-finder"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read(400_000).decode("utf-8", "ignore")
    except Exception:
        return ""


def scan(site):
    if not site.startswith("http"):
        site = "https://" + site
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(site))
    emails, phones, tgs = set(), set(), set()
    for path in PAGES:
        html = fetch(base + path)
        emails |= {e.lower() for e in EMAIL.findall(html) if not any(b in e.lower() for b in BAD_EMAIL)}
        phones |= {re.sub(r"\s+", " ", p).strip() for p in PHONE.findall(html)}
        tgs |= set(TG.findall(html))
        time.sleep(1)
    return base, sorted(emails), sorted(phones)[:5], sorted(tgs)


if __name__ == "__main__":
    w = csv.writer(sys.stdout)
    w.writerow(["website", "emails", "phones", "telegram"])
    for u in sys.argv[1:]:
        b, e, p, t = scan(u)
        w.writerow([b, "; ".join(e), "; ".join(p), "; ".join(t)])
