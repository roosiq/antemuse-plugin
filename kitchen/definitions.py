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
        "minutes": 8,
        "turns": 3,
        "tools": [],  # no tools: a walk is not research
        "directive": (
            "You are walking. You took the problem outside and left the desk. "
            "Do not plan, do not enumerate, do not use tools. Report only what you notice, "
            "in the first person, in at most 120 words. One observation must be concrete "
            "(a thing, a sound, a person, a number). If you have nothing to notice, say so."
        ),
        "contract": "observations, not conclusions",
        "residue": "walked: the problem was carried, not solved",
    },
    "daydream": {
        "label": "DAYDREAMING",
        "minutes": 10,
        "turns": 2,
        "tools": [],
        "directive": (
            "You are daydreaming: undemanding, associative, no evaluation. "
            "Produce five fragments that touch the problem sideways. No ranking, no "
            "recommendations, no next steps, no tools. Fragments may be a phrase, an image, "
            "a comparison, or a half-sentence. Do not explain them."
        ),
        "contract": "five unranked fragments, no recommendations",
        "residue": "daydreamed: five fragments kept, none chosen",
    },
    "dissociate": {
        "label": "DISSOCIATED",
        "minutes": 3,
        "turns": 2,
        "tools": None,  # tools allowed
        "directive": (
            "You are dissociated from this: describe the situation from outside it, as an "
            "operator of the system or a stranger reading the log. Never write I, me, my, we, "
            "or our. Name whose problem this actually is and who pays for it. Stay concrete; "
            "distance is not vagueness."
        ),
        "contract": "third person only, names who pays",
        "residue": "dissociated: the problem was described from outside",
    },
    "dream": {
        "label": "DREAMING",
        "minutes": 480,
        "turns": 1,
        "tools": [],
        "directive": (
            "You are dreaming on this session: no tools, no lookup. Recombine two things "
            "already present in this conversation into one proposal that neither contained. "
            "State the two sources by their own words, then the recombination in one sentence, "
            "then the smallest test. Nothing else."
        ),
        "contract": "one recombination from two sources already in the session",
        "residue": "dreamed: one recombination kept",
    },
    "doomscroll": {
        "label": "DOOMSCROLLING",
        "minutes": 20,
        "turns": 3,
        "tools": ["web_search", "web_extract", "read_file", "search_files", "browser_exec"],
        "directive": (
            "You are doomscrolling: consuming, not producing. Read but do not write, edit, or "
            "run anything. End the reply by naming exactly what you consumed and which of it "
            "you are about to copy. Be honest: the cost of this state is fixation."
        ),
        "contract": "read-only, must name what it consumed and would copy",
        "residue": "doomscrolled: fixation risk — the next idea may be borrowed",
    },
}

ALIASES = {
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
    return "\n".join(lines)
