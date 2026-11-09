"""Turn a session's material and output into the preregistered primary outcome.

Deterministic only: no model, no judgement, no fuzzy matching beyond case folding and
word-boundary regexes. If an outcome needs an opinion it is not a primary outcome.

    carry(text, material)          walk      — a delivered concept appears in the work
    landing(text, material)        daydream  — a delivered pair co-occurs
    adoption(text, material)       doomscroll— a delivered url/domain is used
    kept(session, material)        dream     — a recombination is kept or lands in a doc
    adopted(directions, text)      unstuck   — a spec names the recommended direction

Each returns True/False; the caller decides the window. Exported helpers are the only
thing the runner and the report share, so the definition exists in one place.
"""
from __future__ import annotations

import re
from typing import Iterable, List

STOP = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "at", "for", "with", "by",
    "is", "are", "was", "were", "be", "been", "it", "its", "this", "that", "these",
    "those", "from", "as", "not", "no", "you", "your", "we", "our", "they", "their",
    "step", "state", "walk", "dream", "note", "kept", "seed",
}

WORD = re.compile(r"[A-Za-z][A-Za-z\-]{3,}")
BRACKET = re.compile(r"\[[^\]]*\]")
ARROWS = re.compile(r"→|->|·|\|")

#: words that are structure rather than subject matter, so they never count as carry
GENERIC = {"system", "list", "thing", "work", "code", "file", "test", "step", "item",
           "line", "note", "page", "some", "most", "other", "such", "then", "than"}
URL = re.compile(r"https?://[^\s)>\]]+")


def _words(text: str) -> List[str]:
    return [w.lower() for w in WORD.findall(text or "") if w.lower() not in STOP]


def seeds(material: Iterable[str]) -> List[str]:
    """The concepts a state actually delivered, one per arrow-headed segment.

    A walk line reads `list system→Japanese lilac [far] → …`: the bracketed part is the
    citation and the segment either side of an arrow is a concept. Reading it that way
    beats taking the longest word of the line (which once made "japanese" the subject of a
    line about a lilac) and beats taking every word (which lets "system" count as carry).
    """
    out: List[str] = []
    for line in material:
        clean = BRACKET.sub(" ", line or "")
        for segment in ARROWS.split(clean):
            words = [w for w in _words(segment) if w not in GENERIC]
            if words:
                # the head of an English noun phrase is its last word: "Japanese lilac"
                # is a lilac, and taking the longest word made the adjective the subject
                out.append(words[-1])
    return out


def carry(text: str, material: Iterable[str]) -> bool:
    """walk: the delivered concept shows up in the work that follows."""
    body = (text or "").lower()
    for term in seeds(material):
        if re.search(rf"\b{re.escape(term)}\b", body):
            return True
    return False


def landing(text: str, material: Iterable[str]) -> bool:
    """daydream: both halves of a delivered pair appear in the same later turn."""
    body = (text or "").lower()
    for line in material:
        words = sorted(set(_words(line)), key=len, reverse=True)[:2]
        if len(words) == 2 and all(re.search(rf"\b{re.escape(w)}\b", body) for w in words):
            return True
    return False


def adoption(text: str, material: Iterable[str]) -> bool:
    """doomscroll: a delivered url or its host is fetched, cited, or named."""
    body = text or ""
    for line in material:
        for url in URL.findall(line):
            host = re.sub(r"^https?://", "", url).split("/")[0]
            if url in body or host in body:
                return True
    return False


def kept(material: Iterable[str], kept_handles: Iterable[str], later_text: str) -> bool:
    """dream: a delivered recombination was kept, or its compound reached a document."""
    handles = {str(h) for h in kept_handles or []}
    if handles:
        return True
    return carry(later_text, material)


def adopted(direction: str, spec_text: str) -> bool:
    """unstuck: the recommended direction became the subject of a written spec."""
    words = sorted(set(_words(direction)), key=len, reverse=True)[:2]
    if not words:
        return False
    body = (spec_text or "").lower()
    return any(re.search(rf"\b{re.escape(w)}\b", body) for w in words)


PRIMARY = {
    "walk": lambda text, material, extra: carry(text, material),
    "daydream": lambda text, material, extra: landing(text, material),
    "doomscroll": lambda text, material, extra: adoption(text, material),
    "dream": lambda text, material, extra: kept(material, extra.get("kept") or [],
                                                extra.get("later_text") or ""),
    "unstuck": lambda text, material, extra: adopted(extra.get("direction") or "", text),
}


def compute(state: str, text: str, material: Iterable[str], extra: dict | None = None) -> bool:
    fn = PRIMARY.get(state)
    if fn is None:
        raise SystemExit(f"no primary outcome for state {state!r}")
    return bool(fn(text, list(material), extra or {}))
