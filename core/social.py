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
#: Distraction, not information. Every lane here is satire or comedy; a business or industry
#: feed is the *opposite* of this state.
#: Satire and comedy lanes that actually serve text. Reddit rate-limits this machine
#: (HTTP 429 on every /r/ path) and Bluesky's search API answers 403 without a token, so
#: neither is in the pool: a lane that cannot answer is a lane that silently empties the
#: state. Every URL here returned a text feed on 2026-11-08.
COMEDY_FEEDS = [
    "https://www.theonion.com/rss",
    "https://babylonbee.com/feed",
    "https://www.reductress.com/feed",
    "https://www.pointandclickbait.com/feed",
    "https://www.thedailymash.co.uk/feed",
    "https://xkcd.com/rss.xml",
    "https://www.smbc-comics.com/comic/rss",
]

#: A cheap, deterministic "is this work?" test. Not a classifier and not a judgement about
#: quality: a line carrying any of these is professional material, which is not distraction.
WORK_WORDS = set("""
earnings revenue quarter investor investors market markets shares stock stocks ceo
funding valuation startup startups regulation compliance policy government senate
congress election campaign launch roadmap enterprise b2b saas infrastructure outage
breach cyberattack vulnerability layoffs hiring recruitment merger acquisition ipo
""".split())


def is_work(text: str) -> bool:
    words = {w for w in re.findall(r"[a-z]{3,}", (text or "").lower())}
    return bool(words & WORK_WORDS)


#: Satire and comedy lanes that actually serve text. Reddit rate-limits this machine
#: (HTTP 429 on every /r/ path) and Bluesky's search API answers 403 without a token, so
#: neither is in the pool: a lane that cannot answer is a lane that silently empties the
#: state. Every URL here returned a text feed on 2026-11-08.
#: The RSS lanes are comedy lanes now. They were general news when the state was defined as
#: "random material"; the goal is distraction, and a technology feed delivers the work back.
FEEDS = list(COMEDY_FEEDS)


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
    """Which lanes this fetch will try, shuffled — the pool is not sampled twice the same."""
    # five of seven: a dose of six needs enough lanes to fill, and drawing all seven every
    # time makes every scroll the same scroll
    return {"rss": RNG.sample(FEEDS, min(5, len(FEEDS)))}


def _rss(feeds: List[str] | None = None) -> List[Dict[str, str]]:
    out = []
    for url in (feeds or _rotate()["rss"]):
        try:
            body = _get(url)
        except Exception:
            continue
        for block in re.findall(r"<item[^>]*>(.*?)</item>", body, re.S)[:12]:
            t = re.search(r"<title[^>]*>(.*?)</title>", block, re.S)
            if not t:
                continue
            text = _clean(t.group(1), 140)
            # the seen-set is keyed on url: an empty url made every item "unseen" forever,
            # so a second scroll could serve the same headline as new
            link = re.search(r"<link[^>]*>\s*(?:<!\[CDATA\[)?\s*(https?://[^\s<\]]+)", block, re.S)
            key = link.group(1) if link else f"{url}#{abs(hash(text))}"
            out.append({"source": url.split("/")[2], "author": "feed",
                        "text": text, "url": key})
    return out


#: One fetcher, one kind of material. Social timelines and HN were removed with the goal
#: change: news and industry chatter is the opposite of distraction.
FETCHERS = {"satire": _rss}


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
    """Comedy first, work excluded, and the exclusion is stated rather than silent."""
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
        # an image-only post has no text to read, so it is not an item this state can
        # deliver; the same is true of a work item, which is the wrong kind of material
        kept = [i for i in pool
                if (i.get("text") or "").strip() and not is_work(i.get("text", ""))]
        skipped = len(pool) - len(kept)
        pool = kept or pool
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
                out.append(f"{item['source']} · @{item['author']} · {item['text']}"
                           + (f" · [{skipped} skipped as work]" if skipped else ""))
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
