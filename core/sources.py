"""Where each state gets its material, without model calls or wall-clock endings."""
from __future__ import annotations

import importlib.util
import random
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from . import recall, storage

RNG = random.SystemRandom()
FEEDS = (
    "https://www.theonion.com/rss",
    "https://www.reddit.com/r/BrandNewSentence/.rss",
    "https://hnrss.org/frontpage",
)
STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it",
        "of", "on", "or", "that", "the", "their", "this", "to", "was", "with", "you", "your"}


def ready(kind: str, graph_name: str = "wordnet") -> str | None:
    """Why a provider cannot start, before an active state is recorded."""
    if kind == "daydream" and len(_own_turns()) < 3:
        return "empty · fewer than three recorded turns are available for two pairs"
    if kind == "doomscroll":
        from . import settings
        if not bool(settings._raw("doomscroll_feed", True)):
            return "unavailable · doomscroll feed is disabled by settings"
        if not feed():
            return "unavailable · feed returned no items"
    if kind == "dream" and sum(len(_recent_subjects(root)) for root in projects()) < 3:
        return ("empty · fewer than three commit subjects in the last month across the projects "
                "this chat can see, so there is nothing to recombine")
    if kind == "unstuck":
        root = storage.project_root()
        if root is None:
            return "unavailable · no local project repository is available"
        if not _recent_subjects(root):
            return "empty · local git history is unavailable"
        if not _graph_edge(root):
            return "unavailable · the concept map has no edge to point at yet"
    if kind != "walk" or graph_name != "wordnet":
        return None
    if importlib.util.find_spec("nltk") is None:
        return ("nltk is not importable in the interpreter Hermes runs. "
                "Install it there, then restart Hermes: "
                "uv pip install --python \"$(python3 -c 'import sys;print(sys.executable)')\" "
                "'nltk>=3.8,<4'")
    import nltk
    for target in ("corpora/wordnet", "corpora/wordnet.zip"):
        try:
            nltk.data.find(target)
            return None
        except Exception:
            continue
    return ("the wordnet corpus is not installed for nltk. "
            "Run: python3 -c \"import nltk; nltk.download('wordnet')\"")


def _hop_key(line: str) -> str:
    """The hop a walk line reports: the arrow and the two labels, without the gloss."""
    head = str(line or "").split(" · ")[0]
    head = re.sub(r"^\[seed=[^\]]*\]\s*", "", head)
    head = re.sub(r"\([^)]*\)", "", head)          # the same hop may or may not name its parts
    return " ".join(head.split()).lower()


def walk_text(steps: int = 1) -> List[str]:
    """Run the selected walk; a path is recorded but never injected as material.

    A walk must move. When the graph hands back the hop it just served — a two-node cycle, a stub
    synset that can only go back, a restart that lands where it stood — the walk sets out fresh
    instead of serving the repeat. The engine counts a repeat as drained material, and that is how
    a six-hop walk ended at two claiming "nothing new arrived".
    """
    from . import engine, walks
    active = engine.watch_state().get("active") or {}
    name = str(active.get("walk") or "wander")
    recent = [_hop_key(str(x)) for x in (active.get("shown") or [])][-3:]
    try:
        walk = walks.get(name)
        out = walk.step(steps)
        for _ in range(2):
            if not out or _hop_key(out[0]) not in recent:
                return out
            walk.reset()                      # same hop again: set out from somewhere else
            out = walk.step(steps)
        # Still the same hop with the cursor cleared: the walk is standing somewhere it cannot
        # leave. Say so instead of handing the repeat back — the engine reads a repeat as drained
        # material and closes the walk `dry`, which is a lie about a graph that is merely stuck.
        engine.record("state", f"walk '{name}' could not move · the same hop came back after "
                               f"two fresh starts", event="walk")
        return []
    except Exception as exc:
        try:
            engine.record("state", f"walk '{name}' failed · "
                          f"{type(exc).__name__}: {str(exc).splitlines()[0][:90]}", event="walk")
        except Exception:
            pass
        return []


def _clip(text: str, limit: int = 120) -> str:
    """One readable line; never slice a word in half."""
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    cut = clean[:limit].rsplit(" ", 1)[0].rstrip(" ,;:·-")
    return (cut or clean[:limit].rstrip()) + "…"


def _words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z]{4,}", text.lower()) if word not in STOP}


def _own_turns() -> List[str]:
    """Only the person's recorded local conversation turns, never a memory backend."""
    seen, out = set(), []
    for raw in recall.recent(recall.CAP, who="person"):
        text = _clip(raw, 160)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def memory_pairs(steps: int = 1, skip: set[str] | None = None, keyed: bool = False) -> List[Any]:
    """Two recorded turns, what they touch, and one possibility."""
    pool = _own_turns()
    if len(pool) < 2:
        return ["daydream empty · fewer than two recorded turns are available"]
    skip = skip or set()
    choices = []
    for left in range(len(pool)):
        for right in range(left + 1, len(pool)):
            a, b = pool[left], pool[right]
            ident = f"{left}:{right}"
            if ident in skip:
                continue
            shared = sorted(_words(a) & _words(b))
            touch = ", ".join(shared[:3]) if shared else "the gap between them"
            line = (f"JOINED · memory one: {_clip(a, 96)} · memory two: {_clip(b, 96)} "
                    f"· touch: {touch} · possibility: try treating {touch} as the subject")
            choices.append((ident, line))
    if not choices:
        return ["daydream empty · no unused pair remains"]
    selected = choices[:max(1, int(steps))]
    return selected if keyed else [line for _, line in selected]


def projects() -> List[Path]:
    """The current local repository only: no transcript or remote history reads."""
    root = storage.project_root()
    return [root] if root is not None else []


# Today first, then wider. A person who has not committed today still has work worth dreaming
# over; refusing at the door because the last 24 hours were quiet turned a novelty into a dud.
_SUBJECT_WINDOWS = ("24 hours ago", "7 days ago", "30 days ago")


def _git_subjects(root: Path, since: str = "24 hours ago") -> List[str]:
    try:
        run = subprocess.run(["git", "-C", str(root), "log", "--since", since, "--pretty=%s"],
                             capture_output=True, text=True, timeout=8)
    except Exception:
        return []
    if run.returncode:
        return []
    return [_clip(line, 100) for line in run.stdout.splitlines() if line.strip()]


def _recent_subjects(root: Path, want: int = 3) -> List[str]:
    """The last ``want`` commit subjects: today if there are enough, otherwise further back."""
    widened: List[str] = []
    for window in _SUBJECT_WINDOWS:
        subjects = _git_subjects(root, window)
        widened = subjects
        if len(subjects) >= want:
            return subjects
    return widened


def day_connections(steps: int = 1, skip: set[str] | None = None, keyed: bool = False) -> List[Any]:
    """Recombine only local git commit subjects, never changed files or transcripts."""
    subjects = [(root.name, subject) for root in projects() for subject in _recent_subjects(root)]
    if len(subjects) < 2:
        return ["dream empty · fewer than two local git commit subjects are available"]
    skip = skip or set()
    choices = []
    for left in range(len(subjects)):
        for right in range(left + 1, len(subjects)):
            project_a, a = subjects[left]
            project_b, b = subjects[right]
            ident = f"{project_a}:{left}|{project_b}:{right}"
            if ident in skip:
                continue
            shared = sorted(_words(a) & _words(b))
            bridge = ", ".join(shared[:3]) if shared else "the same unfinished shape"
            choices.append((ident, f"connection · {project_a}: {a} ↔ {project_b}: {b} · shared: {bridge}"))
    if not choices:
        return ["dream empty · no unused recombination remains"]
    selected = choices[:max(1, int(steps))]
    return selected if keyed else [line for _, line in selected]


def _strip_xml(text: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", "", text or "").split())


def _fetch_feed(url: str, limit: int = 12) -> List[Dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": "antemuse/0.11"})
    with urllib.request.urlopen(request, timeout=8) as response:
        body = response.read().decode("utf-8", "replace")
    source = url.split("/")[2]
    titles = [_strip_xml(t) for t in re.findall(r"<title[^>]*>(.*?)</title>", body, re.S)]
    out = []
    for title in titles:
        if not title or len(title) < 12:
            continue  # a channel name ("The Onion") is not an item
        if title.lower() == source.lower() or title.lower().startswith(source.lower()):
            continue
        out.append({"source": source, "title": _clip(title, 120)})
    return out[:limit]


def feed() -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for url in FEEDS:
        try:
            items.extend(_fetch_feed(url))
        except Exception:
            continue
    return items


def scroll_text(steps: int = 1, skip: set[str] | None = None, keyed: bool = False) -> List[Any]:
    """One-line feed items. The engine treats these as untrusted and never persists them."""
    from . import settings
    if not bool(settings._raw("doomscroll_feed", True)):
        return ["doomscroll unavailable · doomscroll feed is disabled by settings"]
    items = feed()
    if not items:
        return ["doomscroll unavailable · feed returned no items"]
    skip = skip or set()
    out = []
    for item in items:
        text = f"{item['source']} · {_clip(item['title'], 120)}"
        ident = f"{item['source']}:{item['title']}"
        if ident not in skip:
            out.append((ident, text))
        if len(out) >= max(1, int(steps)):
            break
    if not out:
        return ["doomscroll empty · no unused feed item remains"]
    return out if keyed else [line for _, line in out]


def _graph_edge(root: Path) -> str:
    """One edge from the active graph provider, over concepts this person actually has.

    The first version read the *folder name* — `antemuse-plugin` -> "antemuse", "plugin" — which
    resolves to nothing in WordNet, so `unstuck` was advertised and unreachable in every real
    home. The material that does exist is the concept ledger: what the agent has already been
    working on. Folder terms stay as a last resort.
    """
    from . import walks
    try:
        graph = walks.make_graph("wordnet")
        terms: List[str] = []
        try:
            from . import history

            conn = history._connect()
            if conn is not None:
                try:
                    terms = [str(row[0]) for row in conn.execute(
                        "SELECT label FROM concepts ORDER BY times DESC, last_seen DESC LIMIT 24"
                    )]
                finally:
                    conn.close()
        except Exception:
            terms = []
        terms += [part.lower() for part in re.findall(r"[A-Za-z]{4,}", root.name)] or ["project"]
        for term in terms:
            node = graph.resolve(term)
            if node is None:
                continue
            edges = graph.edges(node)
            if edges:
                relation, neighbour = edges[0]
                return f"{node['label']} → {neighbour['label']} ({relation})"
    except Exception:
        return ""
    return ""


def unstuck_text(steps: int = 1, skip: set[str] | None = None, keyed: bool = False) -> List[Any]:
    """One direction grounded in recent history plus one graph edge."""
    root = storage.project_root()
    if root is None:
        return ["unstuck unavailable · no local project repository is available"]
    subjects = _recent_subjects(root)
    edge = _graph_edge(root)
    if not subjects or not edge:
        missing = "history" if not subjects else "graph edge"
        return [f"unstuck empty · {missing} is unavailable"]
    ident = f"{subjects[0]}|{edge}"
    if ident in (skip or set()):
        return ["unstuck empty · no unused direction remains"]
    line = (f"direction · continue the last change: {subjects[0]} · graph edge: {edge} "
            f"· first: write the smallest test for that next change")
    result = [(ident, line)]
    return result if keyed else [line]


PROVIDERS = {
    "walk": walk_text,
    "daydream": memory_pairs,
    "doomscroll": scroll_text,
    "dream": day_connections,
    "unstuck": unstuck_text,
}
