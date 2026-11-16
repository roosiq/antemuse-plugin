"""Walks are data, not code: a walk is a graph plus the rules for moving on it.

The built-ins cover WordNet (up, down, across, wander), but a user can drop a
JSON file in `$ANTEMUSE_STATES_HOME/walks/` and walk their own graph:

    {"name": "hearth",
     "title": "Hearth walk",
     "graph": "manual",
     "edges": {"salt": ["brine", "cure"], "brine": ["salt", "fish"]},
     "seed": {"mode": "fixed", "node": "salt"},
     "avoid_backtrack": true}

Nothing here calls a model. A step is a real edge on a real graph, chosen by the
walk's own policy, and the cursor keeps each walk where it left off.
"""
from __future__ import annotations

import json
import os
import random
import time
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RNG = random.SystemRandom()

HOME = Path.home()


def _data_dir() -> Path:
    try:
        from . import storage
        return storage.data_dir()
    except Exception:
        return HOME / ".hermes" / "plugin-data" / "antemuse"


def cursor_path() -> Path:
    """Resolved at call time: the data dir depends on env that may load later."""
    return _data_dir() / "walk_cursor.json"


CURSOR = cursor_path()
NLTK_HOME = HOME / "nltk_data"
if NLTK_HOME.is_dir():
    os.environ.setdefault("NLTK_DATA", str(NLTK_HOME))

ALL_RELATIONS = ["hypernym", "hyponym", "holonym", "meronym", "similar", "also", "antonym"]

BUILTIN: Dict[str, Dict[str, Any]] = {
    "outer": {
        "title": "Outer — jumps to the farthest concept each step, not the nearest",
        "graph": "wordnet",
        "relations": ALL_RELATIONS,
        "jump": "far",
        "seed": {"mode": "continue"},
        "avoid_backtrack": False,
    },
    "wander": {
        "title": "Wander — every WordNet edge, no direction",
        "graph": "wordnet",
        "relations": ALL_RELATIONS,
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
    "upward": {
        "title": "Upward — hypernyms and wholes only, toward the general",
        "graph": "wordnet",
        "relations": ["hypernym", "holonym"],
        "seed": {"mode": "continue"},
        "avoid_backtrack": False,
    },
    "downward": {
        "title": "Downward — hyponyms and parts only, toward the specific",
        "graph": "wordnet",
        "relations": ["hyponym", "meronym"],
        "seed": {"mode": "continue"},
        "avoid_backtrack": False,
    },
    "composite": {
        "title": "Composite — every navigation in one walk: run, far, vault, orbit, near",
        "graph": "wordnet",
        "relations": ALL_RELATIONS,
        "jump": "composite",
        "samples": 48,
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
    "vault": {
        "title": "Vault — two far jumps per step: the graph it lands in is not the one it left",
        "graph": "wordnet",
        "relations": ALL_RELATIONS,
        "jump": "vault",
        "samples": 64,
        "seed": {"mode": "continue"},
        "avoid_backtrack": False,
    },
    "run3": {
        "title": "Run3 — three adjacent edges reported as one arc, so the step covers distance",
        "graph": "wordnet",
        "relations": ALL_RELATIONS,
        "jump": "run:3",
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
    "orbit": {
        "title": "Orbit — one near edge, then one far jump, alternating",
        "graph": "wordnet",
        "relations": ALL_RELATIONS,
        "jump": "orbit",
        "samples": 48,
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
    "lateral": {
        "title": "Lateral — similars, also-sees and opposites, never up or down",
        "graph": "wordnet",
        "relations": ["similar", "also", "antonym"],
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
}


# --------------------------------------------------------------------- graphs

class Graph:
    """A graph a walk can move on. Subclasses supply nodes and named edges."""
    name = "graph"

    def resolve(self, word: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def random_node(self, relations: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def edges(self, node: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        raise NotImplementedError

    def resume(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.resolve(node_id)

    def far_from(self, node: Dict[str, Any], samples: int = 32,
                 avoid: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Graphs without distance say so, rather than pretending to jump."""
        return None


_GLOSS_STOP = {"the", "a", "an", "of", "or", "and", "to", "in", "by", "for", "with",
               "something", "someone", "that", "this", "is", "as", "from", "act",
               "state", "quality", "being", "make", "makes", "making", "into", "its"}


def _content_words(text: str) -> set:
    import re
    return {w for w in re.findall(r"[a-z]{4,}", str(text).lower()) if w not in _GLOSS_STOP}


def _node(id_: str, label: str, pos: str = "", gloss: str = "", **extra) -> Dict[str, Any]:
    return {"id": id_, "label": label, "pos": pos, "gloss": gloss, **extra}


class WordNetGraph(Graph):
    name = "wordnet"
    _node = staticmethod(_node)
    SEEDS = ["walk", "dream", "light", "river", "memory", "door", "signal", "salt",
             "night", "hand", "stone", "weather"]

    def __init__(self) -> None:
        self._wn = None
        self._words: Optional[List[str]] = None

    def wn(self):
        if self._wn is None:
            from nltk.corpus import wordnet as wn
            self._wn = wn
        return self._wn

    def resolve(self, word: str) -> Optional[Dict[str, Any]]:
        syns = self.wn().synsets(word.replace(" ", "_"))
        if not syns:
            return None
        syn = syns[0]
        return self._node(syn.name(), syn.lemma_names()[0].replace("_", " "), syn.pos(), syn.definition())

    def random_node(self, relations: Optional[List[str]] = None) -> Dict[str, Any]:
        """Pick a start that can actually move in the walk's chosen directions."""
        pool = []
        for word in self.SEEDS:
            try:
                syn = self.wn().synsets(word)[0]
            except Exception:
                continue
            if relations:
                rels = {r for r, _ in self.edges(self._node(syn.name(), word))}
                if not rels & set(relations):
                    continue
            pool.append(syn)
        syn = RNG.choice(pool) if pool else self.wn().synsets(RNG.choice(self.SEEDS))[0]
        return self._node(syn.name(), syn.lemma_names()[0].replace("_", " "), syn.pos(), syn.definition())

    def resume(self, node_id: str) -> Optional[Dict[str, Any]]:
        """The cursor's node, or None.

        `wn.synset()` answers None as well as raising for an id that is not a synset, and the
        unattended `.name()` on that None took down a live walk with
        `AttributeError: 'NoneType' object has no attribute 'name'`. A cursor that names
        something WordNet cannot resolve means "start again", not "fail".
        """
        try:
            syn = self.wn().synset(node_id)
        except Exception:
            return None
        if syn is None:
            return None
        try:
            return self._node(syn.name(), syn.lemma_names()[0].replace("_", " "),
                              syn.pos(), syn.definition())
        except Exception:
            return None

    def rim(self, node: Dict[str, Any], depth: int = 2,
            budget: int = 400) -> List[Dict[str, Any]]:
        """Nodes two relation-steps out — the neighbourhood's edge, not the dictionary."""
        try:
            start = self.wn().synset(node["id"])
        except Exception:
            return []
        if start is None:
            return []
        seen = {start.name()}
        frontier = [self._node(start.name(), start.lemma_names()[0].replace("_", " "),
                               start.pos(), start.definition())]
        out: List[Dict[str, Any]] = []
        # `depth=2` means two steps out, so the one-step ring is walked but not returned: it
        # was included, which is why `outer` could land on a direct neighbour of the node it
        # left (`hand → digital arteries`) and why its own test failed on some draws.
        for level in range(1, max(1, depth) + 1):
            nxt: List[Dict[str, Any]] = []
            for cur in frontier:
                for _rel, child in self.edges(cur):
                    if child["id"] in seen:
                        continue
                    seen.add(child["id"])
                    nxt.append(child)
                    if level >= 2:
                        out.append(child)
                    if len(seen) >= budget:
                        return out
            frontier = nxt
            if not frontier:
                break
        return out

    def far_from(self, node: Dict[str, Any], samples: int = 32,
                 avoid: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """The farthest node on the rim: two steps out, as far as that goes.

        This used to sample uniformly from `wordnet.words()` and keep the least
        similar, which guaranteed an unrelated word — `idea → zebra-tailed
        lizard → Hydra` is what that policy is. A jump is now the outer rim of
        the connected neighbourhood: never a direct neighbour, always reachable
        within two relation steps, and chosen from the farthest of a sample so
        two walks do not take the same hop.
        """
        skip = set(avoid or []) | {node["id"]}
        cands = [c for c in self.rim(node, depth=2) if c["id"] not in skip]
        if not cands:
            # No rim is not a reason to step: "one edge out is still a hop" made `outer`
            # serve a neighbour, which is the one thing a walk named for distance must not
            # do. Say there is nothing far, and let the walk restart and report it.
            return None
        try:
            cur = self.wn().synset(node["id"])
        except Exception:
            cur = None
        if cur is None:
            return RNG.choice(cands)
        pool = cands if len(cands) <= samples else RNG.sample(cands, samples)
        # Of the rim, prefer the hops whose own definition does not already reuse
        # the words of the one we are leaving: siblings under the same parent are
        # "distance" that reads as a restatement.
        mine = _content_words(node.get("gloss") or "")
        fresh = [c for c in pool if not (_content_words(c.get("gloss") or "") & mine)]
        pool = fresh or pool
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for cand in pool:
            try:
                cand_syn = self.wn().synset(cand["id"])
                sim = cur.path_similarity(cand_syn) if cand_syn is not None else None
            except Exception:
                sim = None
            scored.append((0.0 if sim is None else float(sim), cand))
        scored.sort(key=lambda t: t[0])
        # Among the farthest few, not the single farthest: a fixed answer would
        # make every walk of a node identical, and this walk is supposed to move.
        edge = scored[:max(1, min(6, len(scored)))]
        return RNG.choice(edge)[1]


    def edges(self, node: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Named edges out of a node; none when the id is not a synset.

        A cursor learned by an older version can hold a label instead of a
        synset name. Asking WordNet for that returns None and every probe then
        raised `'NoneType' object has no attribute '_hypernyms'`, which a walk
        surfaced as material. An id that does not resolve has no edges.
        """
        try:
            syn = self.wn().synset(node["id"])
        except Exception:
            return []                       # a malformed name is not a node
        if syn is None:
            return []
        probes = {
            "hypernym": lambda s: s.hypernyms(),
            "hyponym": lambda s: s.hyponyms(),
            "holonym": lambda s: s.part_holonyms() + s.member_holonyms() + s.substance_holonyms(),
            "meronym": lambda s: s.part_meronyms() + s.member_meronyms() + s.substance_meronyms(),
            "similar": lambda s: getattr(s, "similar_tos", lambda: [])(),
            "also": lambda s: s.also_sees(),
            "antonym": lambda s: [a.synset() for l in s.lemmas() for a in l.antonyms()],
        }
        out: List[Tuple[str, Dict[str, Any]]] = []
        for rel, fn in probes.items():
            try:
                for t in fn(syn):
                    if t is not None:
                        out.append((rel, self._node(t.name(), t.lemma_names()[0].replace("_", " "),
                                                    t.pos(), t.definition())))
            except Exception:
                continue
        return out


class ManualGraph(Graph):
    """A user-authored graph: an adjacency list in the walk's own file."""
    name = "manual"

    def __init__(self, edges: Dict[str, List[str]], labels: Optional[Dict[str, Dict[str, str]]] = None):
        self.edges_map = {k: list(v) for k, v in (edges or {}).items()}
        self.labels = labels or {}

    def _mk(self, key: str) -> Dict[str, Any]:
        meta = self.labels.get(key, {})
        return _node(key, meta.get("label", key), meta.get("pos", ""), meta.get("gloss", ""))

    def resolve(self, word: str) -> Optional[Dict[str, Any]]:
        key = word.strip().lower()
        return self._mk(key) if key in self.edges_map else None

    def random_node(self, relations: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        return self._mk(RNG.choice(list(self.edges_map))) if self.edges_map else None

    def edges(self, node: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        rel = "next"
        return [(rel, self._mk(n)) for n in self.edges_map.get(node["id"], [])]


GRAPHS = {"wordnet": WordNetGraph, "manual": ManualGraph}


# ----------------------------------------------------------------------- walk

class GraphWalk:
    """One walkable graph plus the policy that decides each step."""

    def __init__(self, spec: Dict[str, Any], cursor_path: Path):
        self.spec = dict(spec)
        self.name = str(spec.get("name") or "wander")
        self.cursor_path = cursor_path
        self.graph_name = spec.get("graph", "wordnet")
        if self.graph_name == "manual":
            self.graph: Graph = ManualGraph(spec.get("edges", {}), spec.get("labels"))
        else:
            self.graph = GRAPHS[self.graph_name]()
        default_rel = ["next"] if self.graph_name == "manual" else ALL_RELATIONS
        self.relations = spec.get("relations") or default_rel
        self.avoid_backtrack = bool(spec.get("avoid_backtrack", True))
        self.seed_spec = spec.get("seed") or {"mode": "continue"}
        self.jump = spec.get("jump")
        # how wide a far search looks. Wider is further out: 32 samples is a jump to the
        # edge of the neighbourhood, 64 is a jump out of it.
        self.samples = int(spec.get("samples") or 32)
        # A composite walk is not a fifth policy: it is every policy, in a fixed rotation,
        # so one walk covers ground by running, by stepping, by jumping and by vaulting.
        self.rotation = tuple(spec.get("rotation") or
                              ("run:3", "far", "near", "vault", "orbit"))

    # -- cursor, per walk name, so two walks never fight over one place
    def _cursors(self) -> Dict[str, Dict[str, Any]]:
        try:
            data = json.loads(self.cursor_path.read_text())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _read_cursor(self) -> Dict[str, Any]:
        cur = self._cursors().get(self.name)
        return cur if isinstance(cur, dict) else {}

    def _write_cursor(self, node_id: str, prev: str, used: Optional[List[str]] = None) -> None:
        data = self._cursors()
        entry = {"node": node_id, "prev": prev, "at": time.time()}
        if used:
            # remembering what this walk has already started from is what keeps two
            # entries in the same repository from opening on the same word
            entry["used"] = [t for t in dict.fromkeys(used) if t][-12:]
        data[self.name] = entry
        self.cursor_path.parent.mkdir(parents=True, exist_ok=True)
        self.cursor_path.write_text(json.dumps(data))

    def reset(self) -> None:
        data = self._cursors()
        data.pop(self.name, None)
        self.cursor_path.write_text(json.dumps(data))

    # -- where we are
    def start_node(self) -> Optional[Dict[str, Any]]:
        mode = (self.seed_spec or {}).get("mode", "continue")
        # a seed places the first step; after that the walk continues from its cursor
        cur = self._read_cursor().get("node")
        # A walk is where you left it, not where it was three days ago: an old
        # cursor kept the walk in leftover WordNet space (`finback → mammal
        # genus`) instead of setting out from the work in front of the person.
        stale = (time.time() - float(self._read_cursor().get("at") or 0)) > 12 * 3600
        if cur and not stale and mode in ("fixed", "word", "continue"):
            resumed = self.graph.resume(cur)
            if resumed is not None:
                return resumed
        if mode == "fixed":
            return self.graph.resolve(str(self.seed_spec.get("node", "")))
        if mode == "word":
            return (self.graph.resolve(str(self.seed_spec.get("word", "")))
                    or self.graph.random_node(self.relations))
        if mode == "random":
            return self.graph.random_node(self.relations)
        # `continue` with no cursor, and the new `project` mode, draw from the mix:
        # 50 % the repository, 30 % the conversation, 20 % deliberately unrelated.
        try:
            from . import seeding
            for seed in seeding.candidates("walk", when=time.time(),
                                           exclude=self._used_terms(),
                                           goal=str((self.seed_spec or {}).get("goal") or "")):
                resolved = self.graph.resolve(seed["term"])
                if resolved is not None:
                    # the marker is claimed only when the seed was actually used: a
                    # journal that says "project:antemuse" over a random start is a lie
                    self._seed_marker = seeding.marker(seed)
                    return resolved
        except Exception:
            pass
        return self.graph.random_node(self.relations)

    def _used_terms(self) -> List[str]:
        try:
            return [str(x) for x in (self._read_cursor().get("used") or [])][-12:]
        except Exception:
            return []

    def step(self, steps: int = 1) -> List[str]:
        self._seed_marker = ""
        node = self.start_node()
        if node is None:
            return [f"walk unavailable · graph '{self.graph_name}' has no starting node"]
        prev_id = self._read_cursor().get("prev", "")
        prefix = f"[{self._seed_marker}] " if getattr(self, "_seed_marker", "") else ""
        # The goal is distant *and connected*: distance without a path back is noise. The
        # anchor is the concept the walk set out from — the task's own, when a task seed
        # was available — and every line says how far it went and how it gets back.
        anchor = node["label"]
        hops = 0
        trail: List[str] = [anchor]

        def back(jumped: bool = False) -> str:
            path = " → ".join(trail[-4:])
            how = "jumped" if jumped else f"{hops} hop{'s' if hops != 1 else ''}"
            return f" · ↩ {how} from {anchor}: {path}"
        out: List[str] = []
        # A jump used to be able to land back on a node the walk had already left,
        # which reads as a loop rather than as distance. Everything the walk has
        # stood on stays out of the far search.
        visited_ids = {node["id"]}

        def far(node_, avoid=None):
            if not hasattr(self.graph, "far_from"):
                return None
            skip = list(dict.fromkeys(str(x) for x in [*(avoid or []), *visited_ids]))
            return self.graph.far_from(node_, samples=self.samples, avoid=skip)

        def unseen(node_) -> bool:
            try:
                from . import history
                return not history.known(str(node_.get("label") or ""))
            except Exception:
                return True

        def pick(cands):
            """Of the candidates, prefer one the ledger has not been to.

            Distance is the walk's goal; landing on the same concept a third session running
            is not distance, it is a habit. When every candidate is known the walk takes one
            anyway and says so, because a dead walk is worse than a repeated one.
            """
            if not cands:
                return None
            fresh = [c for c in cands if unseen(c[1] if isinstance(c, tuple) else c)]
            return RNG.choice(fresh) if fresh else RNG.choice(cands)

        def far_fresh(node_, avoid=None, tries: int = 5):
            """`far_from` returns one node; ask a few times so there is something to choose."""
            best = None
            for _ in range(tries):
                cand = far(node_, avoid=avoid)
                if cand is None:
                    continue
                if best is None:
                    best = cand
                if unseen(cand):
                    return cand
            return best

        def visited(node_) -> str:
            """Has the ledger been here? This is the answer a walk never had."""
            try:
                from . import history
                past = history.seen_before(str(node_.get("label") or ""))
                if past.get("sessions"):
                    return (f" · seen {history.when(past.get('last_session_at'))}"
                            f" in {past['sessions']} other session"
                            f"{'s' if past['sessions'] != 1 else ''}")
            except Exception:
                pass
            return ""

        def remember(node_) -> None:
            try:
                from . import engine, history
                # The session the state belongs to, not an empty string: the pane asks
                # activations(<state's session>) and a serving filed under "" is invisible to it,
                # so a running walk lit nothing while serving a concept per hop.
                origin = engine.current_origin() or {}
                history.notice(str(node_.get("label") or ""), move="walk",
                               session=str(origin.get("session_id") or ""))
            except Exception:
                pass

        def line(a, b, how, jumped: bool = False):
            gloss = (b.get("gloss") or "").split(";")[0][:90]
            remember(b)
            return (f"{a['label']} ({a['pos'] or 'thing'}) → {b['label']} "
                    f"({b['pos'] or 'thing'}) · {how}"
                    + (f" · “{gloss}”" if gloss else "") + back(jumped) + visited(b))

        def mode_at(n):
            if self.jump != "composite":
                return self.jump
            return self.rotation[n % len(self.rotation)]

        for n in range(steps):
            visited_ids.add(node["id"])
            mode = mode_at(n)
            # --- navigation policies that leave the neighbourhood -----------------
            if mode == "vault":
                near = far_fresh(node, avoid=[prev_id])
                beyond = far_fresh(near, avoid=[node["id"], prev_id]) if near else None
                if near is not None and beyond is not None:
                    gloss = (beyond.get("gloss") or "").split(";")[0][:90]
                    hops += 2
                    if beyond["label"] not in trail:
                        trail.append(beyond["label"])
                    remember(beyond)
                    out.append(f"{node['label']} → {beyond['label']} "
                               f"({beyond['pos'] or 'thing'}) · vaulted past {near['label']}"
                               + (f" · “{gloss}”" if gloss else "") + back(jumped=True)
                               + visited(beyond))
                    prev_id, node = near["id"], beyond
                    continue
            elif mode == "orbit":
                skip = far_fresh(node, avoid=[prev_id])
                if skip is not None:
                    hops += 1
                    if skip["label"] not in trail:
                        trail.append(skip["label"])
                    out.append(line(node, skip, "took its far edge", jumped=True))
                    prev_id, node = node["id"], skip
                    continue
            elif isinstance(mode, str) and mode.startswith("run:"):
                length = max(2, int(mode.split(":", 1)[1]))
                chain, rels, walked = [node], [], prev_id
                # a stub of a synset cannot host an arc, so try one fresh start before
                # settling for a single edge — otherwise "run" silently becomes "step"
                for attempt in range(2):
                    if attempt:
                        restart = self.graph.random_node(self.relations)
                        if restart is None:
                            break
                        chain, rels, walked = [restart], [], ""
                    for _ in range(length):
                        opts = [(r, c) for r, c in self.graph.edges(chain[-1])
                                if r in self.relations and c["id"] != walked]
                        if not opts:
                            break
                        rel, nxt = RNG.choice(opts)
                        rels.append(rel)
                        walked, chain = chain[-1]["id"], chain + [nxt]
                    if len(chain) > 2:
                        break
                if len(chain) > 2:
                    names = " → ".join(c["label"] for c in chain)
                    out.append(f"{names} · ran {len(chain) - 1} edges "
                               f"({', '.join(sorted(set(rels)))})")
                    prev_id, node = chain[-2]["id"], chain[-1]
                    continue
            elif mode == "far":
                skip = far_fresh(node, avoid=[prev_id])
                if skip is None:
                    # `outer` promises distance, and a neighbour step is the one thing it must
                    # not do. When the far search comes back empty — a synset with no usable
                    # rim, or a pool that is all visited — restart from somewhere else and say
                    # so, in the same words a dead end already uses.
                    # Two or three draws, because `random_node` can land on the node the
                    # walk is standing on and one unlucky draw is not a dead graph.
                    restart = None
                    for _ in range(3):
                        drew = self.graph.random_node(self.relations)
                        if drew is not None and drew["id"] != node["id"]:
                            restart = drew
                            break
                    if restart is None:
                        out.append(f"{node['label']} · nothing far from here — the walk stops")
                        break
                    hops += 1
                    if restart["label"] not in trail:
                        trail.append(restart["label"])
                    remember(restart)
                    out.append(f"{node['label']} → {restart['label']} "
                               f"({restart['pos'] or 'thing'}) · picks up again after a dead end"
                               + back(jumped=True) + visited(restart))
                    prev_id, node = node["id"], restart
                    continue
                hops += 1
                if skip["label"] not in trail:
                    trail.append(skip["label"])
                out.append(line(node, skip, "took its far edge", jumped=True))
                prev_id, node = node["id"], skip
                continue
            options = [(rel, n) for rel, n in self.graph.edges(node) if rel in self.relations]
            if not options:
                # a dead end is not the end of the walk unless the graph is exhausted.
                # The restart is a hop and says so: a diagnostic line in the material
                # ("dead end — no hyponym edge") reads to a turn like a concept that arrived.
                restart = self.graph.random_node(self.relations)
                if restart is None or restart["id"] == node["id"]:
                    out.append(f"{node['label']} · no {', '.join(self.relations)} edge — the walk stops")
                    break
                hops += 1
                if restart["label"] not in trail:
                    trail.append(restart["label"])
                remember(restart)
                out.append(f"{node['label']} → {restart['label']} "
                           f"({restart['pos'] or 'thing'}) · picks up again after a dead end"
                           + back(jumped=True) + visited(restart))
                prev_id, node = node["id"], restart
                continue
            forward = [(r, n) for r, n in options if n["id"] != prev_id] if self.avoid_backtrack else options
            if not forward:
                restart = self.graph.random_node(self.relations)
                if restart is not None and restart["id"] != node["id"]:
                    hops += 1
                    if restart["label"] not in trail:
                        trail.append(restart["label"])
                    remember(restart)
                    out.append(f"{node['label']} → {restart['label']} "
                               f"({restart['pos'] or 'thing'}) · the only edge back, so the walk "
                               f"picks up again" + back(jumped=True) + visited(restart))
                    prev_id, node = node["id"], restart
                    continue
            choice = pick([(r, n) for r, n in (forward or options)])
            rel, nxt = choice if choice else RNG.choice(forward or options)
            gloss = (nxt.get("gloss") or "").split(";")[0][:90]
            hops += 1
            if nxt["label"] not in trail:
                trail.append(nxt["label"])
            remember(nxt)
            out.append(f"{node['label']} ({node['pos'] or 'thing'}) → {nxt['label']} ({nxt['pos'] or 'thing'})"
                       f" · took its {rel}" + (f" · “{gloss}”" if gloss else "") + back()
                       + visited(nxt))
            prev_id, node = node["id"], nxt
        if out and prefix:
            out[0] = prefix + out[0]
        self._write_cursor(node["id"], prev_id, used=self._used_terms() + ([self._seed_marker.split(":", 1)[1]] if getattr(self, "_seed_marker", "") else []))
        return out

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "title": self.spec.get("title", self.name),
                "graph": self.graph_name, "relations": self.relations,
                "seed": self.seed_spec, "avoid_backtrack": self.avoid_backtrack,
                "builtin": self.name in BUILTIN}


# ------------------------------------------------------------------- registry

def cursor_path_default() -> Path:
    """A walk in a repository resumes in that repository."""
    from . import storage
    local = storage.project_dir()
    if local is not None:
        return local / "walk_cursor.json"
    return cursor_path()


def walks_dir(cursor_path: Path) -> Path:
    return cursor_path.parent / "walks"


def list_walks(cursor_path: Path | None = None) -> List[Dict[str, Any]]:
    cursor_path = cursor_path or cursor_path_default()
    out: List[Dict[str, Any]] = [GraphWalk({"name": k, **v}, cursor_path).describe()
                                 for k, v in BUILTIN.items()]
    directory = walks_dir(cursor_path)
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            try:
                spec = json.loads(path.read_text())
                spec.setdefault("name", path.stem)
                out.append(GraphWalk(spec, cursor_path).describe())
            except Exception:
                continue
    return out


#: A walk is a file in the walks directory named after it, so its name is a filename.
#: Walk names are untrusted model input. Without validation, a name containing traversal
#: segments could point at the Hermes credential file and be read, overwritten or
#: deleted. The alphabet is deliberately narrow — no dots at all, so '..' cannot be spelled.
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def normalise(name: str) -> str:
    """The name as a filename: lowercase, trimmed, spaces turned into dashes.

    `save()` has always done this, and a name that arrives from a command or a tool argument
    should mean the same file whichever door it came through.
    """
    return str(name or "").strip().lower().replace(" ", "-")


def valid_name(name: str) -> bool:
    return bool(NAME_RE.match(normalise(name)))


def _walk_file(name: str, cursor_path: Path | None = None) -> Path:
    """The one file `name` may mean. Raises rather than returning something outside the dir."""
    key = normalise(name)
    if not NAME_RE.match(key):
        raise ValueError(
            f"walk names are lowercase letters, digits, '-' and '_', up to 64 characters "
            f"(got {name!r})")
    directory = walks_dir(cursor_path or cursor_path_default()).resolve()
    path = (directory / f"{key}.json").resolve()
    if not path.is_relative_to(directory):
        raise ValueError(f"walk name {name!r} resolves outside {directory}")
    if path.parent != directory:
        raise ValueError(f"walk name {name!r} is not a file in {directory}")
    return path


def names(cursor_path: Path | None = None) -> List[str]:
    """Every walk a person can name: the built-ins, then any saved beside them."""
    cursor_path = cursor_path or cursor_path_default()
    seen: List[str] = []
    for walk in list_walks(cursor_path):
        name = str(walk.get("name") or "")
        if name and name not in seen:
            seen.append(name)
    return seen


def get(name: str, cursor_path: Path | None = None) -> GraphWalk:
    cursor_path = cursor_path or cursor_path_default()
    name = str(name or "").strip().lower() or "wander"
    if name in BUILTIN:
        return GraphWalk({"name": name, **BUILTIN[name]}, cursor_path)
    path = _walk_file(name, cursor_path)
    if path.exists():
        spec = json.loads(path.read_text())
        spec.setdefault("name", name)
        return GraphWalk(spec, cursor_path)
    # A name that does not exist used to become `wander` in silence, so a typo entered a
    # state whose walk was not the one asked for and reported success. Refuse it where it
    # is resolved; the callers that pass a real name never see this.
    raise ValueError(f"no such walk: {name!r} · try: {', '.join(names(cursor_path))}")


def save(spec: Dict[str, Any], cursor_path: Path | None = None) -> Dict[str, Any]:
    cursor_path = cursor_path or cursor_path_default()
    name = str(spec.get("name") or "").strip().lower().replace(" ", "-")
    if not name:
        raise ValueError("a walk needs a name")
    if name in BUILTIN:
        raise ValueError(f"'{name}' is a built-in walk; pick another name")
    spec = dict(spec, name=name)
    if spec.get("graph") == "manual" and not spec.get("edges"):
        raise ValueError("graph 'manual' needs an 'edges' map")
    directory = walks_dir(cursor_path)
    directory.mkdir(parents=True, exist_ok=True)
    _walk_file(name, cursor_path).write_text(json.dumps(spec, indent=2))
    return GraphWalk(spec, cursor_path).describe()


def remove(name: str, cursor_path: Path | None = None) -> bool:
    cursor_path = cursor_path or cursor_path_default()
    if name in BUILTIN:
        return False
    path = _walk_file(name, cursor_path)
    if path.exists():
        path.unlink()
        return True
    return False
