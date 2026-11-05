"""Where a state's material comes from.

Everything here reads something real on this machine or on the wire, and says so
when it cannot. No generated filler: if the graph, the memories, or the feed are
missing, the event says which one was missing.
"""
from __future__ import annotations

import json
import random
import re
import sqlite3
import time
import urllib.request
from pathlib import Path
from typing import Dict, List

ONTOLOGY = Path("/home/ryan/world-ontology/var/quickstart.sqlite3")
MEMORY = Path.home() / ".hermes/memories/MEMORY.md"
USER = Path.home() / ".hermes/memories/USER.md"
FEED_CACHE = Path.home() / ".hermes/plugin-data/antemuse-states/feed.json"
LOCAL_CORPUS = Path.home() / ".hermes"

FEEDS = [
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml",
    "https://hnrss.org/frontpage",
]

STOP = set("""a an the and or but if then than that this these those is are was were be been being
of to in on at for with from by as it its it's their there here we you i he she they them
not no yes do does did have has had will would can could should may might must about into
over under more most less very just also so such only own same other some any each""".split())


# --------------------------------------------------------------- concept graph

def concepts() -> List[Dict[str, str]]:
    if not ONTOLOGY.exists():
        return []
    try:
        con = sqlite3.connect(f"file:{ONTOLOGY}?mode=ro", uri=True)
        rows = con.execute(
            "select canonical_label, definition, super_concept_iri, domain_iri, kind from concepts "
            "where status='active' and canonical_label is not null"
        ).fetchall()
        con.close()
    except Exception:
        return []
    return [{"label": r[0], "definition": r[1] or "", "parent": r[2] or "", "domain": r[3] or "",
             "kind": r[4] or ""} for r in rows]


def concept_walk(steps: int = 1) -> List[str]:
    """Walk the graph one concept at a time, naming why the step was taken."""
    pool = concepts()
    if len(pool) < 2:
        return [f"graph unavailable · {ONTOLOGY} has no usable concepts"]
    out = []
    for _ in range(steps):
        a = random.SystemRandom().choice(pool)
        kin = [c for c in pool if c is not a and c["parent"] and c["parent"] == a["parent"]]
        same_domain = [c for c in pool if c is not a and c["domain"] and c["domain"] == a["domain"]]
        both = [c for c in pool if c is not a and c["kind"] == a["kind"]]
        if kin:
            b, why = random.SystemRandom().choice(kin), "same parent class"
        elif same_domain:
            b, why = random.SystemRandom().choice(same_domain), "same domain"
        elif both:
            plural = {"property": "properties", "class": "classes"}.get(a["kind"], a["kind"] + "s")
            b, why = random.SystemRandom().choice(both), f"both are {plural}"
        else:
            b, why = random.SystemRandom().choice([c for c in pool if c is not a]), "no shared parent — a guess"
        gloss = (b["definition"] or "").split(".")[0][:90]
        out.append(f"{a['label']} → {b['label']} · {why}" + (f" · “{gloss}”" if gloss else ""))
    return out


# ------------------------------------------------------------------ memories

def memories() -> List[str]:
    out: List[str] = []
    for path in (MEMORY, USER):
        if not path.exists():
            continue
        for chunk in path.read_text().split("§"):
            text = " ".join(chunk.split())
            if len(text) > 24:
                out.append(text)
    return out


def _words(s: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", s.lower()) if w not in STOP}


def memory_pairs(steps: int = 1, join_threshold: int = 2) -> List[str]:
    """Bring two memories back; say whether the connection is worth joining."""
    pool = memories()
    if len(pool) < 2:
        return ["no memories on disk · looked in MEMORY.md and USER.md"]
    out = []
    for _ in range(steps):
        a, b = random.SystemRandom().sample(pool, 2)
        shared = _words(a) & _words(b)
        if len(shared) >= join_threshold:
            out.append(f"JOINED · {a[:70]}… ↔ {b[:70]}… · shared: {', '.join(sorted(shared)[:4])}")
        else:
            out.append(f"adjacent · {a[:70]}… ↔ {b[:70]}… · only {len(shared)} shared terms")
    return out


def invent(steps: int = 1) -> List[str]:
    """A disparate connection turned into a thing: three concepts, one object."""
    pool = concepts()
    if len(pool) < 3:
        return ["graph unavailable · cannot recombine concepts"]
    out = []
    verbs = ["measure", "carry", "predict", "repair", "hide", "trade", "teach", "sort"]
    for _ in range(steps):
        a, b, c = random.SystemRandom().sample(pool, 3)
        craft = random.SystemRandom().choice(["made of", "grown from", "built out of"])
        out.append(
            f"invented · a {a['label'].lower()} {craft} {b['label'].lower()}, "
            f"used to {random.SystemRandom().choice(verbs)} what a {c['label'].lower()} holds"
        )
    return out


# ---------------------------------------------------------------------- feed

def _strip_xml(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _fetch_feed(url: str, limit: int = 12) -> List[Dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "antemuse-states/0.5"})
    with urllib.request.urlopen(req, timeout=8) as r:
        body = r.read().decode("utf-8", "replace")
    items = []
    for block in re.findall(r"<item[^>]*>(.*?)</item>", body, re.S)[:limit]:
        t = re.search(r"<title[^>]*>(.*?)</title>", block, re.S)
        l = re.search(r"<link[^>]*>(.*?)</link>", block, re.S)
        if t:
            items.append({"title": _strip_xml(t.group(1))[:140], "link": _strip_xml(l.group(1))[:200] if l else "",
                          "source": url.split("/")[2]})
    if not items:
        for block in re.findall(r"<entry[^>]*>(.*?)</entry>", body, re.S)[:limit]:
            t = re.search(r"<title[^>]*>(.*?)</title>", block, re.S)
            if t:
                items.append({"title": _strip_xml(t.group(1))[:140], "link": "", "source": url.split("/")[2]})
    return items


def feed(refresh: bool = False, ttl: int = 1800) -> List[Dict[str, str]]:
    """Real feed items, cached. Never invents a headline."""
    if FEED_CACHE.exists() and not refresh:
        try:
            data = json.loads(FEED_CACHE.read_text())
            if time.time() - data.get("at", 0) < ttl and data.get("items"):
                return data["items"]
        except Exception:
            pass
    items: List[Dict[str, str]] = []
    for url in FEEDS:
        try:
            items += _fetch_feed(url)
        except Exception:
            continue
    if items:
        FEED_CACHE.parent.mkdir(parents=True, exist_ok=True)
        FEED_CACHE.write_text(json.dumps({"at": time.time(), "items": items}))
    return items


def feed_pick(steps: int = 1) -> List[str]:
    items = feed()
    if not items:
        return ["feed unavailable · no network and no cache"]
    out = []
    for item in random.SystemRandom().sample(items, min(steps, len(items))):
        out.append(f"{item['source']} · {item['title']}")
    return out


PROVIDERS = {
    "walk": concept_walk,
    "daydream": memory_pairs,
    "dream": invent,
    "doomscroll": feed_pick,
}
