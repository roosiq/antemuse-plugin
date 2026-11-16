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
from typing import Any, Dict, List, Optional, Tuple, Type

# Unseeded walks retain their old entropy. A seeded generator is made per walk so
# two walks with the same cursor and seed replay the same choices.
RNG = random.SystemRandom()
ROLE_VOCABULARY = {"general", "specific", "part", "whole", "lateral", "sequence"}
MAX_GRAPH_NODES = 400
MAX_GRAPH_EDGES = 1200
WORDNET_SOURCE = "Princeton WordNet 3.0"
WORDNET_LICENCE = "WordNet License"


def _rng() -> random.Random:
    seed = os.environ.get("ANTEMUSE_GRAPH_SEED")
    return random.Random(seed) if seed is not None else RNG

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
        "roles": ["general", "specific", "part", "whole", "lateral"],
        "jump": "far",
        "seed": {"mode": "continue"},
        "avoid_backtrack": False,
    },
    "wander": {
        "title": "Wander — every WordNet edge, no direction",
        "graph": "wordnet",
        "roles": ["general", "specific", "part", "whole", "lateral"],
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
    "upward": {
        "title": "Upward — hypernyms and wholes only, toward the general",
        "graph": "wordnet",
        "roles": ["general", "whole"],
        "seed": {"mode": "continue"},
        "avoid_backtrack": False,
    },
    "downward": {
        "title": "Downward — hyponyms and parts only, toward the specific",
        "graph": "wordnet",
        "roles": ["specific", "part"],
        "seed": {"mode": "continue"},
        "avoid_backtrack": False,
    },
    "composite": {
        "title": "Composite — every navigation in one walk: run, far, vault, orbit, near",
        "graph": "wordnet",
        "roles": ["general", "specific", "part", "whole", "lateral"],
        "jump": "composite",
        "samples": 48,
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
    "vault": {
        "title": "Vault — two far jumps per step: the graph it lands in is not the one it left",
        "graph": "wordnet",
        "roles": ["general", "specific", "part", "whole", "lateral"],
        "jump": "vault",
        "samples": 64,
        "seed": {"mode": "continue"},
        "avoid_backtrack": False,
    },
    "run3": {
        "title": "Run3 — three adjacent edges reported as one arc, so the step covers distance",
        "graph": "wordnet",
        "roles": ["general", "specific", "part", "whole", "lateral"],
        "jump": "run:3",
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
    "orbit": {
        "title": "Orbit — one near edge, then one far jump, alternating",
        "graph": "wordnet",
        "roles": ["general", "specific", "part", "whole", "lateral"],
        "jump": "orbit",
        "samples": 48,
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
    "lateral": {
        "title": "Lateral — similars, also-sees and opposites, never up or down",
        "graph": "wordnet",
        "roles": ["lateral"],
        "seed": {"mode": "continue"},
        "avoid_backtrack": True,
    },
}


# --------------------------------------------------------------------- graphs

class GraphLoadError(Exception):
    """A named, non-fatal graph failure that a walk can say in its own voice."""
    def __init__(self, mode: str, detail: str = "") -> None:
        self.mode, self.detail = mode, detail
        super().__init__(f"{mode}: {detail}")


class Graph:
    """A declared walk-graph contract. Providers never rely on ``hasattr``."""
    name = "graph"
    relations: Dict[str, str] = {}
    capabilities: set[str] = set()
    size: Dict[str, int] = {"nodes": 0, "edges": 0}
    source = ""
    licence = ""

    def node(self, key: str, label: str | None = None, pos: str = "", gloss: str = "") -> Dict[str, Any]:
        return {"id": f"{self.name}:{key}", "label": label or key, "pos": pos,
                "gloss": gloss, "source": self.source, "licence": self.licence}

    def key(self, node_id: str) -> str | None:
        prefix = f"{self.name}:"
        return node_id[len(prefix):] if str(node_id).startswith(prefix) else None

    def resolve(self, word: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def random_node(self, relation_roles: Optional[set[str]] = None) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def edges(self, node: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        raise NotImplementedError

    def resume(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Pick a walk back up — including from a cursor written before ids were namespaced.

        Cursors on disk from older releases hold a bare key ("design", "carousel.n.01"). A
        namespaced id is checked first; a bare id is handed to the provider as its own key, so an
        upgrade resumes the walk it was in instead of silently starting a new one.
        """
        key = self.key(node_id)
        if key is None:
            raw = str(node_id or "").strip()
            key = raw if raw and ":" not in raw else None
        return self.resolve(key) if key else None

    def far_from(self, node: Dict[str, Any], samples: int = 32,
                 avoid: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        return None


_GLOSS_STOP = {"the", "a", "an", "of", "or", "and", "to", "in", "by", "for", "with",
               "something", "someone", "that", "this", "is", "as", "from", "act",
               "state", "quality", "being", "make", "makes", "making", "into", "its"}


def _content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", str(text).lower()) if w not in _GLOSS_STOP}


class WordNetGraph(Graph):
    name = "wordnet"
    relations = {"hypernym": "general", "hyponym": "specific", "holonym": "whole",
                 "meronym": "part", "similar": "lateral", "also": "lateral", "antonym": "lateral"}
    capabilities = {"far", "resume", "gloss", "seeds"}
    size = {"nodes": 117659, "edges": 0}
    source, licence = WORDNET_SOURCE, WORDNET_LICENCE
    SEEDS = ["walk", "dream", "light", "river", "memory", "door", "signal", "salt",
             "night", "hand", "stone", "weather"]

    def __init__(self, **_kwargs: Any) -> None:
        self._wn = None
        self.rng = _rng()

    def wn(self):
        if self._wn is None:
            try:
                from nltk.corpus import wordnet as wn
                # Force a real lookup here so missing corpus data has a named failure.
                wn.synsets("walk")
                self._wn = wn
            except Exception as exc:
                raise GraphLoadError("unavailable", "WordNet data is unavailable") from exc
        return self._wn

    def _from_synset(self, syn: Any) -> Dict[str, Any]:
        return self.node(syn.name(), syn.lemma_names()[0].replace("_", " "), syn.pos(), syn.definition())

    def resolve(self, word: str) -> Optional[Dict[str, Any]]:
        try:
            syns = self.wn().synsets(str(word).replace(" ", "_"))
            return self._from_synset(syns[0]) if syns else None
        except GraphLoadError:
            raise
        except Exception:
            return None

    def random_node(self, relation_roles: Optional[set[str]] = None) -> Optional[Dict[str, Any]]:
        pool: List[Dict[str, Any]] = []
        for word in self.SEEDS:
            node = self.resolve(word)
            if node is None:
                continue
            if relation_roles and not any(self.relations.get(rel) in relation_roles for rel, _ in self.edges(node)):
                continue
            pool.append(node)
        return self.rng.choice(pool) if pool else None

    def resume(self, node_id: str) -> Optional[Dict[str, Any]]:
        # Legacy cursors held bare synset ids; accepting those lets old walks restart safely.
        key = self.key(node_id) or str(node_id)
        try:
            syn = self.wn().synset(key)
            return self._from_synset(syn) if syn is not None else None
        except GraphLoadError:
            raise
        except Exception:
            return None

    def edges(self, node: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        key = self.key(str(node.get("id") or "")) or str(node.get("id") or "")
        try:
            syn = self.wn().synset(key)
        except GraphLoadError:
            raise
        except Exception:
            return []
        if syn is None:
            return []
        probes = {
            "hypernym": lambda s: s.hypernyms(), "hyponym": lambda s: s.hyponyms(),
            "holonym": lambda s: s.part_holonyms() + s.member_holonyms() + s.substance_holonyms(),
            "meronym": lambda s: s.part_meronyms() + s.member_meronyms() + s.substance_meronyms(),
            "similar": lambda s: getattr(s, "similar_tos", lambda: [])(), "also": lambda s: s.also_sees(),
            "antonym": lambda s: [a.synset() for l in s.lemmas() for a in l.antonyms()],
        }
        out: List[Tuple[str, Dict[str, Any]]] = []
        for rel, fn in probes.items():
            try:
                out.extend((rel, self._from_synset(target)) for target in fn(syn) if target is not None)
            except Exception:
                continue
        return out

    def rim(self, node: Dict[str, Any], depth: int = 2, budget: int = 400) -> List[Dict[str, Any]]:
        seen, frontier, out = {node["id"]}, [node], []
        for level in range(1, max(1, depth) + 1):
            nxt = []
            for cur in frontier:
                for _rel, child in self.edges(cur):
                    if child["id"] in seen:
                        continue
                    seen.add(child["id"]); nxt.append(child)
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
        skip = set(avoid or []) | {node["id"]}
        cands = [c for c in self.rim(node) if c["id"] not in skip]
        if not cands:
            return None
        key = self.key(node["id"]) or node["id"]
        try:
            cur = self.wn().synset(key)
        except Exception:
            cur = None
        pool = cands if len(cands) <= samples else self.rng.sample(cands, samples)
        fresh = [c for c in pool if not (_content_words(c.get("gloss") or "") & _content_words(node.get("gloss") or ""))]
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for cand in fresh or pool:
            try:
                cand_syn = self.wn().synset(self.key(cand["id"]) or cand["id"])
                sim = cur.path_similarity(cand_syn) if cur and cand_syn else None
            except Exception:
                sim = None
            scored.append((0.0 if sim is None else float(sim), cand))
        scored.sort(key=lambda item: item[0])
        return self.rng.choice(scored[:max(1, min(6, len(scored)))])[1]


class ManualGraph(Graph):
    """A walk-local adjacency graph retained for backwards-compatible user walks."""
    name = "manual"
    relations = {"next": "sequence"}
    capabilities = {"resume", "gloss", "seeds"}
    source, licence = "User-authored walk", "User supplied"

    def __init__(self, edges: Dict[str, List[str]] | None = None,
                 labels: Optional[Dict[str, Dict[str, str]]] = None, **_kwargs: Any) -> None:
        self.edges_map = {str(k): list(v) for k, v in (edges or {}).items()}
        self.labels = labels or {}
        self.size = {"nodes": len(self.edges_map), "edges": sum(len(v) for v in self.edges_map.values())}
        self.rng = _rng()

    def _mk(self, key: str) -> Dict[str, Any]:
        meta = self.labels.get(key, {})
        return self.node(key, meta.get("label", key), meta.get("pos", ""), meta.get("gloss", ""))

    def resolve(self, word: str) -> Optional[Dict[str, Any]]:
        key = self.key(str(word)) or str(word).strip().lower()
        return self._mk(key) if key in self.edges_map else None

    def random_node(self, relation_roles: Optional[set[str]] = None) -> Optional[Dict[str, Any]]:
        choices = [key for key, values in self.edges_map.items()
                   if values and (not relation_roles or "sequence" in relation_roles)]
        return self._mk(self.rng.choice(choices)) if choices else None

    def edges(self, node: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        key = self.key(str(node.get("id") or ""))
        return [("next", self._mk(str(n))) for n in self.edges_map.get(key or "", [])]


class CorpusGraph(Graph):
    """An explicit, local corpus graph; no co-occurrence or runtime derivation."""
    name = "corpus"
    capabilities = {"resume", "gloss", "seeds"}

    def __init__(self, corpus_name: str = "", **_kwargs: Any) -> None:
        self.rng = _rng()
        self.corpus_name = str(corpus_name or "").strip()
        if not self.corpus_name:
            raise GraphLoadError("unavailable", "no corpus graph named")
        path = _data_dir() / "graphs" / f"{self.corpus_name}.json"
        try:
            raw = json.loads(path.read_text())
        except Exception as exc:
            raise GraphLoadError("unavailable", f"corpus '{self.corpus_name}' is unavailable") from exc
        if not isinstance(raw, dict) or str(raw.get("name") or "") != self.corpus_name or not raw.get("source") or not raw.get("licence"):
            raise GraphLoadError("unavailable", f"corpus '{self.corpus_name}' needs matching name, source and licence")
        self.source, self.licence = str(raw["source"]), str(raw["licence"])
        nodes, edges = raw.get("nodes") or {}, raw.get("edges") or []
        if not isinstance(nodes, dict) or not isinstance(edges, list):
            raise GraphLoadError("unavailable", f"corpus '{self.corpus_name}' has invalid explicit edges")
        if len(nodes) > MAX_GRAPH_NODES or len(edges) > MAX_GRAPH_EDGES:
            raise GraphLoadError("too_large", f"corpus '{self.corpus_name}' exceeds {MAX_GRAPH_NODES} nodes or {MAX_GRAPH_EDGES} edges")
        self.nodes = {str(key): (meta if isinstance(meta, dict) else {}) for key, meta in nodes.items()}
        self.edges_map: Dict[str, List[Tuple[str, str]]] = {key: [] for key in self.nodes}
        self.relations = {}
        for edge in edges:
            if not isinstance(edge, dict):
                raise GraphLoadError("unavailable", "corpus edges must be explicit objects")
            src, dst, relation = str(edge.get("from") or ""), str(edge.get("to") or ""), str(edge.get("relation") or "")
            role = str(edge.get("role") or ("sequence" if relation in {"next", "follows", "contains"} else "lateral"))
            if src not in self.nodes or dst not in self.nodes or not relation or role not in ROLE_VOCABULARY:
                raise GraphLoadError("unavailable", "corpus edge is invalid")
            self.edges_map[src].append((relation, dst)); self.relations[relation] = role
        self.size = {"nodes": len(self.nodes), "edges": len(edges)}
        if not self.nodes or not any(self.edges_map.values()):
            raise GraphLoadError("empty", f"corpus '{self.corpus_name}' has no usable edges")

    def _mk(self, key: str) -> Dict[str, Any]:
        meta = self.nodes[key]
        return self.node(key, str(meta.get("label") or key), str(meta.get("pos") or ""), str(meta.get("gloss") or ""))

    def resolve(self, word: str) -> Optional[Dict[str, Any]]:
        key = self.key(str(word)) or str(word).strip()
        if key not in self.nodes:
            key = next((k for k, meta in self.nodes.items() if str(meta.get("label") or k).lower() == str(word).lower()), "")
        return self._mk(key) if key in self.nodes else None

    def random_node(self, relation_roles: Optional[set[str]] = None) -> Optional[Dict[str, Any]]:
        choices = [key for key, edges in self.edges_map.items() if any(
            not relation_roles or self.relations[relation] in relation_roles for relation, _ in edges)]
        return self._mk(self.rng.choice(choices)) if choices else None

    def edges(self, node: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        key = self.key(str(node.get("id") or ""))
        return [(relation, self._mk(dst)) for relation, dst in self.edges_map.get(key or "", [])]


GRAPH_REGISTRY: Dict[str, Type[Graph]] = {}
GRAPHS = GRAPH_REGISTRY  # compatibility alias; providers now register through the validation path.


def register_graph(name: str, provider: Type[Graph]) -> None:
    key = str(name).strip().lower()
    if not key or key != getattr(provider, "name", None):
        raise ValueError("a graph provider name must match its registry key")
    GRAPH_REGISTRY[key] = provider


def unregister_graph(name: str) -> None:
    GRAPH_REGISTRY.pop(str(name).strip().lower(), None)


def _unknown_graph(name: str) -> ValueError:
    return ValueError(f"unknown graph '{name}' (known: {', '.join(GRAPH_REGISTRY)})")


def make_graph(name: str, **kwargs: Any) -> Graph:
    key = str(name or "wordnet").strip().lower()
    provider = GRAPH_REGISTRY.get(key)
    if provider is None:
        raise _unknown_graph(key)
    return provider(**kwargs)


for _provider in (WordNetGraph, ManualGraph, CorpusGraph):
    register_graph(_provider.name, _provider)


# ----------------------------------------------------------------------- walk

class GraphWalk:
    """One walkable graph plus the policy that decides each step."""

    def __init__(self, spec: Dict[str, Any], cursor_path: Path):
        self.spec = dict(spec)
        self.name = str(spec.get("name") or "wander")
        self.cursor_path = cursor_path
        self.graph_name = str(spec.get("graph", "wordnet")).lower()
        self.rng = _rng()
        try:
            self.graph = make_graph(self.graph_name, edges=spec.get("edges", {}), labels=spec.get("labels"),
                                    corpus_name=spec.get("corpus") or spec.get("name", ""))
            self.graph_error: GraphLoadError | None = None
        except GraphLoadError as exc:
            self.graph = None  # loaded lazily enough that a state can say the failure, not crash
            self.graph_error = exc
        if self.graph is not None:
            self.roles = set(spec.get("roles") or [])
            if self.roles - ROLE_VOCABULARY:
                raise ValueError(f"unknown graph roles: {', '.join(sorted(self.roles - ROLE_VOCABULARY))}")
            self.relations = list(spec.get("relations") or [relation for relation, role in self.graph.relations.items()
                                                             if not self.roles or role in self.roles])
        else:
            self.roles = set(spec.get("roles") or [])
            self.relations = list(spec.get("relations") or [])
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
    def _failure(self) -> str:
        if self.graph_error is not None:
            return f"walk unavailable · graph '{self.graph_name}' {self.graph_error.mode} · {self.graph_error.detail}"
        if self.jump in {"far", "vault", "orbit", "composite"} and (self.graph is None or "far" not in self.graph.capabilities):
            return f"walk unavailable · graph '{self.graph_name}' cannot jump (no_far) · use wander or supply far_from"
        return ""

    def start_node(self) -> Optional[Dict[str, Any]]:
        if self.graph is None:
            return None
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
                    or self.graph.random_node(self.roles))
        if mode == "random":
            return self.graph.random_node(self.roles)
        # `continue` with no cursor, and the new `project` mode, draw from the mix:
        # 50 % the repository, 30 % the conversation, 20 % deliberately unrelated.
        first_usable = None
        for candidate in self._seed_candidates():
            resolved = candidate
            if resolved is not None:
                if "far" not in self.graph.capabilities or self.jump not in ("far", "vault", "orbit", "composite", "run:3"):
                    self._seed_marker = getattr(self, "_pending_marker", "")
                    return resolved
                # A jump walk needs somewhere to jump to. A seed whose rim is empty ends the walk
                # on its first line ("nothing far from here"), which is honest but useless when the
                # next candidate would have walked — so take the first seed that can actually move.
                if self.graph.far_from(resolved, samples=32, avoid=[]) is not None:
                    self._seed_marker = getattr(self, "_pending_marker", "")
                    return resolved
                if first_usable is None:
                    first_usable = resolved
        if first_usable is not None:
            self._seed_marker = getattr(self, "_pending_marker", "")
            return first_usable
        return self.graph.random_node(self.roles)

    def _seed_candidates(self):
        """The seeded start nodes, in tier order, each carrying the marker of the seed it came from.

        A candidate can be a ledger id ("project:hermes"); the term after the namespace is what a
        graph can resolve. A candidate that resolves nothing is skipped rather than ending the walk.
        """
        self._pending_marker = ""
        graph = self.graph
        if graph is None:
            return
        try:
            from . import seeding
            for seed in seeding.candidates("walk", when=time.time(),
                                           exclude=self._used_terms(),
                                           goal=str((self.seed_spec or {}).get("goal") or "")):
                resolved = graph.resolve(seed["term"])
                if resolved is None and ":" in str(seed["term"]):
                    resolved = graph.resolve(str(seed["term"]).rsplit(":", 1)[-1])
                if resolved is not None:
                    self._pending_marker = seeding.marker(seed)
                    yield resolved
        except Exception:
            return

    def _used_terms(self) -> List[str]:
        try:
            return [str(x) for x in (self._read_cursor().get("used") or [])][-12:]
        except Exception:
            return []

    def step(self, steps: int = 1) -> List[str]:
        self._seed_marker = ""
        failure = self._failure()
        if failure:
            return [failure]
        node = self.start_node()
        if node is None:
            return [f"walk unavailable · graph '{self.graph_name}' empty · has no starting node"]
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
            return self.rng.choice(fresh) if fresh else self.rng.choice(cands)

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
                               session=str(origin.get("session_id") or ""), kind=self.graph_name,
                               key=str(node_.get("id") or ""), provenance_source=str(node_.get("source") or ""),
                               licence=str(node_.get("licence") or ""))
            except Exception:
                pass

        def line(a, b, how, jumped: bool = False):
            gloss = (b.get("gloss") or "").split(";")[0][:90]
            remember(b)
            graph_tag = f" · {self.graph_name}" if self.graph_name != "wordnet" else ""
            return (f"{a['label']} ({a['pos'] or 'thing'}) → {b['label']} "
                    f"({b['pos'] or 'thing'}) · {how}{graph_tag}"
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
                        rel, nxt = self.rng.choice(opts)
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
            rel, nxt = choice if choice else self.rng.choice(forward or options)
            gloss = (nxt.get("gloss") or "").split(";")[0][:90]
            hops += 1
            if nxt["label"] not in trail:
                trail.append(nxt["label"])
            remember(nxt)
            out.append(f"{node['label']} ({node['pos'] or 'thing'}) → {nxt['label']} ({nxt['pos'] or 'thing'})"
                       f" · took its {rel}" + (f" · {self.graph_name}" if self.graph_name != "wordnet" else "")
                       + (f" · “{gloss}”" if gloss else "") + back()
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


def _graph_requirements(spec: Dict[str, Any]) -> None:
    graph_name = str(spec.get("graph") or "wordnet").strip().lower()
    if graph_name not in GRAPH_REGISTRY:
        raise _unknown_graph(graph_name)
    jump = spec.get("jump")
    if jump in {"far", "vault", "orbit", "composite"} and "far" not in GRAPH_REGISTRY[graph_name].capabilities:
        raise ValueError(f"graph '{graph_name}' cannot jump (no_far) · use wander or supply far_from")


def entry_error(name: str, cursor_path: Path | None = None) -> str:
    """The capability failure an entry point can return before it starts a state."""
    try:
        walk = get(name, cursor_path)
    except (ValueError, GraphLoadError) as exc:
        return str(exc)
    return walk._failure().replace("walk unavailable · ", "")


def save(spec: Dict[str, Any], cursor_path: Path | None = None, validate: bool = True) -> Dict[str, Any]:
    cursor_path = cursor_path or cursor_path_default()
    name = str(spec.get("name") or "").strip().lower().replace(" ", "-")
    if not name:
        raise ValueError("a walk needs a name")
    if name in BUILTIN:
        raise ValueError(f"'{name}' is a built-in walk; pick another name")
    spec = dict(spec, name=name)
    if validate:
        _graph_requirements(spec)
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
