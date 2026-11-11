"""A pane poll is a second of the state's life.

Delivery is paced by the clock (one unit a second from entry), so the thing that asks while
nobody is typing is the pane — `GET /state`, every four seconds. That makes the poll route a
delivery surface, not just a reader, and nothing else in the suite exercises it: the engine
tests call `deliver_if_due()` themselves, which would pass even if the route never did.

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
route_state = getattr(plugin_api, "state")

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
    monkeypatch.setattr(sources, "PROVIDERS",
                        {**sources.PROVIDERS, "walk": lambda steps=1: body[:steps]})


def test_a_poll_delivers_the_units_the_clock_earned(monkeypatch):
    """No turn, no typing — three seconds pass and the pane's own poll serves them."""
    _stub_walk(monkeypatch)
    engine.stop(reason="reset")
    engine.enter("walk", session="poll-pane", platform="desktop")
    assert _served() == 0, "entry alone served material; the poll is not what this measures"

    _backdate(3)
    route_state(session="poll-pane")             # one poll, as the pane sends it

    assert _served() == 4, f"entry plus three banked seconds is 4 units, got {_served()}"


def test_a_second_poll_in_the_same_second_buys_nothing(monkeypatch):
    """The pane polls every four seconds; a burst of polls must not drain the dose."""
    _stub_walk(monkeypatch)
    engine.stop(reason="reset")
    engine.enter("walk", session="poll-burst", platform="desktop")

    route_state(session="poll-burst")
    first = _served()
    for _ in range(3):
        route_state(session="poll-burst")
    assert _served() == first, f"four polls in one second served {_served() - first} extra units"


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
