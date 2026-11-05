"""What doomscrolling is actually eating.

Real timelines, not headlines only: Bluesky's public feed, a Mastodon public
timeline, the Hacker News front page, and a couple of RSS firehoses. Anything
unreachable is skipped and reported, never invented.

Every item is normalised to {source, author, text, url} so the state can say who
said it, and the sample is uniformly random across *sources*, not across items —
one loud feed must not take over the scroll.
"""
from __future__ import annotations

import json
import random
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

RNG = random.SystemRandom()
CACHE = Path.home() / ".hermes/plugin-data/antemuse-states/social.json"
TTL = 600
UA = "antemuse-states/0.7 (+https://antemuse.com)"
TIMEOUT = 8

SOURCES = {
    "bluesky": "https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed"
               "?feed=at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot&limit=40",
    "mastodon": "https://fosstodon.org/api/v1/timelines/public?limit=30",
    "hn": "https://hn.algolia.com/api/v1/search?tags=front_page",
    "rss": None,
}

FEEDS = [
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml",
]


def _get(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = r.read().decode("utf-8", "replace")
    try:
        return json.loads(body)
    except Exception:
        return body


def _clean(text: str, limit: int = 220) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = " ".join(text.split())
    return text[:limit]


def _bluesky() -> List[Dict[str, str]]:
    data = _get(SOURCES["bluesky"])
    out = []
    for item in data.get("feed", []):
        post = item.get("post") or {}
        author = (post.get("author") or {}).get("handle", "someone")
        text = _clean((post.get("record") or {}).get("text", ""))
        if text:
            out.append({"source": "bluesky", "author": author, "text": text,
                        "url": f"https://bsky.app/profile/{author}"})
    return out


def _mastodon() -> List[Dict[str, str]]:
    data = _get(SOURCES["mastodon"])
    out = []
    for st in data if isinstance(data, list) else []:
        text = _clean(re.sub(r"<[^>]+>", " ", st.get("content", "")))
        if text:
            out.append({"source": "mastodon", "author": (st.get("account") or {}).get("acct", "someone"),
                        "text": text, "url": st.get("url", "")})
    return out


def _hn() -> List[Dict[str, str]]:
    data = _get(SOURCES["hn"])
    out = []
    for hit in (data.get("hits") or [])[:30]:
        text = _clean(hit.get("title") or hit.get("story_text") or "")
        if text:
            out.append({"source": "hn", "author": hit.get("author", "someone"), "text": text,
                        "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"})
    return out


def _rss() -> List[Dict[str, str]]:
    out = []
    for url in FEEDS:
        try:
            body = _get(url)
        except Exception:
            continue
        for block in re.findall(r"<item[^>]*>(.*?)</item>", body, re.S)[:12]:
            t = re.search(r"<title[^>]*>(.*?)</title>", block, re.S)
            if t:
                out.append({"source": url.split("/")[2], "author": "feed",
                            "text": _clean(t.group(1), 140), "url": ""})
    return out


FETCHERS = {"bluesky": _bluesky, "mastodon": _mastodon, "hn": _hn, "rss": _rss}


def fetch_all() -> Dict[str, Any]:
    items: List[Dict[str, str]] = []
    failed: List[str] = []
    for name, fn in FETCHERS.items():
        try:
            got = fn()
            items += got
            if not got:
                failed.append(name)
        except Exception:
            failed.append(name)
    return {"at": time.time(), "items": items, "failed": failed}


def cache(refresh: bool = False, ttl: int = TTL) -> Dict[str, Any]:
    if CACHE.exists() and not refresh:
        try:
            data = json.loads(CACHE.read_text())
            if time.time() - data.get("at", 0) < ttl and data.get("items"):
                return data
        except Exception:
            pass
    data = fetch_all()
    if data["items"]:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(data))
    return data


def pick(steps: int = 1) -> List[str]:
    """Uniform across sources first, then across items — no feed hogging the scroll."""
    data = cache()
    items = data.get("items") or []
    if not items:
        missing = ", ".join(data.get("failed") or []) or "no network"
        return [f"feed unavailable · {missing}"]
    by_source: Dict[str, List[Dict[str, str]]] = {}
    for item in items:
        by_source.setdefault(item["source"], []).append(item)
    out = []
    for _ in range(steps):
        source = RNG.choice(list(by_source))
        item = RNG.choice(by_source[source])
        out.append(f"{item['source']} · @{item['author']} · {item['text']}")
    return out
