"""Where each state gets its material, without model calls or wall-clock endings."""
from __future__ import annotations

import importlib.util
import random
import re
import subprocess
import pathlib
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

from . import recall, storage

RNG = random.SystemRandom()
FEEDS = (
    "https://www.theonion.com/rss",
    "https://www.reddit.com/r/BrandNewSentence/.rss",
    "https://hnrss.org/frontpage",
)
# The event words a material line leads with. The account tallies them, so they live here next
# to the lines that emit them: when the copy pass renamed JOINED to LINKED, the engine kept
# counting the old word and every daydream account silently lost its tally.
MARKS = ("LINKED", "NO LINK", "link", "no link")

STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it",
        "of", "on", "or", "that", "the", "their", "this", "to", "was", "with", "you", "your"}


def ready(kind: str, graph_name: str = "wordnet", session: str | None = None) -> str | None:
    """Why a provider cannot start, before an active state is recorded."""
    if kind == "daydream" and len(_own_turns(session)) < 3:
        return "need at least 3 messages from you in this chat"
    if kind == "doomscroll":
        from . import settings
        if not bool(settings._raw("doomscroll_feed", True)):
            return "the feed is turned off in settings"
        if not feed():
            return "the feed came back empty"
    if kind == "dream":
        commits = sum(len(_recent_subjects(root)) for root in projects())
        if commits < 3 and len(_day_threads(session)) < 2:
            return "nothing from today yet · say a few things in this chat or run a state first"
    if kind == "unstuck":
        if not _recent_work(session):
            return "nothing to go on yet · say what you are working on, then try again"
        if not _graph_edge(storage.project_root(), session):
            return "the map has no links to point at yet"
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
        # Two resets and the same hop again: the seed resolves to the same start every time, so
        # clearing the cursor changes nothing. Set out from a random node the graph can leave, and
        # leave a line saying where — that is the difference between a walk that moves and one that
        # reports the pool is drained.
        if out:
            engine.record("state", f"walk '{name}' repeated '{_hop_key(out[0])}' "
                                   f"· shown: {' | '.join(recent)}", event="walk")
        node = walk._movable_start()
        if node is not None:
            walk._write_cursor(node["id"], "", [], [])
            out = walk.step(steps)
            if out and _hop_key(out[0]) not in recent:
                engine.record("state", f"walk '{name}' set out from '{node['label']}' "
                                       f"after a repeat", event="walk")
                return out
        engine.record("state", f"walk '{name}' could not move · the same hop came back after "
                               f"two fresh starts and a random one", event="walk")
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


def _own_turns(session: str | None = None) -> List[str]:
    """Only the person's recorded turns from THIS chat, never a memory backend.

    Newest first, matching `_recent_subjects`. The ring is chronological, so reading it straight
    put the OLDEST turn in subjects[0] — which `unstuck` calls `last` and treats as the thing just
    finished. A chat that began with a pasted install command declined forever on that paste and
    never reached what the person said next.
    """
    seen, out = set(), []
    for raw in reversed(recall.recent(recall.CAP, who="person", session=session)):
        text = _clip(raw, 160)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _covered_indexes(ident: Any) -> List[int]:
    """The subject indexes an ident encodes, and nothing else.

    Two forms: daydream's bare `<left>:<right>`, and dream's
    `<project>:<left>|<project>:<right>`. Reading every digit in the string made a project named
    `repo2` count as subject 2, so a shown pair forged coverage and the ordering re-anchored on
    subject 0 — the exact defect the tally exists to prevent.
    """
    text = str(ident or "")
    parts = text.split("|") if "|" in text else [text]
    out: List[int] = []
    for part in parts:
        # In the project form the index is the tail after the last colon; in the bare form both
        # sides are indexes. A name may contain digits, so only a wholly numeric tail counts.
        pieces = part.split(":") if "|" not in text else [part.rsplit(":", 1)[-1]]
        for piece in pieces:
            if piece.isdigit() and len(piece) <= 6:
                out.append(int(piece))
    return out


def _by_coverage(pool: List[Tuple[int, int, Any]],
                 skip: set[str] | None = None) -> List[Any]:
    """Order pairs so a dose compares different things instead of one anchor twice.

    Taking the first N pairs in index order gives (0,1) then (0,2): a 2-pair dose that
    reused its left side and never reached the rest of the day. Least-used subject first,
    so independent comparisons come before repeat anchors and every subject gets reached
    as early as the material allows.
    """
    out: List[Any] = []
    used: dict[int, int] = {}
    # The engine asks for ONE unit per turn, so this runs again on every turn with the earlier
    # pairs in `skip`. Starting the tally empty each time re-anchored on subject 0 forever: the
    # ordering only worked when a single call asked for the whole dose, which is not how the
    # dose is delivered. What was already shown is what has already been covered.
    for ident in (skip or set()):
        for n in _covered_indexes(ident):
            used[n] = used.get(n, 0) + 1
    remaining = list(pool)
    while remaining:
        pick = min(remaining, key=lambda c: (used.get(c[0], 0) + used.get(c[1], 0),
                                             max(used.get(c[0], 0), used.get(c[1], 0)),
                                             c[0], c[1]))
        remaining.remove(pick)
        out.append(pick[2])
        used[pick[0]] = used.get(pick[0], 0) + 1
        used[pick[1]] = used.get(pick[1], 0) + 1
    return out


def memory_pairs(steps: int = 1, skip: set[str] | None = None, keyed: bool = False,
                 session: str | None = None) -> List[Any]:
    """Two recorded turns from this chat, what they touch, and one possibility."""
    pool = _own_turns(session)
    if len(pool) < 2:
        return ["daydream: need at least 2 messages from you in this chat"]
    skip = skip or set()
    choices = []
    for left in range(len(pool)):
        for right in range(left + 1, len(pool)):
            a, b = pool[left], pool[right]
            ident = f"{left}:{right}"
            if ident in skip:
                continue
            shared = sorted(_words(a) & _words(b))
            if shared:
                touch = ", ".join(shared[:3])
                line = (f"LINKED · one: {_clip(a, 96)} · two: {_clip(b, 96)} "
                        f"· shared: {touch} · idea: try {touch} as the topic")
            else:
                # Two unrelated turns are not a connection. Calling every pair JOINED and
                # inventing a possibility from "the gap between them" manufactured an insight
                # the material did not support, against the state's own exit instruction.
                line = (f"NO LINK · one: {_clip(a, 96)} · two: {_clip(b, 96)} "
                        f"· shared: nothing · idea: none, these do not connect")
            # Declared, not mined: "LINKED", "shared", "idea", "topic" are the template's
            # words, and harvesting the sentence turned them into the person's concepts.
            choices.append((left, right, (ident, line,
                                          _terms_of(a) + _terms_of(b) + shared[:3])))
    if not choices:
        return ["daydream: no new pairs left"]
    selected = _by_coverage(choices, skip)[:max(1, int(steps))]
    return selected if keyed else [line for _, line, _ in selected]


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


def _day_threads(session: str | None = None) -> List[Tuple[str, str]]:
    """What this chat did today, with no git involved.

    A day exists whether or not anyone committed anything. Git was the only source, so `/dream`
    refused in every chat that was not inside a repository — which is most of them, including a
    chat in the operator's home. The person's own turns come first; the concepts the plugin
    served this chat come next, tagged with the state that surfaced them. Both are this chat's
    own record, so nothing crosses chats.
    """
    turns = _own_turns(session)
    if len(turns) >= 2:
        return [("today", _clip(turn, 100)) for turn in turns]
    from . import history
    who = str(session or "")
    rows = [r for r in history.recent(days=3, limit=60)
            if not who or str(r.get("session") or "") == who]
    seen, out = set(), []
    for row in rows:
        label = str(row.get("label") or "").strip()
        if not label or label in seen:
            continue
        seen.add(label)
        out.append((str(row.get("move") or "today"), label))
    return out


#: A line the person ran rather than thought. Anchored at the start so prose that merely
#: mentions a tool ("the git history is a mess") is still material.
_CMD_VERB = re.compile(
    r"^\s*(?:tar|cd|python3?|pip3?|npm|npx|node|git|curl|wget|uvx|uv|bash|sh|zsh|sudo"
    r"|chmod|chown|mkdir|cp|mv|rm|ls|cat|echo|export|source|brew|winget|choco|py|dotnet"
    r"|cargo|make|docker|kubectl|ssh|scp|hermes)\b", re.I)
#: Flags, backslash paths and filenames: the shapes a shell paste has and a sentence does not.
_CMD_SHAPE = re.compile(
    r"\\|(?:^|\s)--?[A-Za-z][\w-]*"
    r"|\.(?:py|gz|tar|zip|json|md|txt|exe|sh|yaml|yml|js|mjs|ts|toml|cfg|ini|lock)\b", re.I)
#: `antemuse-0` is where the tokenizer stopped at the first dot of a version.
_VERSIONISH = re.compile(r"^[A-Za-z][A-Za-z0-9]*-\d")


def _terms_of(text: str) -> List[str]:
    """The concept-sized terms in one piece of the person's own material.

    A whole turn is a sentence, and recording it whole gave accounts like
    "the parser keeps failing on ne" - truncated mid-word by the ledger's label cap.
    Extraction is sound here: it reads what the person said, not the template around it.
    """
    from . import history
    prose = []
    for line in str(text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        # A pasted command is something the person ran, not something they were thinking
        # about. `tar -xzf antemuse-0.12.7.tar.gz` used to yield antemuse-0, python,
        # scripts, install: single tokens, but filename fragments nobody would recognise.
        if _CMD_VERB.match(s) or _CMD_SHAPE.search(s):
            continue
        prose.append(s)
    try:
        terms = list(history.extract(" ".join(prose), limit=6))
    except Exception:  # health: BLE001 -- material without terms is still material
        return []
    return [w for w in terms if not _VERSIONISH.match(w)][:4]


def day_connections(steps: int = 1, skip: set[str] | None = None, keyed: bool = False,
                    session: str | None = None) -> List[Any]:
    """Connect two things from the day: commits when there are any, otherwise the day's record."""
    subjects = [(root.name, subject) for root in projects() for subject in _recent_subjects(root)]
    if len(subjects) < 2:
        subjects = _day_threads(session)
    if len(subjects) < 2:
        return ["dream: nothing from today yet · say a few things in this chat or run a state first"]
    skip = skip or set()
    pool = []
    for left in range(len(subjects)):
        for right in range(left + 1, len(subjects)):
            project_a, a = subjects[left]
            project_b, b = subjects[right]
            ident = f"{project_a}:{left}|{project_b}:{right}"
            if ident in skip:
                continue
            shared = sorted(_words(a) & _words(b))
            # The terms are declared, not mined back out of the sentence: the rendered line
            # contains "link", "shared", "connect", and harvesting it made the plugin's own
            # scaffolding into the person's concepts.
            terms = _terms_of(a) + _terms_of(b) + shared[:3]
            if shared:
                bridge = ", ".join(shared[:3])
                pool.append((left, right, ident,
                             f"link · {project_a}: {a} ↔ {project_b}: {b} "
                             f"· shared: {bridge}", terms))
            else:
                pool.append((left, right, ident,
                             f"no link · {project_a}: {a} ↔ {project_b}: {b} "
                             f"· shared: nothing yet · these two do not connect", terms))
    if not pool:
        return ["dream: no new pairs left"]
    choices = _by_coverage([(left, right, (ident, line, terms))
                            for left, right, ident, line, terms in pool], skip)
    selected = choices[:max(1, int(steps))]
    return selected if keyed else [line for _, line, _ in selected]


def _strip_xml(text: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", "", text or "").split())


#: Openers that make third-party text read as an instruction once it is inside a model's
#: context. The `[UNTRUSTED FEED TEXT]` header is a mitigation, not a boundary, so the text
#: itself is neutralised rather than trusted to the label.
_DIRECTIVE_OPENER = re.compile(
    r"^\s*(?:\[[^\]]{0,40}\]\s*)?"
    r"(?:ignore\b|disregard\b|forget\b|override\b|system\s*:|assistant\s*:|user\s*:|"
    r"you\s+are\b|act\s+as\b|new\s+instructions?\b|instruction\s*:)",
    re.I)


#: The same openers searched anywhere. Anchoring at the start meant a benign prefix carried the
#: imperative through: a headline beginning "Breaking:" and then telling the model to discard its
#: prior context matched nothing. The phrase is described rather than quoted here so the payload
#: scanner does not read this detector as the thing it detects.
_DIRECTIVE_ANYWHERE = re.compile(
    r"(?:ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\b|disregard\s+(?:all\s+)?"
    r"(?:previous|prior|above|earlier)\b|forget\s+(?:all\s+)?(?:previous|prior|above|earlier)\b|"
    r"new\s+instructions?\b|instructions?\s*:|system\s*:|assistant\s*:|"
    r"you\s+are\s+now\b|act\s+as\b|override\s+(?:all\s+)?(?:previous|prior|your)\b|"
    r"^\s*(?:\[[^\]]{0,40}\]\s*)?(?:ignore|disregard|forget|override|user\s*:))",
    re.I)


def _defang_title(text: str) -> str:
    """An imperative feed title arrives marked as reported speech, not as an address.

    Nothing is dropped: a hostile headline is still material the person may find interesting.
    It just cannot present itself as something addressed to the model. An ordinary headline
    passes through with its whitespace normalised.
    """
    clean = " ".join(str(text or "").split())
    if not clean:
        return ""
    if _DIRECTIVE_ANYWHERE.search(clean):
        # Keep the words, remove the address. The prefix says whose voice this is.
        return f"headline says: {clean}"
    return clean


def _user_agent() -> str:
    """Name the version we actually are. A hardcoded one went stale at 0.11 and stayed there."""
    try:
        import re as _re
        manifest = pathlib.Path(__file__).resolve().parents[1] / "plugin.yaml"
        m = _re.search(r'^version:\s*"?([0-9][^"\s]*)"?', manifest.read_text(), _re.M)
        if m:
            return f"antemuse/{m.group(1)}"
    except Exception:  # health: BLE001 -- a feed fetch must not fail over its own name
        pass
    return "antemuse"


def _fetch_feed(url: str, limit: int = 12) -> List[Dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
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
        out.append({"source": source, "title": _clip(_defang_title(title), 120)})
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
        return ["doomscroll: the feed is turned off in settings"]
    items = feed()
    if not items:
        return ["doomscroll: the feed came back empty"]
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
        return ["doomscroll: no new posts left"]
    return out if keyed else [line for _, line in out]


def _graph_edge(root: Path | None = None, session: str | None = None) -> str:
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

            who = str(session or "")
            terms = [str(r.get("label") or "") for r in history.recent(days=7, limit=60)
                     if not who or str(r.get("session") or "") == who]
        except Exception:
            terms = []
        # Then the words this chat itself used, so a chat with no ledger still has ground.
        terms += [w for turn in _own_turns(session) for w in sorted(_words(turn))][:24]
        if root is not None:
            terms += [part.lower() for part in re.findall(r"[A-Za-z]{4,}", root.name)]
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


def _recent_work(session: str | None = None) -> List[str]:
    """What this chat has been doing: commits when there are any, otherwise its own day."""
    root = storage.project_root()
    if root is not None:
        subjects = _recent_subjects(root)
        if subjects:
            return subjects
    return [text for _, text in _day_threads(session)]


def _is_command(text: str) -> bool:
    """True when the material is something the person ran, not something they were attempting."""
    for line in str(text or "").splitlines():
        s = line.strip()
        if s and (_CMD_VERB.match(s) or _CMD_SHAPE.search(s)):
            return True
    return False


def unstuck_text(steps: int = 1, skip: set[str] | None = None, keyed: bool = False,
                 session: str | None = None) -> List[Any]:
    """One next move grounded in what you have been doing plus one map link. No repo required."""
    subjects = _recent_work(session)
    edge = _graph_edge(storage.project_root(), session)
    if not subjects:
        return ["unstuck: nothing to go on yet · say what you are working on, then try again"]
    if not edge:
        return ["unstuck: the map has no links to point at yet"]
    # The point of being stuck is that the last change is the obvious next move and it is not
    # working. Recommending `subjects[0]` — the newest commit, the thing just finished — told the
    # person to continue exactly what they had done. The direction is grounded in earlier work
    # and names what to step away from.
    last = subjects[0]
    earlier = next((s for s in subjects[1:] if s != last), "")
    ident = f"{earlier or last}|{edge}"
    if ident in (skip or set()):
        return ["unstuck: no new move left"]
    # The sentence shape is fixed and only the two nouns change, so a noun that is not an
    # attempt makes nonsense: "install the tarball a different way, write a test for it".
    # The state's own exit instruction says to decline when the material cannot support a
    # suggestion; until now the only refusal branch was "this pair was already suggested".
    unusable = [s for s in (last, earlier) if s and _is_command(s)]
    if unusable:
        line = (f"no move to suggest · the map link is real ({edge}) but "
                f"{'both slots' if len(unusable) > 1 else 'one slot'} held a command you ran, "
                f"not an attempt to vary · say what you were trying and what went wrong, "
                f"then ask again")
    elif earlier:
        line = (f"next move · skip another pass at {last} · try {earlier} a different way "
                f"· map link: {edge} · first: write the smallest test for that different way")
    else:
        line = (f"next move · only one thing here ({last}), so there is nothing earlier to "
                f"go back to · map link: {edge} · first: write the smallest test that comes at "
                f"{last} from that side instead")
    edge_terms = [part.strip() for part in re.split(r"→|\(", edge) if part.strip()]
    terms = _terms_of(last) + (_terms_of(earlier) if earlier else []) + edge_terms[:2]
    result = [(ident, line, terms)]
    return result if keyed else [line]


PROVIDERS = {
    "walk": walk_text,
    "daydream": memory_pairs,
    "doomscroll": scroll_text,
    "dream": day_connections,
    "unstuck": unstuck_text,
}
