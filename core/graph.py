"""The concept ledger as a graph: concepts, the sessions they were met in, the projects and
the files they touch.

Three questions this answers that the tables alone do not:

- **which concepts were met in the same move** (co-served) — the actual edges a walk or a
  dream could traverse;
- **which concepts came from which session** — provenance, so a concept can be traced back to
  the conversation it was met in without reading that conversation;
- **which files a concept is attached to** — the artifact side of the graph, from the file
  names the repositories' own commits touched.

Read-only. Bounded. A missing or broken ledger returns an empty graph, never an exception:
this is a diagnostic, not a dependency.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, Tuple

MAX_NODES = 400
MAX_EDGES = 1200


def _rows(history, sql: str, args: Iterable[Any] = ()) -> List[Tuple]:
    try:
        return history._query(sql, args)
    except Exception:
        return []


def session_label(session: str) -> str:
    """`20261108_091834_aa6c8db0` is an id, not a label. A person reads a date."""
    import datetime as _dt
    raw = (session or "").strip()
    for fmt in ("%Y%m%d_%H%M%S", "%Y-%m-%d"):
        try:
            stamp = _dt.datetime.strptime(raw[:len("20261108_091834")], fmt)
            return stamp.strftime("%b %-d %H:%M")
        except Exception:
            continue
    return raw.replace("_", " ")[:14] or "session"


def _tokens(text: str) -> Set[str]:
    import re
    return {w for w in re.findall(r"[a-z][a-z0-9\-]{2,}", (text or "").lower())}


def snapshot(limit: int = MAX_NODES, max_edges: int = MAX_EDGES) -> Dict[str, Any]:
    """Nodes and edges, capped. Node ids are `kind:key` so the same thing is never two nodes."""
    from . import history

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    seen_edges: Set[Tuple[str, str, str]] = set()

    def node(kind: str, key: str, label: str) -> str:
        nid = f"{kind}:{key}"
        if nid not in nodes and len(nodes) < limit:
            nodes[nid] = {"id": nid, "kind": kind, "key": key, "label": label}
        return nid

    def edge(a: str, b: str, relation: str, weight: int = 1) -> None:
        if len(edges) >= max_edges or a == b:
            return
        key = (a, b, relation)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append({"source": a, "target": b, "relation": relation, "weight": weight})

    # a picture of one kind of thing is not a picture of a graph: give each kind a quota
    q_concepts = max(8, int(limit * 0.50))
    q_sessions = max(4, int(limit * 0.20))
    q_files = max(4, int(limit * 0.25))
    concepts = _rows(history, """SELECT id, kind, key, label, times FROM concepts
                                 WHERE kind != 'file'
                                 ORDER BY times DESC, last_seen DESC LIMIT ?""", (q_concepts,))
    by_id = {}
    for cid, kind, key, label, times in concepts:
        by_id[cid] = node("concept", f"{kind}:{key}", label)

    # concept -> session: provenance without the conversation. A session is a hub, so each
    # one gets a handful of spokes: a hub with eighty edges is a hairball, not provenance.
    per_session: Dict[str, int] = {}
    for cid, session, at in _rows(history, """SELECT concept_id, session, MAX(at) FROM served
                                              WHERE session != '' GROUP BY concept_id, session
                                              ORDER BY MAX(at) DESC LIMIT ?""", (max_edges,)):
        if cid not in by_id:
            continue
        if session not in per_session and sum(1 for n in nodes.values()
                                              if n["kind"] == "session") >= q_sessions:
            continue
        if per_session.get(session, 0) >= 4:
            continue
        per_session[session] = per_session.get(session, 0) + 1
        sid = node("session", session, session_label(session))
        edge(by_id[cid], sid, "served_in")

    # concept -> artifact: a file name a repository's commit touched
    files = _rows(history, """SELECT kind, key, label FROM concepts WHERE kind = 'file'
                              ORDER BY times DESC LIMIT ?""", (q_files,))
    for _kind, key, label in files:
        fid = node("file", key, label)
        project = key.split("/", 1)[0] if "/" in key else ""
        pid = node("project", project, project) if project else ""
        if pid:
            edge(fid, pid, "in_project")
        want = _tokens(label) | _tokens(key.rsplit("/", 1)[-1])
        for cid, ckind, ckey, clabel, _ in concepts:
            if want & _tokens(clabel):
                edge(by_id[cid], fid, "touched")

    # concept <-> concept: co-served in the same move of the same session
    groups = _rows(history, """SELECT session, move, GROUP_CONCAT(DISTINCT concept_id)
                               FROM served WHERE session != ''
                               GROUP BY session, move HAVING COUNT(DISTINCT concept_id) BETWEEN 2 AND 8
                               LIMIT ?""", (limit,))
    for _session, _move, ids in groups:
        members = [int(x) for x in (ids or "").split(",") if x.strip().isdigit()]
        members = [by_id[m] for m in members if m in by_id][:8]
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                edge(a, b, "co_served")

    # an edge whose endpoint did not fit under the node cap is not an edge of this graph
    known = set(nodes)
    edges = [e for e in edges if e["source"] in known and e["target"] in known]
    return {"nodes": list(nodes.values()), "edges": edges,
            "counts": {"nodes": len(nodes), "edges": len(edges)}}


def summary(graph: Dict[str, Any]) -> Dict[str, int]:
    """How many of each kind, and how many edges of each relation — the numbers a reader
    needs before trusting a picture."""
    kinds: Dict[str, int] = {}
    for n in graph.get("nodes", []):
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    rels: Dict[str, int] = {}
    for e in graph.get("edges", []):
        rels[e["relation"]] = rels.get(e["relation"], 0) + 1
    out = {f"nodes:{k}": v for k, v in sorted(kinds.items())}
    out.update({f"edges:{k}": v for k, v in sorted(rels.items())})
    return out
