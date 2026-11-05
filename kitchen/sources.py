"""Where a state's material comes from.

WordNet is the concept graph: 117k synsets joined by hypernym, hyponym, part,
domain and antonym links, so a step can say *why* it was taken and where the
last step ended. FrameNet is the scene grammar: 1,221 frames of roles and
lexical units, recombined during sleep. Memories and live feeds fill the rest.

Everything fails loudly: a missing corpus says so rather than inventing content.
"""
from __future__ import annotations

import json
import os
import random
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

HOME = Path.home()
NLTK_HOME = HOME / "nltk_data"
DATA = HOME / ".hermes/plugin-data/antemuse-states"
WALK_CURSOR = DATA / "walk_cursor.json"
FEED_CACHE = DATA / "feed.json"
MEMORY = HOME / ".hermes/memories/MEMORY.md"
USER = HOME / ".hermes/memories/USER.md"

if NLTK_HOME.is_dir():
    os.environ.setdefault("NLTK_DATA", str(NLTK_HOME))

FEEDS = [
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml",
    "https://hnrss.org/frontpage",
]

STOP = set("""a an the and or but if then than that this these those is are was were be been being
of to in on at for with from by as it its it's their there here we you i he she they them
not no yes do does did have has had will would can could should may might must about into
over under more most less very just also so such only own same other some any each""".split())

RNG = random.SystemRandom()

SEEDS = ["walk", "dream", "light", "river", "memory", "door", "signal", "salt", "night", "hand"]


# ------------------------------------------------------------------- wordnet

def _wn():
    from nltk.corpus import wordnet as wn  # imported late: 117k synsets, slow to load
    return wn


def _lemma(syn) -> str:
    return syn.lemma_names()[0].replace("_", " ")


def _pos(syn) -> str:
    return {"n": "noun", "v": "verb", "a": "adj", "s": "adj", "r": "adv"}.get(syn.pos(), syn.pos())


def _cursor_data() -> dict:
    try:
        data = json.loads(WALK_CURSOR.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def cursor() -> str:
    value = _cursor_data().get("synset") or ""
    return value if isinstance(value, str) else ""


def _save_cursor(name: str, prev: str = "") -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    WALK_CURSOR.write_text(json.dumps({"synset": name, "prev": prev, "at": time.time()}))


def _edges(syn) -> List[tuple]:
    """Every relation WordNet exposes for this synset, with the verb for the step."""
    out = []
    probes = [
        ("hypernym", lambda s: s.hypernyms(), "went up to its"),
        ("hyponym", lambda s: s.hyponyms(), "went down into a"),
        ("holonym", lambda s: s.part_holonyms() + s.member_holonyms() + s.substance_holonyms(), "stepped into the"),
        ("meronym", lambda s: s.part_meronyms() + s.member_meronyms() + s.substance_meronyms(), "opened up its"),
        ("similar", lambda s: getattr(s, "similar_tos", lambda: [])(), "bent toward its"),
        ("also", lambda s: s.also_sees(), "ran alongside its"),
        ("antonym", lambda s: [a.synset() for l in s.lemmas() for a in l.antonyms()], "turned against its"),
    ]
    for name, fn, verb in probes:
        try:
            targets = [t for t in fn(syn) if t is not None]
        except Exception:
            targets = []
        if targets:
            out.append((name, targets, verb))
    return out


def walk_step(steps: int = 1) -> List[str]:
    """One step along a real WordNet edge, starting from where the last step ended."""
    try:
        wn = _wn()
        first = wn.synsets(RNG.choice(SEEDS))[0]
    except Exception as exc:
        return [f"wordnet unavailable · {str(exc).splitlines()[0][:90]}"]
    out: List[str] = []
    seed = cursor()
    try:
        syn = wn.synset(seed) if seed else first
    except Exception:
        syn = first
    for _ in range(steps):
        options = _edges(syn)
        if not options:
            out.append(f"{_lemma(syn)} · no edge out of this synset — the walk stops here")
            break
        name, targets, verb = RNG.choice(options)
        back = _cursor_data().get("prev")
        forward = [t for t in targets if t.name() != back]
        nxt = RNG.choice(forward or targets)
        gloss = (nxt.definition() or "").split(";")[0][:90]
        out.append(
            f"{_lemma(syn)} ({_pos(syn)}) → {_lemma(nxt)} ({_pos(nxt)}) · {verb} {name}"
            + (f" · “{gloss}”" if gloss else "")
        )
        prev_name, syn = syn.name(), nxt
    _save_cursor(syn.name(), prev_name)
    return out


# ------------------------------------------------------------------ framenet

_FRAMES: List[Any] = []


def _frames() -> List[Any]:
    global _FRAMES
    if _FRAMES:
        return _FRAMES
    from nltk.corpus import framenet as fn
    _FRAMES = [f for f in fn.frames() if len(f.FE) >= 3 and f.lexUnit]
    return _FRAMES


def _lu(frame) -> str:
    lu = RNG.choice(list(frame.lexUnit.values()))
    return str(getattr(lu, "name", "thing")).split(".")[0].replace("_", " ")


def _roles(frame, n: int = 3) -> List[str]:
    names = [fe.name for fe in frame.FE.values() if fe.name != "Lexical_unit"]
    return RNG.sample(names, min(n, len(names))) if names else ["thing"]


DREAM_FORMS = [
    "a {frame} in which the {a} is really the {b}",
    "the {a} of {frame}, kept after the {b} is gone",
    "something that {lu}s, but only where the {a} and the {b} trade places",
    "a {frame} missing its {a}, so every {b} has to stand in for it",
    "an object that holds the {a} of {frame} the way a jar holds weather",
    "a {b} that has been given the {a}'s work in {frame} and does it badly, on purpose",
]


def dream_recombine(steps: int = 1) -> List[str]:
    """FrameNet gives the roles; the recombination is the part that never existed."""
    try:
        frames = _frames()
    except Exception as exc:
        return [f"framenet unavailable · {str(exc).splitlines()[0][:90]}"]
    if not frames:
        return ["framenet unavailable · no frames with roles and lexical units"]
    out = []
    for _ in range(steps):
        frame = RNG.choice(frames)
        roles = _roles(frame, 2) + ["thing", "thing"]
        out.append("invented · " + RNG.choice(DREAM_FORMS).format(
            frame=frame.name.replace("_", " ").lower(),
            a=roles[0].replace("_", " ").lower(),
            b=roles[1].replace("_", " ").lower(),
            lu=_lu(frame)))
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
        a, b = RNG.sample(pool, 2)
        shared = _words(a) & _words(b)
        if len(shared) >= join_threshold:
            out.append(f"JOINED · {a[:70]}… ↔ {b[:70]}… · shared: {', '.join(sorted(shared)[:4])}")
        else:
            out.append(f"adjacent · {a[:70]}… ↔ {b[:70]}… · only {len(shared)} shared terms")
    return out


# ---------------------------------------------------------------------- feed

def _strip_xml(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _fetch_feed(url: str, limit: int = 12) -> List[Dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "antemuse-states/0.6"})
    with urllib.request.urlopen(req, timeout=8) as r:
        body = r.read().decode("utf-8", "replace")
    items = []
    for block in re.findall(r"<item[^>]*>(.*?)</item>", body, re.S)[:limit]:
        t = re.search(r"<title[^>]*>(.*?)</title>", block, re.S)
        l = re.search(r"<link[^>]*>(.*?)</link>", block, re.S)
        if t:
            items.append({"title": _strip_xml(t.group(1))[:140],
                          "link": _strip_xml(l.group(1))[:200] if l else "",
                          "source": url.split("/")[2]})
    if not items:
        for block in re.findall(r"<entry[^>]*>(.*?)</entry>", body, re.S)[:limit]:
            t = re.search(r"<title[^>]*>(.*?)</title>", block, re.S)
            if t:
                items.append({"title": _strip_xml(t.group(1))[:140], "link": "",
                              "source": url.split("/")[2]})
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
    for item in RNG.sample(items, min(steps, len(items))):
        out.append(f"{item['source']} · {item['title']}")
    return out


# ------------------------------------------------------- walks and scrolling

def walk_text(steps: int = 1) -> List[str]:
    """Run the walk the active state selected, not a hard-coded one."""
    from . import engine, walks
    state = engine.watch_state() or {}
    name = ((state.get("active") or {}).get("walk") or "wander")
    walk = walks.get(name)
    try:
        return walk.step(steps)
    except Exception as exc:
        return [f"walk '{name}' failed · {str(exc).splitlines()[0][:90]}"]


def scroll_text(steps: int = 1) -> List[str]:
    from . import social
    return social.pick(steps)


PROVIDERS = {
    "walk": walk_text,
    "daydream": memory_pairs,
    "dream": dream_recombine,
    "doomscroll": scroll_text,
}
