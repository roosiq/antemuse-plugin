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
from . import recall, storage

#: Resolved through the host's own plugin-storage convention, not a guessed path:
#: `~/.hermes` is only the default home, and profiles move it.
DATA = storage.data_dir()
WALK_CURSOR = DATA / "walk_cursor.json"
FEED_CACHE = DATA / "feed.json"
MEMORY = storage.hermes_home() / "memories/MEMORY.md"
USER = storage.hermes_home() / "memories/USER.md"

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


# ---------------------------------------------------------------------- ready

NEEDS = {"walk": ("wordnet",), "dream": ("framenet_v17", "framenet"), "daydream": None}


def ready(kind: str) -> str | None:
    """Why a state could not run, or None. Cheap: no corpus is loaded.

    A walk whose material cannot be produced is an empty room with a locked
    door; better to refuse the entry and say what is missing.
    """
    import importlib.util

    if importlib.util.find_spec("nltk") is None:
        return ("nltk is not importable in the interpreter Hermes runs. "
                "Install it there, then restart Hermes: "
                "uv pip install --python \"$(python3 -c 'import sys;print(sys.executable)')\" "
                "'nltk>=3.8,<4'")
    corpora = NEEDS.get(kind)
    if not corpora:
        return None
    import nltk

    for corpus in corpora:
        for target in (f"corpora/{corpus}", f"corpora/{corpus}.zip"):
            try:
                nltk.data.find(target)
                return None
            except Exception:
                continue
    return (f"the {corpora[0]} corpus is not installed for nltk. "
            f"Run: python3 -c \"import nltk; nltk.download('{corpora[0]}')\"")


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


#: No "a"/"an" before a slot: FrameNet role names are singular, plural and mass without
#: warning, and an article that disagrees makes the recombination read as a broken template
#: rather than as an invented thing.
DREAM_FORMS_CROSS = [
    "a mechanism built out of {a} and {b}, which works once and then needs a new name",
    "a workshop where {a} is used to build {b}, and the result is against the rules",
    "an object that sits between {a} and {b} and belongs to neither",
    "a place that keeps {a} and {b} in the same room, and forbids them to touch",
    "a machine that charges for the distance between {a} and {b}",
    "a document that records {a} and {b} happening at once, in the order it was told",
]


def _frame_words(frame) -> List[str]:
    """The frame's lexical units as plain words: `abandon.v` -> `abandon`.

    NLTK's Frame object raises KeyError (not AttributeError) for `lexical_units`, so the
    old `getattr(frame, "lexical_units", [])` looked like an empty list and every path that
    needed a lexical unit silently fell back to a placeholder — including the memory seed
    that dream is supposed to start from.
    """
    try:
        units = list((frame.get("lexUnit") or {}).keys())
    except Exception:
        units = []
    return [str(u).rsplit(".", 1)[0].replace("_", " ").lower() for u in units if u]


def _lu_pair(frame) -> List[str]:
    """Two real words from a frame, not its role names.

    Role names ("entity", "time", "circumstance") are structural: recombining them gives a
    sentence about grammar. Lexical units are the words the frame is about — "dying",
    "surrounding", "sawhorse" — and those are what make a recombination read as a thing.
    """
    units = _frame_words(frame)[:40]
    singles = [u for u in units if u and " " not in u]
    if not singles:
        # multi-word units ("have as translation equivalent") read as grammar: take the
        # last word, which is the noun or verb the frame is really about
        singles = [u.split()[-1] for u in units if u]
    units = [u for u in singles if len(u) > 2]
    if not units:
        return ["thing", "thing"]
    RNG.shuffle(units)
    return (units + units)[:2]


def _frame_lus(frame) -> set:
    return {u for u in _frame_words(frame)[:60] if u}


def _far_frame(frames: List[Any], base: Any, samples: int = 64) -> Any:
    """The frame furthest from `base` by lexical-unit overlap — a jump, not a neighbour.

    Two frames that share no lexical units describe worlds that were never asked to
    touch. That is the raw material a recombination needs: the single-frame version could
    only shuffle roles inside one world, which is why its output read as template.
    """
    base_lus = _frame_lus(base)
    pool = RNG.sample(frames, min(samples, len(frames))) if len(frames) > samples else list(frames)
    scored = []
    for cand in pool:
        if cand.name == base.name:
            continue
        lus = _frame_lus(cand)
        overlap = len(base_lus & lus) / max(1, len(base_lus | lus))
        scored.append((overlap, cand))
    if not scored:
        return None
    scored.sort(key=lambda row: row[0])
    return scored[0][1]


def dream_recombine(steps: int = 1) -> List[str]:
    """FrameNet gives the roles; the recombination is the part that never existed."""
    try:
        frames = _frames()
    except Exception as exc:
        return [f"framenet unavailable · {str(exc).splitlines()[0][:90]}"]
    if not frames:
        return ["framenet unavailable · no frames with roles and lexical units"]
    seed_line = ""
    chosen = None
    try:
        from . import seeding
        # Dream starts from memory: a stored or recently spoken word, not a random frame.
        for seed in seeding.candidates("dream", when=time.time()):
            term = seed["term"].lower()
            for candidate in frames:
                words = {w.lower() for w in re.findall(r"[A-Za-z]+", candidate.name)}
                lus = set(_frame_words(candidate)[:40])
                if term in words or term in lus:
                    chosen = candidate
                    seed_line = seeding.marker(seed)
                    break
            if chosen is not None:
                break
    except Exception:
        seed_line = ""
    out = []
    seen_pairs: set = set()
    for _ in range(steps):
        frame = chosen or RNG.choice(frames)
        chosen = None
        other = _far_frame(frames, frame)
        if other is None:
            roles = _roles(frame, 2) + ["thing", "thing"]
            out.append("invented · " + RNG.choice(DREAM_FORMS).format(
                frame=frame.name.replace("_", " ").lower(),
                a=roles[0].replace("_", " ").lower(),
                b=roles[1].replace("_", " ").lower(),
                lu=_lu(frame)))
            continue
        pair = tuple(sorted((frame.name, other.name)))
        if pair in seen_pairs:
            other = RNG.choice([f for f in frames if f.name not in pair] or [other])
            pair = tuple(sorted((frame.name, other.name)))
        seen_pairs.add(pair)
        words_a, words_b = _lu_pair(frame), _lu_pair(other)
        out.append("invented · " + RNG.choice(DREAM_FORMS_CROSS).format(
            frame=frame.name.replace("_", " ").lower(),
            frame_b=other.name.replace("_", " ").lower(),
            a=words_a[0], b=words_b[1],
            lu=words_a[0], lu_b=words_b[1]) + f" · [{frame.name.lower()} × {other.name.lower()}]")
    if out and seed_line:
        out[0] = f"[{seed_line}] " + out[0]
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


def memory_provider() -> str:
    """Which memory backend the host is configured with, if it can be read.

    Hermes memory is provider-pluggable. This module can only read the *built-in*
    provider's files, so with an external provider (hindsight, honcho, mem0) the
    files may be empty or stale — which is a limitation to name, not to hide.
    """
    try:
        from hermes_cli.config import load_config_readonly  # type: ignore
        config = load_config_readonly() or {}
        return str((config.get("memory") or {}).get("provider") or "builtin")
    except Exception:
        return "unknown"


def memory_pool() -> List[str]:
    """Everything this state can honestly call a memory, best source first.

    Recent turns come from the live conversation and are therefore the same under any
    memory provider; the built-in files are enrichment that only exists when the host
    is running the built-in provider.
    """
    # the whole ring, not the last six: a join needs a pool with enough
    # different things in it that two of them can actually share a term
    said = recall.recent(recall.CAP)
    seen = set()
    pool: List[str] = []
    for text in said + memories():
        key = text[:64]
        if key in seen:
            continue
        seen.add(key)
        if len(text) > 24:
            pool.append(text)
    return pool


def memory_pairs(steps: int = 1, join_threshold: int = 2) -> List[str]:
    """Bring two memories back and say whether the connection is worth joining.

    The act is to join *only when the join holds*, so one random pair per item is the
    wrong sampling: with a small pool almost every draw misses, and the state spends its
    dose reporting that nothing joins. Each item therefore looks across the pool for the
    best-supported pair and reports the strongest one it found — saying plainly how many
    pairs it looked at when nothing cleared the bar. The threshold is untouched: this is a
    search for a join that holds, not a lower bar.
    """
    pool = memory_pool()
    if len(pool) < 2:
        provider = memory_provider()
        if recall.recent(1):
            return ["only one thing to remember so far · a join needs two"]
        if provider in ("unknown", "builtin"):
            return ["no memories yet · nothing said in this conversation, and no built-in MEMORY.md"]
        return [f"no memories yet · nothing said in this conversation · memory provider is "
                f"'{provider}', which this state cannot read (built-in MEMORY.md only)"]

    words = {text: _words(text) for text in pool}
    # a shared "state" or "plugin" is not a connection: it is the same project talking.
    # A term counts toward a join only if it is rare *within the pool* — rare enough that
    # two memories carrying it are saying something more than "we are both about this repo".
    df: Dict[str, int] = {}
    for ws in words.values():
        for w in ws:
            df[w] = df.get(w, 0) + 1
    common = max(2, len(pool) // 4)
    distinctive = {w for w, n in df.items() if n <= common}
    words = {text: ws & distinctive for text, ws in words.items()}
    best: List[tuple[int, str, str, set]] = []
    for i, a in enumerate(pool):
        for b in pool[i + 1:]:
            shared = words[a] & words[b]
            best.append((len(shared), a, b, shared))
    best.sort(key=lambda row: row[0], reverse=True)

    out: List[str] = []
    used: set = set()
    for _ in range(steps):
        pick = next((row for row in best if row[1] not in used and row[2] not in used), None)
        if pick is None:
            break
        shared, a, b, common = pick
        used.update((a, b))
        if shared >= join_threshold:
            out.append(f"JOINED · {a[:70]}… ↔ {b[:70]}… · shared: {', '.join(sorted(common)[:4])}")
        else:
            out.append(f"adjacent · {a[:70]}… ↔ {b[:70]}… · only {shared} shared distinct "
                       f"terms (best of {len(best)} pairs, needs {join_threshold})")
    return out


# ---------------------------------------------------------------------- feed

def _strip_xml(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _fetch_feed(url: str, limit: int = 12) -> List[Dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "antemuse/0.9"})
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


# ----------------------------------------------------------------- greenfield

def _git(root: Path) -> Dict[str, Any]:
    import subprocess
    out: Dict[str, Any] = {"commits": None, "first": "", "error": ""}
    try:
        count = subprocess.run(["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                               capture_output=True, text=True, timeout=5)
        if count.returncode != 0:
            err = (count.stderr or "not a repository").strip()
            # an unborn HEAD is the normal state of a brand-new repo, not an error to quote
            if "unknown revision" in err or "ambiguous argument" in err or "does not have any commits" in err:
                out["error"] = "the repository is empty"
            else:
                out["error"] = err.splitlines()[0][:80]
            return out
        out["commits"] = int((count.stdout or "0").strip() or 0)
        first = subprocess.run(["git", "-C", str(root), "log", "--reverse", "--max-count=1",
                                "--format=%s"], capture_output=True, text=True, timeout=5)
        out["first"] = (first.stdout or "").strip()[:120]
    except Exception as exc:
        out["error"] = str(exc).splitlines()[0][:80]
    return out


def _spec_files(root: Path) -> List[str]:
    found: List[str] = []
    for pattern in ("specs/*/spec.md", "specs/*/*/spec.md", ".specify/specs/*/spec.md",
                    "docs/spec.md", "AGENTS.md", "spec.md"):
        try:
            for hit in sorted(root.glob(pattern)):
                rel = str(hit.relative_to(root))
                if rel not in found:
                    found.append(rel)
        except Exception:
            continue
    return found[:8]


def unstuck_text(steps: int = 1) -> List[str]:
    """Directions, one per step, each bound to the evidence that produced it.

    The state's act is to choose a direction, so its material is *directions* — not a
    status report. Every direction carries what it came from and a first move that can be
    started in one turn; a direction with no evidence is a guess with a confident voice
    and is not offered.

    Memory is an input, not decoration: something the person recently said or stored is
    what makes a direction *theirs* rather than a generic suggestion. When no memory is
    readable, that is stated as a missing input instead of being papered over.
    """
    root = storage.project_root()
    if root is None:
        return ["no project root · no .git ancestor above this directory"]

    found: List[tuple[str, str, str]] = []          # direction, evidence, first move
    missing: List[str] = []

    git = _git(root)
    specs = _spec_files(root)
    readme = next((root / n for n in ("README.md", "README.rst", "README.txt")
                   if (root / n).is_file()), None)
    try:
        entries = [c.name for c in root.iterdir() if not c.name.startswith(".")]
    except Exception:
        entries = []

    if git["commits"] is None:
        found.append(("decide what this is before writing code",
                      f"no commits · {git['error'] or 'git said nothing'}",
                      "write one paragraph in README.md: the thing, for whom, and what it refuses"))
    if readme is None:
        found.append(("state the purpose in a README",
                      "no README · nobody has said what this is",
                      "create README.md with four lines: what, for whom, why now, what it is not"))
    if not specs:
        found.append(("write the first spec section",
                      "no spec files yet · the direction is still unchosen",
                      "create specs/changes/<change>/spec.md with the goal and one acceptance check"))
    if len(entries) <= 3:
        found.append(("build the smallest end-to-end slice",
                      f"only {len(entries)} top-level entr{'y' if len(entries) == 1 else 'ies'}",
                      "make one command run from input to output, however small, and run it"))
    if specs and readme and git["commits"]:
        found.append(("pick the next unfinished acceptance check",
                      f"{len(specs)} spec file(s) and {git['commits']} commit(s) already exist",
                      "open the newest spec, find a check with no test, write that test first"))

    # memory as an input: what the person said or stored is the subject matter
    pool = memory_pool()
    if pool:
        term = RNG.choice(pool)
        head = " ".join(term.split())[:60]
        found.append((f"make '{head}' the subject of the first slice",
                      "from memory · something you said or stored",
                      "write one test that uses it, and let the test name the interface"))
    else:
        missing.append("memory (nothing said or stored this session, and no readable MEMORY.md)")

    if not found:
        return ["no direction available · the evidence this state needs is missing: "
                + "; ".join(missing or ["nothing to read"])]

    RNG.shuffle(found)
    want = max(0, int(steps))
    if want == 0:
        return ["unstuck · no direction asked for at this dose"]
    take = found[:want] or found[:1]
    out: List[str] = []
    for i, (direction, evidence, first) in enumerate(take, start=1):
        out.append(f"direction {i} · {direction} · because {evidence} · first: {first}")
    try:
        from . import seeding
        seed = seeding.entry("unstuck", when=time.time())
        out.insert(0, "starts from " + seeding.marker(seed))
    except Exception:
        pass
    if missing:
        out.append("missing input · " + "; ".join(missing))
    return out


PROVIDERS = {
    "walk": walk_text,
    "daydream": memory_pairs,
    "dream": dream_recombine,
    "doomscroll": scroll_text,
    "unstuck": unstuck_text,
}
