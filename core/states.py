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
        "minutes": 3,
        "turns": 6,
        # the dose is turns worked with the frame elsewhere; the walk supplies nothing
        "dose": {"unit": "turns", "n": 6},
        "cadence": 9,
        "tools": None,
        "scene": "walk",
        # The human evidence is subtraction: the problem is removed, the fixation
        # decays, the gain shows on return. So a walk supplies no material to the
        # working turn — it takes the frame away and makes you come back different.
        "feeds": False,
        "restart": True,
        "directive": (
            "You are walking while you work. Keep the task moving and answer what you were asked. "
            "The walk does not supply ideas and will not hand you anything to react to: it is the "
            "time away from the frame, not new material. Do not describe the walk, do not pad a "
            "reply with it, and do not wait for it to tell you something."
        ),
        "contract": "work continues · the frame is elsewhere",
        "residue": "walked: a path taken while the work carried on",
    },
    "daydream": {
        "label": "DAYDREAMING",
        "minutes": 3,
        "turns": 2,
        "dose": {"unit": "pairs", "n": 2},
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
        "dose": {"unit": "items", "n": 3},
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
    "unstuck": {
        "label": "UNSTUCK",
        "minutes": 5,
        "turns": 3,
        "dose": {"unit": "directions", "n": 1},
        "cadence": 20,
        # Read the empty project, change nothing. A trailhead that can edit is a
        # scaffold generator, and that is a different tool.
        "tools": ["read_file", "search_files"],
        "scene": "walk",
        "feeds": True,
        "directive": (
            "You are in a greenfield: an empty repository, no spec, no conventions to inherit. "
            "Look at what is actually there — the files, the first commit, what nobody has decided "
            "yet — then name ONE direction: what this product is, and which spec file that sentence "
            "becomes (or which file it creates). One direction, stated plainly, in the present "
            "tense: the promise, not the roadmap. No menu, no ranked options, no summary of the "
            "repo back to the person. If the direction is wrong they will say so; five of them are "
            "unusable. You do not write the spec from this state."
        ),
        "contract": "one direction · the promise, and where it goes",
        "residue": "unstuck: a direction named, and where it goes",
    },
    "dream": {
        "label": "DREAMING",
        "minutes": 30,
        "turns": 2,
        "dose": {"unit": "recombinations", "n": 2},
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
    "greenfield": "unstuck",
    "start": "unstuck",
    "new_project": "unstuck",
    "trailhead": "unstuck",
    "zero": "unstuck",
    "day-one": "unstuck",
}


def resolve(name: str) -> str | None:
    key = (name or "").strip().lower().replace(" ", "_")
    key = ALIASES.get(key, key)
    return key if key in STATES else None


def palette() -> str:
    lines = ["AGENT STATES"]
    for key, s in STATES.items():
        if s["tools"] is None:
            tools = "all tools"                      # ambient: nothing is taken away
        elif not s["tools"]:
            tools = "no tools"
        else:
            tools = "tools: " + ", ".join(s["tools"])
        lines.append(f"  /{key:<10} {s['minutes']:>3} min · {s['turns']} turn(s) · {tools}")
        lines.append(f"             {s['contract']}")
    lines.append("  /return     end the current state and keep the residue")
    lines.append("")
    doses = " · ".join(f"{key} {spec['dose']['n']} {spec['dose']['unit']}"
                       for key, spec in STATES.items())
    lines.append(f"  a state ends when its dose is delivered: {doses}")
    return "\n".join(lines)
