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
from . import storage

CACHE = storage.data_dir() / "social.json"
TTL = 600
UA = "antemuse/0.9 (+https://antemuse.com)"
TIMEOUT = 8

#: Every feed is one draw from a pool that is shuffled per fetch, so a scroll does not
#: keep returning the same timeline because it was the first one that answered.
BLUESKY_FEEDS = [
    "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot",
    "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/thevids",
    "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/with-friends",
    "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/science",
]

MASTODON_INSTANCES = [
    "https://fosstodon.org", "https://mastodon.social", "https://hachyderm.io",
    "https://mstdn.social", "https://techhub.social",
]

SOURCES = {
    "bluesky": "https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed?feed={feed}&limit=40",
    "mastodon": "{instance}/api/v1/timelines/public?limit=30",
    "hn": "https://hn.algolia.com/api/v1/search?tags=front_page",
    "rss": None,
}

FEEDS = [
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://lwn.net/headlines/rss",
    "https://www.quantamagazine.org/feed/",
    "https://phys.org/rss-feed/",
    "https://news.ycombinator.com/rss",
    "https://www.sciencedaily.com/rss/top/science.xml",
    "https://www.eff.org/rss/updates.xml",
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


def _rotate() -> Dict[str, Any]:
    """Which feeds this fetch will try, shuffled — the pool is not sampled twice the same."""
    return {
        "bluesky": RNG.sample(BLUESKY_FEEDS, min(2, len(BLUESKY_FEEDS))),
        "mastodon": RNG.sample(MASTODON_INSTANCES, min(2, len(MASTODON_INSTANCES))),
        "rss": RNG.sample(FEEDS, min(4, len(FEEDS))),
    }


def _bluesky(feeds: List[str] | None = None) -> List[Dict[str, str]]:
    feeds = feeds or _rotate()["bluesky"]
    data: Dict[str, Any] = {"feed": []}
    for feed in feeds:
        try:
            got = _get(SOURCES["bluesky"].format(feed=feed))
        except Exception:
            continue
        data["feed"].extend((got or {}).get("feed", []) if isinstance(got, dict) else [])
    out = []
    for item in data.get("feed", []):
        post = item.get("post") or {}
        author = (post.get("author") or {}).get("handle", "someone")
        text = _clean((post.get("record") or {}).get("text", ""))
        if text:
            out.append({"source": "bluesky", "author": author, "text": text,
                        "url": f"https://bsky.app/profile/{author}"})
    return out


def _mastodon(instances: List[str] | None = None) -> List[Dict[str, str]]:
    instances = instances or _rotate()["mastodon"]
    merged: List[Any] = []
    for host in instances:
        try:
            got = _get(SOURCES["mastodon"].format(instance=host))
        except Exception:
            continue
        if isinstance(got, list):
            merged.extend(got)
    data = merged
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


def _rss(feeds: List[str] | None = None) -> List[Dict[str, str]]:
    out = []
    for url in (feeds or _rotate()["rss"]):
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
    """Sample across sources, without repeating what this cache already served.

    Stratifying by source (rather than sampling items) stops one loud feed taking the
    whole scroll. The seen-set is what stops the *next* scroll returning the same six
    items: when the cache cannot fill a dose with unseen material it refetches, so a
    scroll that has run dry says so instead of pretending to be new.
    """
    data = cache()
    out: List[str] = []
    for _attempt in range(2):
        items = data.get("items") or []
        seen = set(data.get("seen") or [])
        fresh = [i for i in items if i.get("url") not in seen]
        if len(fresh) < steps and _attempt == 0:
            data = cache(refresh=True)
            continue
        pool = fresh or items
        by_source: Dict[str, List[Dict[str, str]]] = {}
        for item in pool:
            by_source.setdefault(item["source"], []).append(item)
        sources_order = list(by_source)
        RNG.shuffle(sources_order)
        while len(out) < steps and sources_order:
            for name in list(sources_order):
                bucket = by_source[name]
                if not bucket:
                    sources_order.remove(name)
                    continue
                item = bucket.pop(RNG.randrange(len(bucket)))
                out.append(f"{item['source']} · @{item['author']} · {item['text']}")
                seen.add(item.get("url"))
                if len(out) >= steps:
                    break
        data["seen"] = sorted(s for s in seen if s)
        try:
            CACHE.write_text(json.dumps(data))
        except Exception:
            pass
        if out:
            return out
    missing = ", ".join(data.get("failed") or []) or "no network"
    return [f"feed unavailable · {missing}"]
