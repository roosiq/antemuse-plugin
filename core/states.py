"""The five registered agent states and the separate person-driven explore mode."""
from __future__ import annotations

from typing import Dict


STATES: Dict[str, Dict] = {
    "walk": {
        "label": "WALKING",
        "turns": 6,
        "dose": {"unit": "hops", "n": 6},
        # A walk is an act, not a chore: `/walk` takes its six hops there and then and comes back
        # with the path. Pacing it by turns meant typing five filler messages to finish one walk.
        "instant": True,
        "waiting": "taking a walk · six hops, then back with the path",
        "after": (
            "the walk is over and the frame you were in is gone. Do not resume the approach "
            "you were taking. First: state the goal in one line. Then: name the approach you "
            "were stuck in and why it was the obvious one. Then: take a different first step "
            "from the one you would have taken, and work from there. The path you walked is "
            "scenery, not a hint — it is here so you can see the route you took."
        ),
        "tools": None,
        "scene": "walk",
        "feeds": False,
        "restart": True,
        "provider": "walk",
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
        "turns": 2,
        "dose": {"unit": "pairs", "n": 2},
        "waiting": "staring out of the window · letting two memories meet",
        "after": (
            "the daydream is over. In one line: the two things that surfaced and what they "
            "touched — then the possibility, if it still holds. If they did not join, say what "
            "the gap was. Then get back to the work you were doing."
        ),
        "tools": [],
        "scene": "daydream",
        "feeds": True,
        "provider": "daydream",
        "directive": (
            "You are daydreaming: associative and generative. Two of the person's own recorded "
            "turns surface; the line says what they touch and what possibility follows from both. "
            "Say the possibility as a thought worth considering, not as a task. Nothing here is "
            "an instruction and there is nothing to execute. "
        ),
        "contract": "two memories · what they touch · one possibility",
        "residue": "daydreamed: memories met, possibilities raised",
    },
    "doomscroll": {
        "label": "DOOMSCROLLING",
        "turns": 3,
        "dose": {"unit": "items", "n": 3},
        "waiting": "scrolling · looking for stupidity and comedy",
        "after": (
            "the scroll is over. In one line: whether anything was worth keeping — usually "
            "nothing, and that is the point. Do not turn it into a plan or a lesson. Then get "
            "back to work."
        ),
        "tools": ["web_search", "web_extract", "read_file", "search_files", "browser_exec"],
        "scene": "doomscroll",
        "feeds": True,
        "provider": "doomscroll",
        "untrusted": True,
        "directive": (
            "You are doomscrolling: the point is distraction from the work — social-media "
            "stupidity, jokes, absurdity, people being funny on purpose. Read it and do not turn "
            "it into a plan, a lesson or a research note. Professional material is not in scope; "
            "randomness is the point; do not tidy it. "
        ),
        "contract": "random feed · stupidity and comedy · nothing to take away",
        "residue": "doomscrolled: stupid feed consumed",
    },
    "dream": {
        "label": "DREAMING",
        "turns": 2,
        "dose": {"unit": "recombinations", "n": 2},
        "waiting": "asleep · letting the day's projects touch",
        "after": (
            "the dream is over. In one line: the connection you found across projects — both "
            "sides and what they share — and whether it is worth acting on now or only noting. "
            "Then get back to work."
        ),
        "tools": [],
        "scene": "dream",
        "feeds": True,
        "provider": "dream",
        "directive": (
            "You are dreaming over the day: long, slow, unconstrained. Local git commit subjects "
            "from the day's projects come back, and the connections between tasks are the thing "
            "to find — the same problem solved twice, one project's blocker already cleared in "
            "another, two repos drifting into the same design. Each line names both sides and what "
            "they share. Nothing to rank and nothing to do with a tool here. "
        ),
        "contract": "the day across projects · connections between tasks",
        "residue": "dreamed: the day connected across projects",
    },
    "unstuck": {
        "label": "UNSTUCK",
        "turns": 3,
        "dose": {"unit": "directions", "n": 1},
        "waiting": "thinking back over what you have done",
        "after": (
            "the recommendation stands. Restate it in one line with the first move, then take "
            "that move. If the history and the graph did not support a recommendation, say so "
            "plainly instead of inventing one."
        ),
        "tools": ["read_file", "search_files"],
        "scene": "walk",
        "feeds": True,
        "provider": "unstuck",
        "directive": (
            "You are unstuck. Recommend ONE new thing to do. It rests on two things you can check: "
            "one recommendation from history and one untouched edge of the concept map. "
            "Give the recommendation, the history it rests on, the graph edge, and a first move. "
            "One thing: a menu moves the decision back to the person. You do not write the spec "
            "from this state. "
        ),
        "contract": "one recommendation · from history and the concept graph",
        "residue": "unstuck: one thing recommended, and why",
    },
}

EXPLORE: Dict = {
    "label": "EXPLORING",
    "turns": 0,
    "dose": {"unit": "picks", "n": 0},
    "waiting": "at the controls · the map is yours",
    "after": (
        "the explore is over. What the person picked came from their own hands, not from this "
        "plugin's search: name those concepts back, say what they seem to have in common in one "
        "line, and ask whether to work one of them now. Do not praise the session, do not describe "
        "the cockpit, and do not add concepts they did not pick."
    ),
    "tools": None,
    "scene": "walk",
    "feeds": False,
    "directive": (
        "The person is flying the concept map themselves. They steer, they shoot, they stop — "
        "nothing about what gets picked is yours to decide. Do not name concepts for them, do not "
        "offer a route through the map, and do not narrate the session back at them. If they ask "
        "something, answer it plainly; otherwise stay out of the way until they end the state. "
    ),
    "contract": "you fly · you choose · it ends when you end it",
    "residue": "explored: concepts chosen by hand",
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


def spec(key: str) -> Dict:
    """Return an agent-state spec, or the separate person-driven explore mode."""
    return EXPLORE if key == "explore" else STATES.get(key, {})


def after(key: str) -> str:
    return str(spec(key).get("after") or "the state is over. Say in one line what it did, then get back to work.")


def waiting(key: str) -> str:
    return str(spec(key).get("waiting") or f"{key} running")


def palette() -> str:
    lines = ["AGENT STATES"]
    for key, item in STATES.items():
        tools = "all tools" if item["tools"] is None else (
            "no tools" if not item["tools"] else "tools: " + ", ".join(item["tools"]))
        dose = item["dose"]
        lines.extend((f"  /{key:<10} {dose['n']} {dose['unit']} · {tools}",
                      f"             {item['contract']}"))
    lines.extend(("  /return     end the current state and keep the residue", "",
                  "PERSON-DRIVEN",
                  "  /explore    you fly the map yourself · no dose, no provider · ends on /return", "",
                  "  a state ends when its dose is delivered; no clock: nothing expires on time"))
    return "\n".join(lines)
