"""Deterministic judge for Concept Kitchen.

No model calls, no randomness: the same submission always scores the same way.
Four 25-point axes, a published penalty list, and a distance label derived from
token overlap. The rules are deliberately shallow — they reward naming the
thing you changed, explaining the transfer, and committing to a next action,
because those are the three failures of ordinary idea lists.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence, Tuple

WORD_RE = re.compile(r"[a-z0-9']+")

STOP = {
    "the", "and", "for", "that", "with", "this", "from", "into", "your", "you",
    "our", "their", "its", "it's", "are", "was", "were", "been", "being", "have",
    "has", "had", "will", "would", "can", "could", "should", "may", "might",
    "must", "not", "but", "than", "then", "there", "here", "what", "which",
    "who", "whom", "whose", "when", "where", "why", "how", "all", "any", "each",
    "every", "some", "more", "most", "less", "very", "just", "only", "also",
    "about", "over", "under", "between", "through", "after", "before", "while",
    "one", "two", "three", "like", "make", "makes", "made", "use", "using",
    "used", "get", "gets", "got", "set", "sets", "way", "thing", "things",
    "idea", "ideas", "people", "person", "someone", "something", "instead",
}

SLOP = {
    "synergy", "synergies", "leverage", "holistic", "seamless", "robust",
    "elevate", "unlock", "empower", "ecosystem", "journey", "game-changer",
    "revolutionize", "paradigm", "cutting-edge", "transformative",
    "best-in-class", "next-generation", "disrupt", "innovative", "frictionless",
    "turnkey", "world-class", "streamline",
}

IMPERATIVES = {
    "write", "ask", "call", "sketch", "time", "draw", "measure", "build",
    "test", "cut", "send", "name", "pick", "set", "run", "record", "list",
    "count", "walk", "watch", "offer", "trade", "print", "film", "cook",
    "interview", "sketch", "draft", "post", "delete", "remove", "split",
    "merge", "raise", "lower", "cap", "invite", "pay", "charge", "borrow",
    "rent", "lend", "teach", "host", "stage", "rehearse", "read", "compare",
    "choose", "stop", "start", "give", "take", "put", "leave", "open", "close",
    "book", "email", "phone", "log", "map", "budget", "schedule", "plan", "hire",
    "publish", "ship", "share", "label", "tag", "sort", "photograph", "prototype",
    "mock", "transcribe", "annotate", "rate", "rank", "sample", "survey",
    "add", "attach", "replace", "swap", "note", "check", "verify", "rewrite",
    "reword", "trim", "rename", "fold", "collect", "film", "sketch",
    "narrow", "widen", "shorten", "lengthen", "delay", "schedule",
}

BOUNDS = {
    "one", "two", "three", "four", "five", "single", "half", "double", "by",
    "within", "under", "before", "after", "next", "today", "tomorrow",
    "week", "month", "year", "hour", "minute", "days", "weeks", "months",
}

CONNECTORS = (
    "because", "so that", "which lets", "which means", "that way", "by turning",
    "so it", "therefore", "lets you", "allows", "borrowed from", "the way",
)

CONTRAST = (
    "instead of", "rather than", "normally", "usually", "default", "assumes",
    "expects", "standard", "convention", "taken for granted", "as if",
    "everyone", "the assumption",
)

FLIP_DIMS: Dict[str, Tuple[str, ...]] = {
    "assumption": ("assum", "premise", "premise", "take for granted", "default", "supposed", "expected", "normally"),
    "role": ("role", "who owns", "who does", "who runs", "the person", "operator", "becomes the", "swaps places"),
    "property": ("property", "attribute", "material", "quality", "texture", "colour", "color", "surface", "weight"),
    "sequence": ("sequence", "order", "step", "before", "after", "first", "last", "then", "backwards", "reverse the order"),
    "success": ("success", "done", "finished", "win", "counts as", "measure of", "goal", "score"),
    "resource": ("resource", "budget", "cost", "money", "staff", "energy", "supplies", "compute", "time budget"),
}

SHIFT_DIMS: Dict[str, Tuple[str, ...]] = {
    "actor": ("actor", "who does it", "player", "user", "character", "staff", "a child", "a machine", "the city"),
    "scale": ("scale", "size", "number of", "single", "neighbourhood", "neighborhood", "city", "region", "planet", "millions", "one street"),
    "time": ("time horizon", "decade", "year", "week", "long-term", "season", "century", "morning", "lifetime"),
    "setting": ("setting", "place", "room", "kitchen", "hospital", "outdoors", "school", "factory", "at sea", "in space"),
    "medium": ("medium", "paper", "audio", "video", "app", "physical", "print", "clay", "voice", "radio", "board game"),
}

CONNECT_MARKERS = ("from", "borrowed", "the way", "in the way that", "like how", "steal", "adapt", "port", "transplant")
CONNECT_MECHANISMS = (
    "routes", "sorts", "queues", "meters", "certifies", "prunes", "composts",
    "triages", "batches", "tunes", "rehearses", "audits", "rations", "seasons",
    "ferments", "indexes", "escrows", "holds", "keeps", "reserves", "waits",
    "ages", "cures", "locks", "rents", "lends", "trades", "grades", "weighs",
    "matches", "pairs", "chunks", "invoices", "stamps", "pawned", "recycles",
)

UNPACK_MARKERS = ("ingredient", "assumption", "tension", "overlooked", "taken for granted", "hidden", "cost of", "dependency", "unspoken", "quietly")

MOVE_SPECS = {
    "flip": {"dims": FLIP_DIMS, "label": "FLIP", "job": "reverse exactly one dimension"},
    "shift": {"dims": SHIFT_DIMS, "label": "SHIFT", "job": "move exactly one frame"},
    "connect": {"dims": {}, "label": "CONNECT", "job": "borrow one transferable mechanism"},
    "unpack": {"dims": {}, "label": "UNPACK", "job": "name one overlooked ingredient"},
}

RULES = """CONCEPT KITCHEN — rules
A round deals a SEED and one MOVE. You answer with a spark: title :: why it connects :: try next.

Four axes, 25 points each (100 total):
  1 MOVE DISCIPLINE  name the one dimension you changed (flip: assumption/role/property/
                     sequence/success/resource · shift: actor/scale/time/setting/medium).
                     Flip and shift also want the default you moved away from.
  2 MECHANISM        say why the transfer works: because / which lets / by turning.
                     A distant noun with no bridge is not an idea, it is a coincidence.
  3 ACTIONABILITY    try-next starts with a verb and carries a bound (one, by Friday, under $50).
  4 NOVELTY          token overlap against the whole table. Too close = derivative.
                     Too far without a bridge = noise, and it costs you 15%.

Penalties: slop words (synergy, seamless, unlock...) −10 each (max −20) · three or more
dimensions at once −15 · restating the seed −10 · over the word budget −10 · two or more
hedges −8. A hint costs 8 points.

Five rounds make a service. Round n+1 is seeded by your round-n spark, so a spark that
generates is worth more than a spark that merely sounds good. Humans and agents share one
leaderboard; the judge does not know who is typing.
"""


def content_tokens(text: str) -> set:
    return {w for w in WORD_RE.findall((text or "").lower()) if w not in STOP and len(w) > 2}


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def containment(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def _hit(low: str, needle: str) -> bool:
    """Short needles need word boundaries: 'app' must not match 'happens'."""
    if len(needle) <= 4 and needle.isalpha():
        return re.search(rf"(?<![a-z]){re.escape(needle)}(?![a-z])", low) is not None
    return needle in low


def _match_dims(text: str, dims: Dict[str, Tuple[str, ...]]) -> List[str]:
    low = text.lower()
    return [name for name, needles in dims.items() if any(_hit(low, n) for n in needles)]


def _has_any(text: str, needles: Sequence[str]) -> bool:
    low = text.lower()
    return any(_hit(low, n) for n in needles)


def _words(text: str) -> List[str]:
    return WORD_RE.findall((text or "").lower())


def score(submission: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Score one spark.

    submission: {title, why, try_next}
    ctx: {seed, move, distance, prior: [str], hint: bool, word_budget: int}
    """
    title = (submission.get("title") or "").strip()
    why = (submission.get("why") or "").strip()
    try_next = (submission.get("try_next") or "").strip()
    seed = ctx.get("seed") or ""
    move = ctx.get("move") or "flip"
    prior: List[str] = list(ctx.get("prior") or [])
    word_budget = int(ctx.get("word_budget") or 60)
    hint = bool(ctx.get("hint"))

    joined = f"{title} {why} {try_next}"
    low = joined.lower()
    words = _words(joined)
    notes: List[str] = []
    penalties: List[Tuple[str, int]] = []

    # 1 — move discipline ---------------------------------------------------
    discipline = 0
    dims_hit: List[str] = []
    if move in ("flip", "shift"):
        spec = MOVE_SPECS[move]
        dims_hit = _match_dims(joined, spec["dims"])
        if len(dims_hit) == 1:
            discipline += 18
            notes.append(f"names one dimension: {dims_hit[0]}")
        elif len(dims_hit) == 2:
            discipline += 9
            notes.append(f"names two dimensions ({', '.join(dims_hit)}) — one is enough")
        elif len(dims_hit) >= 3:
            notes.append(f"names {len(dims_hit)} dimensions ({', '.join(dims_hit)}) — pick one")
        else:
            notes.append("no changed dimension named")
        if _has_any(joined, CONTRAST):
            discipline += 7
            notes.append("names the default it moved away from")
    elif move == "connect":
        if _has_any(joined, CONNECT_MARKERS):
            discipline += 14
        if _has_any(joined, CONNECT_MECHANISMS):
            discipline += 11
        if discipline == 25:
            notes.append("source and borrowed mechanism both named")
        elif discipline == 0:
            notes.append("no source domain or mechanism named")
    else:  # unpack
        if _has_any(joined, UNPACK_MARKERS):
            discipline += 18
            notes.append("names the overlooked ingredient")
        if any(k in low for k in ("cost", "tension", "assumption", "dependency", "constraint")):
            discipline += 7
            notes.append("says what kind of ingredient it is")

    # 2 — mechanism ---------------------------------------------------------
    mechanism = 0
    if _has_any(joined, CONNECTORS):
        mechanism += 10
    why_tokens = content_tokens(why)
    title_tokens = content_tokens(title)
    if len(why_tokens - title_tokens) >= 3:
        mechanism += 8
    elif len(why_tokens - title_tokens) >= 1:
        mechanism += 4
        notes.append("the why repeats the title more than it explains it")
    hedges = sum(1 for h in ("could", "might", "potentially", "perhaps", "possibly", "may") if h in _words(why))
    if hedges == 0 and 5 <= len(_words(why)) <= 45:
        mechanism += 7
    elif hedges >= 2:
        notes.append("hedging instead of committing")

    # 3 — actionability -----------------------------------------------------
    action = 0
    tn_words = _words(try_next)
    if tn_words and tn_words[0] in IMPERATIVES:
        action += 12
    elif tn_words:
        notes.append("try-next does not open with a verb")
    if any(w.isdigit() for w in tn_words) or any(w in BOUNDS for w in tn_words):
        action += 8
    else:
        notes.append("try-next has no bound (one, by Friday, under $50)")
    if 3 <= len(tn_words) <= 25:
        action += 5

    # 4 — novelty -----------------------------------------------------------
    toks = content_tokens(joined)
    seed_toks = content_tokens(seed)
    best_j = max((jaccard(toks, content_tokens(p)) for p in prior), default=0.0)
    best_c = max((containment(toks, content_tokens(p)) for p in prior), default=0.0)
    j_seed = jaccard(toks, seed_toks)
    novelty = 0
    if best_c >= 0.72 or best_j >= 0.60:
        novelty = 0
        notes.append("derivative: the table already has this spark")
        distance = "near"
    elif best_j >= 0.40:
        novelty = 10
        distance = "near"
        notes.append("close to something already on the table")
    elif best_j >= 0.08:
        novelty = 25
        distance = "lateral"
    else:
        novelty = 15
        distance = "far"
        notes.append("nothing on the table overlaps it — the bridge carries the whole claim")
    if j_seed >= 0.55:
        novelty = min(novelty, 10)
        notes.append("mostly restates the seed")

    # penalties -------------------------------------------------------------
    slop_hits = sorted(w for w in set(words) if w in SLOP)
    if slop_hits:
        penalties.append((f"slop words: {', '.join(slop_hits)}", -min(20, 10 * len(slop_hits))))
    if len(dims_hit) >= 3:
        penalties.append((f"three or more dimensions changed at once ({', '.join(dims_hit)})", -15))
    if title and seed and jaccard(content_tokens(title), seed_toks) >= 0.8:
        penalties.append(("title restates the seed", -10))
    if len(words) > word_budget:
        penalties.append((f"over the {word_budget}-word budget", -10))
    if hedges >= 2:
        penalties.append(("two or more hedges", -8))

    raw = discipline + mechanism + action + novelty
    total = raw + sum(p for _, p in penalties)
    if distance == "far" and mechanism < 15:
        total = int(round(total * 0.85))
        notes.append("distant but unbridged — cost 15%")
    if hint:
        total -= 8
        notes.append("hint taken (−8)")
    total = max(0, min(100, total))

    return {
        "axes": {
            "move_discipline": discipline,
            "mechanism": mechanism,
            "actionability": action,
            "novelty": novelty,
        },
        "penalties": [{"reason": r, "points": p} for r, p in penalties],
        "total": total,
        "distance": distance,
        "dims": dims_hit,
        "verdict": verdict(total),
        "notes": notes,
        "hint": hint,
    }


def verdict(total: int) -> str:
    if total >= 90:
        return "NEW SAUCE"
    if total >= 72:
        return "SEASONED"
    if total >= 52:
        return "EDIBLE"
    if total >= 32:
        return "UNDERCOOKED"
    return "RAW"
