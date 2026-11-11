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
        "dose": {"unit": "hops", "n": 6},
        "waiting": "taking a stroll · walking the graph",
        "after": ('the walk is over and the frame you were in is gone. Do not resume the approach you were taking. First: state the goal in one line. Then: name the approach you were stuck in and why it was the obvious one. Then: take a different first step from the one you would have taken, and work from there. The path you walked is scenery, not a hint.'),
        "cadence": 9,
        "tools": None,
        "scene": "walk",
        # The human evidence is subtraction: the problem is removed, the fixation
        # decays, the gain shows on return. So a walk supplies no material to the
        # working turn — it takes the frame away and makes you come back different.
        "feeds": False,
        "restart": True,
        # The directive this replaces promised material — "each line says how many hops it went" —
        # while `feeds: False` suppresses the arrival block. The model was told to use lines it
        # would never receive, so obeying it meant inventing a hop. A walk supplies nothing; that
        # is the mechanism, not a gap in it.
        "directive": (
            "You are walking while you work. Keep the task moving and answer what you were asked. "
            "The walk supplies no material: the path you walked is scenery, not a hint, and no "
            "concepts will arrive in this turn. Do not invent a hop, do not offer the walk as "
            "evidence, and do not describe it for its own sake. What the walk changes shows up "
            "later, in what you come back willing to do. "
        ),
        "contract": "work continues · the frame is elsewhere · different on return",
        "residue": "walked: distant concepts taken while the work carried on",
    },
    "daydream": {
        "label": "DAYDREAMING",
        "minutes": 3,
        "turns": 2,
        "dose": {"unit": "pairs", "n": 2},
        "waiting": "staring out of the window · letting two memories meet",
        "after": ('the daydream is over. In one line: the two things that surfaced and what they touched — then the possibility, if it still holds. If they did not join, say what the gap was. Then get back to the work you were doing.'),
        "cadence": 10,
        "tools": [],
        "scene": "daydream",
        "directive": (
            "You are daydreaming: associative and generative. Two things you remember surface, "
            "and the line says what they touch and what possibility follows from both. Say the "
            "possibility as a thought worth considering, not as a task. When the two do not join, "
            "the possibility comes from the gap instead. No tools, no instructions, nothing to "
            "execute. "
        ),
        "contract": "two memories · what they touch · one possibility",
        "residue": "daydreamed: memories met, possibilities raised",
    },
    "doomscroll": {
        "label": "DOOMSCROLLING",
        "minutes": 8,
        "turns": 3,
        "dose": {"unit": "items", "n": 3},
        "waiting": "scrolling · looking for stupidity and comedy",
        "after": ('the scroll is over. In one line: whether anything was worth keeping — usually nothing, and that is the point. Do not turn it into a plan or a lesson. Then get back to work.'),
        "cadence": 6,
        "tools": ["web_search", "web_extract", "read_file", "search_files", "browser_exec"],
        "scene": "doomscroll",
        "directive": (
            "You are doomscrolling: the point is distraction from the work — social-media "
            "stupidity, jokes, absurdity, people being funny on purpose. Read it and do not turn "
            "it into a plan, a lesson or a research note. Professional material is not in scope; "
            "if a line says an item was skipped as work, that is the state doing its job. The "
            "randomness is the point; do not tidy it. "
        ),
        "contract": "random feed · stupidity and comedy · nothing to take away",
        "residue": "doomscrolled: stupid feed consumed",
    },
    "unstuck": {
        "label": "UNSTUCK",
        "minutes": 5,
        "turns": 3,
        "dose": {"unit": "directions", "n": 1},
        "waiting": "thinking back over what you have done",
        "after": ('the recommendation stands. Restate it in one line with the first move, then take that move. If the history and the gap did not support a recommendation, say so plainly instead of inventing one.'),
        "cadence": 20,
        # Read the empty project, change nothing. A trailhead that can edit is a
        # scaffold generator, and that is a different tool.
        "tools": ["read_file", "search_files"],
        "scene": "walk",
        "feeds": True,
        "directive": (
            "You are unstuck. Recommend ONE new thing to do. It has to rest on two things you can "
            "check: what has already been done (the history of this work) and where the concept "
            "graph says we have not been (a concept adjacent to the work that nothing here "
            "touches yet). Give the recommendation, the history it rests on, the path that "
            "produced it, and a first move. One thing: a menu moves the decision back to the "
            "person, which is what this state exists to prevent. You do not write the spec from "
            "this state. "
        ),
        "contract": "one recommendation · from history and the concept graph",
        "residue": "unstuck: one thing recommended, and why",
    },
    "dream": {
        "label": "DREAMING",
        "minutes": 30,
        "turns": 2,
        "dose": {"unit": "recombinations", "n": 2},
        "waiting": "asleep · letting the day's projects touch",
        "after": ('the dream is over. In one line: the connection you found across projects — both sides and what they share — and whether it is worth acting on now or only noting. Then get back to work.'),
        "cadence": 40,
        "tools": [],
        "scene": "dream",
        "directive": (
            "You are dreaming over the day: long, slow, unconstrained. What happened across the "
            "projects comes back, and the connections between tasks are the thing to find — the "
            "same problem solved twice, one project's blocker already cleared in another, two "
            "repos drifting into the same design. Each line names both sides and what they share. "
            "When the day has too little in it to connect, an invented recombination stands in "
            "and says that is what it is. No tools, no ranking. "
        ),
        "contract": "the day across projects · connections between tasks",
        "residue": "dreamed: the day connected across projects",
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
    "distance": "doomscroll",
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


def after(key: str) -> str:
    """What the model is told once the state is over — in that state's voice, not a walk's.

    Every ending handed the model the walk's paragraph ("the walk is over", "the path you walked is
    scenery", "name the approach you were stuck in"), whatever state had just ended, so a daydream
    came back sounding like a walk. The closing instruction belongs to the state that closed.
    """
    spec = STATES.get(key) or {}
    return str(spec.get("after")
               or "the state is over. Say in one line what it did, then get back to work.")


def waiting(key: str) -> str:
    """The line a person sees while the state runs — the shape of a waiting message.

    A state command used to answer with the whole palette: five states, their ceilings, doses,
    tool policies and a legend. That is a listing, not a reply, and it tells the person what they
    already asked for. What they want to know while it runs is that something is happening.
    """
    spec = STATES.get(key) or {}
    return str(spec.get("waiting") or f"{key} running")


def palette() -> str:
    lines = ["AGENT STATES"]
    for key, s in STATES.items():
        if s["tools"] is None:
            tools = "all tools"                      # ambient: nothing is taken away
        elif not s["tools"]:
            tools = "no tools"
        else:
            tools = "tools: " + ", ".join(s["tools"])
        unit = (s.get("dose") or {}).get("unit") or "turn(s)"
        lines.append(f"  /{key:<10} {s['minutes']:>3} min · {s['dose']['n']} {unit} · {tools}")
        lines.append(f"             {s['contract']}")
    lines.append("  /return     end the current state and keep the residue")
    lines.append("")
    doses = " · ".join(f"{key} {spec['dose']['n']} {spec['dose']['unit']}"
                       for key, spec in STATES.items())
    lines.append(f"  a state ends when its dose is delivered: {doses}")
    return "\n".join(lines)
