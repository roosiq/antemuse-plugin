"""Where a state starts, and how it stays from starting the same way twice.

The spec (`specs/changes/state-entry`) fixes the mix: 50 % terms from the working
project, 30 % from the conversation, 20 % deliberately random — drawn by a deterministic
hash of (state, entry time, entry counter) so a replayed entry picks the same source.
Determinism is the point: a live RNG makes a walk unreproducible and its diversity
unmeasurable.

Nothing here calls a model, reaches the network, or invents a term.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from . import recall, storage

#: project : conversation : random, as buckets out of ten — the default.
MIX = (5, 3, 2)

#: A state may declare its own mix. `dream` starts from memory: it is the state whose
#: whole premise is recombining what is already known, so a random frame is the wrong door.
MIXES = {
    "dream": (("memory", 6), ("project", 2), ("random", 2)),
    # at a trailhead the project is the only thing there is; the random share exists so
    # two trailheads in similar repositories do not start from the same word
    "trailhead": (("project", 8), ("random", 2)),
}

STOP = set("""
a about above after again against all also and any are because been before being below
between both but can could did does doing down during each few for from further had has
have having here how into its itself just more most not now off once only other our out
over own same should so some such than that the their them then there these they this
those through too under until very was we were what when where which while who whom why
will with would you your
""".split())

WORD = re.compile(r"[A-Za-z][A-Za-z-]{3,}")

#: Branch names and file trees contribute structure, not vocabulary. A seed of "main"
#: resolves to a synset and produces material about the sea.
GENERIC = set("""
main master develop development staging release trunk repo src source test tests docs doc
lib app apps build dist node_modules readme agents licence license changelog
""".split())


def _words(text: str) -> List[str]:
    return [w.lower() for w in WORD.findall(text or "") if w.lower() not in STOP]


def _head() -> Path:
    root = storage.project_root()
    if root is None:
        return Path()
    head = root / ".git" / "HEAD"
    try:
        text = head.read_text().strip()
    except Exception:
        return root
    return root


def project_terms(goal: str = "", limit: int = 24) -> List[str]:
    """Deterministic vocabulary of the repository being worked in."""
    root = storage.project_root()
    if root is None:
        return []
    terms: List[str] = []
    # repository name first (it names the thing), branch last (it names the process)
    terms += _words(root.name.replace("_", " ").replace("-", " "))
    branch = ""
    try:
        ref = (root / ".git" / "HEAD").read_text().strip()
        branch = ref.split("refs/heads/", 1)[-1]
    except Exception:
        pass
    for readme in ("README.md", "README.rst", "AGENTS.md"):
        path = root / readme
        if path.is_file():
            try:
                terms += _words(path.read_text(errors="ignore")[:4000])
            except Exception:
                pass
    try:
        for child in sorted(root.iterdir())[:40]:
            if child.is_dir() and not child.name.startswith("."):
                terms += _words(child.name.replace("_", " "))
    except Exception:
        pass
    terms += _words(branch)
    terms += _words(goal)
    out: List[str] = []
    for term in terms:
        if term in GENERIC:
            continue
        if term not in out:
            out.append(term)
        if len(out) >= limit:
            break
    return out


def memory_terms(limit: int = 16) -> List[str]:
    """Words from what the person has actually said or stored — memory first.

    Uses the same pool daydream draws from (recent turns, then the built-in memory
    files), so a dream starts from something that happened rather than a random frame.
    """
    try:
        from . import sources  # lazy: sources imports this module inside its own calls
        pool = sources.memory_pool()
    except Exception:
        pool = list(recall.recent(8))
    seen: List[str] = []
    for line in pool:
        for word in _words(line):
            if word not in seen:
                seen.append(word)
            if len(seen) >= limit:
                return seen
    return seen


def conversation_terms(limit: int = 16) -> List[str]:
    seen: List[str] = []
    for line in recall.recent(8):
        for word in _words(line):
            if word not in seen:
                seen.append(word)
            if len(seen) >= limit:
                return seen
    return seen


def random_term() -> str:
    """One WordNet lemma, unrelated to the project on purpose."""
    try:
        import random

        from nltk.corpus import wordnet as wn  # late import: 117k synsets
        names = list(wn.all_lemma_names())
        if not names:
            return ""
        synsets = wn.synsets(random.choice(names))
        return synsets[0].lemma_names()[0].replace("_", " ") if synsets else ""
    except Exception:
        return ""


def _bucket(state: str, when: float, counter: int) -> int:
    digest = hashlib.sha256(f"{state}|{int(when)}|{counter}".encode()).hexdigest()
    return int(digest[:8], 16) % 10


def _weights(state: str):
    return MIXES.get(state) or (("project", MIX[0]), ("conversation", MIX[1]), ("random", MIX[2]))


def _tier(state: str, when: float, counter: int) -> str:
    bucket = _bucket(state, when, counter)
    edge = 0
    for source, weight in _weights(state):
        edge += weight
        if bucket < edge:
            return source
    return _weights(state)[-1][0]


def _order(state: str) -> List[str]:
    """The declaration order, then everything else, so a fallback is still stated."""
    declared = [source for source, _ in _weights(state)]
    rest = [s for s in ("memory", "conversation", "project", "random") if s not in declared]
    return declared + rest


def _pool(source: str, goal: str, limit: int) -> List[str]:
    if source == "memory":
        return memory_terms(limit)
    if source == "project":
        return project_terms(goal, limit)
    if source == "conversation":
        return conversation_terms(limit)
    return [random_term()]


def entry(state: str, *, when: float, counter: int = 0, exclude: Sequence[str] = (),
          goal: str = "") -> Dict[str, str]:
    """The seed this entry starts from: `{source, term}`.

    Falls forward, never sideways: if the chosen tier has nothing usable (no repository,
    or a term already used), the next tier answers — and the source says which one did,
    so the fallback is visible rather than silent.
    """
    tier = _tier(state, when, counter)
    order = [tier] + [s for s in _order(state) if s != tier]
    used = {t.lower() for t in exclude}
    for source in order:
        pool: Iterable[str] = _pool(source, goal, 48)
        for term in pool:
            if term and term.lower() not in used:
                return {"source": source, "term": term}
    return {"source": "none", "term": ""}


def candidates(state: str, *, when: float, counter: int = 0, exclude: Sequence[str] = (),
               goal: str = "", limit: int = 12) -> List[Dict[str, str]]:
    """The tier's terms in order, so a caller can try each against its own vocabulary.

    A repository word like "antemuse" is not in WordNet; the honest answer is the next
    candidate from the same tier, not a silent jump to a random synset.
    """
    tier = _tier(state, when, counter)
    order = [tier] + [s for s in _order(state) if s != tier]
    used = {t.lower() for t in exclude}
    out: List[Dict[str, str]] = []
    for source in order:
        pool: Iterable[str] = _pool(source, goal, limit * 4)
        for term in pool:
            if not term or term.lower() in used:
                continue
            used.add(term.lower())
            out.append({"source": source, "term": term})
            if len(out) >= limit:
                return out
    return out


def marker(seed: Dict[str, str]) -> str:
    """The audit trail: what the entry started from, where a reviewer can see it."""
    source, term = seed.get("source") or "none", seed.get("term") or ""
    return f"seed={source}:{term}" if term else "seed=none"
