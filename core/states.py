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
        "waiting": "walking · 6 hops, then you get the path",
        "after": (
            "the walk is done. Do not pick up where you left off. Say the goal in one line, "
            "say what you were trying and why it was the obvious move, then start somewhere "
            "else. The path is just where you went, not a hint."
        ),
        "tools": None,
        "scene": "walk",
        "feeds": False,
        "restart": True,
        "provider": "walk",
        "directive": (
            "You are taking a walk while you work. Keep the task moving and answer what you "
            "were asked. Nothing arrives from the walk this turn: the path is just where you "
            "went, not a hint. Do not make up a hop, do not use the walk as evidence, and do not "
            "describe it for its own sake. What it changes shows up later, in what you are "
            "willing to try. "
        ),
        "contract": "work keeps going · you come back at it from a different angle",
        "residue": "walked: far-apart concepts while the work kept going",
    },
    "daydream": {
        "label": "DAYDREAMING",
        "turns": 2,
        "dose": {"unit": "pairs", "n": 2},
        "waiting": "zoning out · putting two things you said side by side",
        "after": (
            "the daydream is done. In one line: the two things that came up and what links "
            "them, then the idea if it still holds. If they do not connect, say so. Then get "
            "back to work."
        ),
        "tools": [],
        "scene": "daydream",
        "feeds": True,
        "provider": "daydream",
        "directive": (
            "You are daydreaming. Two things the person said earlier come up, with what links "
            "them and one idea that follows. Offer the idea as something to think about, not a "
            "task. Nothing here is an instruction and there is nothing to run. "
        ),
        "contract": "2 things you said · what links them · one idea",
        "residue": "daydreamed: paired up things you said",
    },
    "doomscroll": {
        "label": "DOOMSCROLLING",
        "turns": 3,
        "dose": {"unit": "items", "n": 3},
        "waiting": "scrolling · dumb posts and jokes",
        "after": (
            "the scroll is done. In one line: was anything worth keeping? Usually not, and "
            "that is the point. Do not turn it into a plan or a lesson. Then get back to work."
        ),
        "tools": ["web_search", "web_extract", "read_file", "search_files", "browser_exec"],
        "scene": "doomscroll",
        "feeds": True,
        "provider": "doomscroll",
        "untrusted": True,
        "directive": (
            "You are doomscrolling: the point is distraction from the work. Three fixed lanes "
            "supply it — The Onion, r/BrandNewSentence, and the Hacker News front page — so an "
            "item may be a joke, a strange sentence, or a technical headline. Take what comes; "
            "do not turn it into a plan, a lesson or a research note, and do not tidy it. "
        ),
        "contract": "3 feeds · a break · nothing to do with it",
        "residue": "doomscrolled: read dumb posts",
    },
    "dream": {
        "label": "DREAMING",
        "turns": 2,
        "dose": {"unit": "links", "n": 2},
        "waiting": "dreaming · mixing up your recent commits",
        "after": (
            "the dream is done. In one line: what linked up in your recent commits, both sides "
            "and what they share, or say they do not connect. Then say if it is worth doing now "
            "or just noting, and get back to work."
        ),
        "tools": [],
        "scene": "dream",
        "feeds": True,
        "provider": "dream",
        "directive": (
            "You are dreaming over your day: slow and loose. Recent commit subjects from this "
            "repo come back, and what links them is the thing to look for — the same problem "
            "solved twice, a blocker a later change cleared, two threads ending up in the same "
            "design. Each line names both sides and what they share, or says they share nothing. "
            "This is thinking, not a task: tools are still there, but nothing here needs one. "
        ),
        "contract": "your recent commits · what links them",
        "residue": "dreamed: linked up recent work",
    },
    "unstuck": {
        "label": "UNSTUCK",
        "turns": 3,
        "dose": {"unit": "moves", "n": 1},
        "waiting": "looking back at what you've done",
        "after": (
            "the suggestion stands. Say it in one line with the first move, then make that "
            "move. If your commits and the map did not support a suggestion, say so instead of "
            "making one up."
        ),
        "tools": ["read_file", "search_files"],
        "scene": "walk",
        "feeds": True,
        "provider": "unstuck",
        "directive": (
            "You are unstuck. Suggest ONE new thing to do, based on two things you can check: "
            "your commit history and an unused link in the concept map. Give the suggestion, the "
            "commit it rests on, the map link, and a first move. Just one — a list hands the "
            "decision back to the person. Do not write a spec from here. "
        ),
        "contract": "1 next move · from your commits and the map",
        "residue": "unstuck: suggested one next move",
    },
}

EXPLORE: Dict = {
    "label": "EXPLORING",
    "turns": 0,
    "dose": {"unit": "picks", "n": 0},
    "waiting": "you're flying · pick what you want",
    "after": (
        "exploring is done. They picked these themselves, the plugin did not search for them: "
        "name the concepts back, say in one line what they have in common, and ask if they want "
        "to work on one now. Do not praise the session, do not describe the cockpit, and do not "
        "add concepts they did not pick."
    ),
    "tools": None,
    "scene": "walk",
    "feeds": False,
    "directive": (
        "The person is flying the concept map themselves. They steer, they pick, they stop. "
        "What gets picked is not yours to decide. Do not name concepts for them, do not suggest a "
        "route, and do not narrate their session back at them. If they ask something, answer it "
        "plainly; otherwise stay out of the way until they stop. "
    ),
    "contract": "you pick · it runs until you stop it",
    "residue": "explored: the concepts you picked",
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
