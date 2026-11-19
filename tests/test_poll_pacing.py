"""A pane poll is a look, not a turn.

The poll route is a delivery surface: the pane asks every four seconds, and the
engine serves the next hop there so a walk shows itself while nobody is typing.
What it may not do is spend the dose the person has not earned — a burst of
polls used to finish a six-hop walk before the first message was written.

These call the route directly, as its own docstring allows, and read the state record
afterwards. The provider is stubbed *in the module the route loads* (`plugin_api.plugin()`),
because that load is a second copy of `core` — stubbing the test's own import would leave the
route serving real WordNet and the measurement would be of something else entirely.
"""

import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="poll-pacing-")

from core import engine  # noqa: E402
from dashboard import plugin_api  # noqa: E402

# The route the pane polls. `router.get` is untyped, so this is the shortest honest way to name
# the function in a test without a type-checker argument.
# The pane's poll is a POST: delivery is a write. `GET /state` is a pure look.
route_state = getattr(plugin_api, "deliver")

HOPS = ["morris dance→sea swallow [far]", "sea swallow→thalassemia [far]",
        "thalassemia→long-horned beetle [far]", "long-horned beetle→glasshouse [far]",
        "glasshouse→flatfish [far]", "flatfish→morris dance [far]"]


def _route_module(name: str):
    """A `core` submodule as the route sees it, loaded the way the web server loads it.

    The route's package is a second copy under a private name, and it imports its own submodules
    lazily, so they are not attributes of the package until something touches them.
    """
    import importlib

    package = getattr(plugin_api, "plugin")()
    return importlib.import_module(f"{package.__name__}.core.{name}")


def _backdate(seconds: float) -> None:
    """Age the running state, so a test can hand the clock several seconds at once."""
    data = engine._load()
    data["active"]["entered_at"] = float(data["active"]["entered_at"]) - seconds
    engine._save(data)


def _served() -> int:
    return int((engine.peek() or {}).get("served") or 0)


def _stub_walk(monkeypatch, lines=None) -> None:
    sources = _route_module("sources")
    body = list(lines if lines is not None else HOPS)

    def call(steps=1):          # a walk serves a new hop per call, not the same first hop
        out, body[:] = body[:steps], body[steps:]
        return out

    monkeypatch.setattr(sources, "PROVIDERS", {**sources.PROVIDERS, "walk": call})


def test_a_poll_serves_one_unit_and_no_clock_banks_them(monkeypatch):
    """No turn, no typing — the pane's own poll serves a unit. Time is not a currency here."""
    _stub_walk(monkeypatch)
    engine.stop(reason="reset")
    engine.enter("walk", session="poll-pane", platform="desktop")
    assert _served() == 0, "entry alone served material; the poll is not what this measures"

    _backdate(3)                                 # three seconds, which now buy nothing
    route_state(session="poll-pane")             # one poll, as the pane sends it

    assert _served() == 1, f"one poll must serve exactly one hop, got {_served()}"


def test_a_burst_of_polls_cannot_outrun_the_person(monkeypatch):
    """A poll is a look, not a turn.

    Four polls used to serve four hops, so a six-hop walk finished itself in
    twenty-four seconds and the person arrived to a chip reading `6/6`. The pane
    may show the hop that exists on entry and no more until a turn is taken.
    """
    _stub_walk(monkeypatch)
    engine.stop(reason="reset")
    engine.enter("walk", session="poll-burst", platform="desktop")

    for _ in range(4):
        route_state(session="poll-burst")
    assert _served() == 1, f"polls spent the dose before anyone spoke: {_served()}"

    engine.note_turn(session="poll-burst")
    route_state(session="poll-burst")
    assert _served() == 2, f"one turn should earn one more hop, got {_served()}"

    for _ in range(6):
        route_state(session="poll-burst")
    assert _served() == 2, f"polls kept spending after the turn: {_served()}"


def test_a_failed_hop_is_named_and_the_pane_still_draws(monkeypatch):
    """A provider that raises is a hop that did not land — the pane keeps its state."""
    sources = _route_module("sources")

    def boom(steps=1):
        raise RuntimeError("corpus is not here")

    monkeypatch.setattr(sources, "PROVIDERS", {**sources.PROVIDERS, "walk": boom})
    engine.stop(reason="reset")
    engine.enter("walk", session="poll-fail", platform="desktop")
    _backdate(2)

    payload = route_state(session="poll-fail")
    assert (payload.get("active") or {}).get("key") == "walk", \
        f"a failed hop took the state off the pane: {payload.get('active')}"
    journal = [str(e.get("text") or "") for e in (engine._load().get("journal") or [])]
    named = [t for t in journal if "provider failed" in t]
    assert named, f"a failed hop was not named anywhere: {journal[-3:]}"
    assert _served() <= math.floor(2) + 1, "a provider that raised was counted as a full hop"
