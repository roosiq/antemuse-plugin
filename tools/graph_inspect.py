#!/usr/bin/env python3
"""Ask the ledger what one concept connects to.

    python3 tools/graph_inspect.py gateway
    python3 tools/graph_inspect.py gateway --text        # also show why it was noticed
    python3 tools/graph_inspect.py --top 10              # the best-connected concepts

Shows the evidence, not a summary: which sessions, which messages (ids), which commits, which
files, which concepts were served beside it, and the nearest concepts by meaning when an
embeddings file is present.

`--text` resolves message ids to short excerpts from Hermes' own store, read-only and never
stored. That is the one place a transcript is visible, and it is a diagnostic: no state reads it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os as _os
EMB = Path(_os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")).expanduser() / "antemuse" / "embeddings.json"


def when(ts: float) -> str:
    import datetime as dt
    return dt.datetime.fromtimestamp(ts).strftime("%b %-d %H:%M")


def nearest(label: str, top: int = 6) -> list:
    """Nearest concepts by meaning, from the embeddings file if one has been built."""
    if not EMB.exists():
        return []
    payload = json.loads(EMB.read_text())
    vectors = payload.get("vectors", {})
    if label not in vectors:
        return []
    mine = vectors[label]
    scored = []
    for other, vec in vectors.items():
        if other == label:
            continue
        scored.append((sum(x * y for x, y in zip(mine, vec)), other))
    scored.sort(reverse=True)
    return [{"label": o, "cosine": round(s, 3)} for s, o in scored[:top]]


def render(detail: dict, text: bool = False, meaning: int = 6) -> str:
    from core import history
    if not detail.get("ok"):
        return f"· {detail.get('reason', 'unknown concept')}"
    c = detail["concept"]
    lines = [f"{c['label']}  ({c['kind']})",
             f"  seen {c['times']}× · first {when(c['first_seen'])} · last {when(c['last_seen'])}"]

    if detail["sessions"]:
        lines.append("  sessions")
        for s in detail["sessions"][:6]:
            label = history.session_label(s["session"])
            lines.append(f"    {label}  {s['count']}×  last {when(s['at'])}")

    if detail["messages"]:
        ids = [m["id"] for m in detail["messages"][:8]]
        excerpts = {}
        if text:
            from core import history
            excerpts = history.message_excerpts(ids)
        lines.append(f"  messages ({len(detail['messages'])} shown)")
        for m in detail["messages"][:8]:
            excerpt = excerpts.get(m["id"], "")
            lines.append(f"    #{m['id']}  {when(m['at'])}  {excerpt}".rstrip())

    if detail["commits"]:
        lines.append("  commits")
        for cm in detail["commits"][:6]:
            lines.append(f"    {cm['sha'][:10]}  {when(cm['at'])}")

    if detail["files"]:
        lines.append("  files")
        for f in detail["files"][:8]:
            lines.append(f"    {f}")

    if detail["siblings"]:
        lines.append("  served beside")
        lines.append("    " + ", ".join(f"{s['label']} ({s['count']})" for s in detail["siblings"][:10]))

    if detail["links"]:
        lines.append("  recorded links")
        for l in detail["links"][:6]:
            lines.append(f"    {l['a']} —{l['relation']}— {l['b']}")

    near = nearest(c["label"], top=meaning)
    if near:
        lines.append("  nearest in meaning")
        lines.append("    " + ", ".join(f"{n['label']} ({n['cosine']})" for n in near))

    return "\n".join(lines)


def top_concepts(limit: int) -> list:
    from core import history
    rows = history._query("""SELECT label, times FROM concepts WHERE kind != 'file'
                             ORDER BY times DESC LIMIT ?""", (limit,))
    return [{"label": l, "times": n} for l, n in rows]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", nargs="*", help="the concept to inspect")
    parser.add_argument("--text", action="store_true", help="resolve message ids to excerpts")
    parser.add_argument("--top", type=int, default=0, help="list the best-connected concepts")
    parser.add_argument("--json", action="store_true", help="raw detail instead of a card")
    args = parser.parse_args(argv)

    from core import history

    if args.top:
        rows = top_concepts(args.top)
        if not rows:
            print("· the ledger is empty — run a state, or let the session scan fill it")
            return 1
        for row in rows:
            print(f"{row['times']:>4}×  {row['label']}")
        return 0

    if not args.concept:
        parser.print_help()
        return 2

    missing = 0
    for term in args.concept:
        detail = history.detail(term)
        if args.json:
            print(json.dumps(detail, indent=2, sort_keys=True))
        else:
            print(render(detail, text=args.text))
            print()
        if not detail.get("ok"):
            missing += 1
    return 1 if missing == len(args.concept) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
