"""Collect candidate articles from Tier-2 feeds for a date window.

    python scripts/jev/fetch_candidates.py --days 7 --out candidates.json

Feed-only and read-only: touches nothing in the repo. Full article text is
fetched because Jev cannot credit evidence it cannot see — the profile
benchmark scored systematically low when fed summaries.
"""

import argparse
import datetime as dt
import html
import json
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sources import BLIND_SPOTS, FEEDS, FIRST_PARTY

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36"
NS = {"atom": "http://www.w3.org/2005/Atom"}


def curl(url, timeout=45):
    try:
        r = subprocess.run(["curl", "-sL", "--max-time", str(timeout), "-A", UA, url],
                           capture_output=True, text=True, timeout=timeout + 15)
        return r.stdout
    except Exception:
        return ""


def strip_html(raw):
    raw = re.sub(r"(?is)<(script|style|nav|header|footer|svg|form)[^>]*>.*?</\1>", " ", raw)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", raw))).strip()


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            d = dt.datetime.strptime(s, fmt)
            return d.replace(tzinfo=None) if d.tzinfo is None else d.astimezone(dt.timezone.utc).replace(tzinfo=None)
        except ValueError:
            continue
    if m := re.search(r"(\d{4}-\d{2}-\d{2})", s):
        return dt.datetime.strptime(m.group(1), "%Y-%m-%d")
    return None


def feed_entries(xml_text):
    """Yield (title, link, published) from RSS or Atom."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        def get(*names):
            for n in names:
                el = item.find(n) if "}" not in n else item.find(n, NS)
                if el is None:
                    for child in item:
                        if child.tag.split("}")[-1] == n:
                            el = child
                            break
                if el is not None:
                    return (el.text or el.get("href") or "").strip()
            return ""
        link = get("link")
        if not link:
            for child in item:
                if child.tag.split("}")[-1] == "link" and child.get("href"):
                    link = child.get("href")
                    break
        yield get("title"), link, get("pubDate", "published", "updated")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--max-per-source", type=int, default=6)
    ap.add_argument("--max-chars", type=int, default=14000)
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    cutoff = now - dt.timedelta(days=args.days)
    candidates, stats = [], {}

    for name, feed_url in FEEDS.items():
        raw = curl(feed_url, 30)
        if not raw:
            stats[name] = "feed unreachable"
            print(f"  {name:<28} FEED UNREACHABLE")
            continue
        picked = []
        for title, link, pub in feed_entries(raw):
            d = parse_date(pub)
            if not link or (d and d < cutoff):
                continue
            if d is None:          # undated entry: keep, flag for the record
                pass
            picked.append((title, link, d))
            if len(picked) >= args.max_per_source:
                break
        for title, link, d in picked:
            text = strip_html(curl(link))
            candidates.append({
                "title": title[:200],
                "source": name,
                "url": link,
                "published": d.strftime("%Y-%m-%d") if d else "",
                "first_party": name in FIRST_PARTY,
                "text": text[:args.max_chars],
                "text_chars": len(text),
                # Below this, the fetch almost certainly hit a paywall or a
                # JS-rendered shell. Judging such an item would be judging its
                # title, so it is flagged rather than scored.
                "text_ok": len(text) >= 500,
            })
        stats[name] = f"{len(picked)} in window"
        print(f"  {name:<28} {len(picked)} in window")

    payload = {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": args.days,
        "sources_ok": stats,
        "blind_spots": sorted(BLIND_SPOTS),   # no feed; excluded from accuracy claims
        "candidates": candidates,
    }
    args.out.write_text(json.dumps(payload, indent=1))
    thin = sum(1 for c in candidates if c["text_chars"] < 500)
    print(f"\n{len(candidates)} candidates from {len(FEEDS)} feeds "
          f"({thin} with <500 chars of text)")
    print(f"blind spots (no feed, excluded from accuracy): {', '.join(sorted(BLIND_SPOTS))}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
