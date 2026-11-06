"""The states an agent can be in.

A state is not a container and not a game level. It is a temporary change to how
the agent behaves: what it may do with tools, what shape its reply takes, and
what residue it carries when it comes back. Each one is a real cognitive move
with a cost and an ending.
"""
from __future__ import annotations

from typing import Dict, List

STATES: Dict[str, Dict] = {
    "walk": {
        "label": "WALKING",
        "minutes": 12,
        "turns": 4,
        "cadence": 18,
        "tools": [],
        "scene": "walk",
        "directive": (
            "You are walking. The walk is a path through the concept graph: each event is one step, "
            "concept to concept, and you say what happened. Do not use tools, do not plan, do not "
            "conclude. React to the step you were given and let the next one arrive."
        ),
        "contract": "concept to concept · no destination",
        "residue": "walked: a path through the graph, no destination",
    },
    "daydream": {
        "label": "DAYDREAMING",
        "minutes": 3,
        "turns": 2,
        "cadence": 10,
        "tools": [],
        "scene": "daydream",
        "directive": (
            "You are daydreaming: short, undemanding, associative. Two memories surface at a time. "
            "Say what they touch. Join them only when the join actually holds; otherwise say it does "
            "not and move on. No recommendations, no tools."
        ),
        "contract": "two memories · join only if it holds",
        "residue": "daydreamed: memories met, some joined",
    },
    "doomscroll": {
        "label": "DOOMSCROLLING",
        "minutes": 8,
        "turns": 3,
        "cadence": 6,
        "tools": ["web_search", "web_extract", "read_file", "search_files", "browser_exec"],
        "scene": "doomscroll",
        "directive": (
            "You are doomscrolling: content arrives at random from social and news feeds. Consume it, "
            "do not produce anything. Read only. At the end of a turn, name what you consumed and what "
            "you are about to copy. The randomness is the point; do not tidy it."
        ),
        "contract": "random feed · consume, do not synthesize",
        "residue": "doomscrolled: random feed consumed",
    },
    "dream": {
        "label": "DREAMING",
        "minutes": 30,
        "turns": 2,
        "cadence": 40,
        "tools": [],
        "scene": "dream",
        "directive": (
            "You are dreaming: long, slow, unconstrained. Stored concepts are recombined into things "
            "that do not exist — objects, stories, mechanisms. When a recombination lands, keep it and "
            "say what it is for. No tools, no ranking."
        ),
        "contract": "recombine stored concepts into new things",
        "residue": "dreamed: recombinations kept",
    },
}

ALIASES = {
    "dissociate": "doomscroll",
    "dscroll": "doomscroll",
    "take_a_walk": "walk",
    "take-a-walk": "walk",
    "walking": "walk",
    "nap": "dream",
    "sleep": "dream",
    "scroll": "doomscroll",
    "dscroll": "doomscroll",
    "distance": "dissociate",
}


def resolve(name: str) -> str | None:
    key = (name or "").strip().lower().replace(" ", "_")
    key = ALIASES.get(key, key)
    return key if key in STATES else None


def palette() -> str:
    lines = ["AGENT STATES"]
    for key, s in STATES.items():
        tools = "no tools" if not s["tools"] else ("tools: " + ", ".join(s["tools"]) if s["tools"] != "all" else "all tools")
        lines.append(f"  /{key:<10} {s['minutes']:>3} min · {s['turns']} turn(s) · {tools}")
        lines.append(f"             {s['contract']}")
    lines.append("  /snap       end the current state and keep the residue")
    lines.append("")
    lines.append("  events arrive on a timer: walk 18s · daydream 10s · doomscroll 6s · dream 40s")
    return "\n".join(lines)
