"""J1 — the experimental boundary is registered, and a session's material dies with it.

Nothing here calls a model. Registration is inert: it declares what the host may
route to, and declares that a session boundary exists. The optional enter fields
are validated and, while the experimental flag is off, refused.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="j1-test-")

from core import engine, options, session  # noqa: E402


def setup_function(_):
    session.clear()
    engine.clear()


class FakeCtx:
    """The parts of a plugin context registration touches, and nothing more."""

    def __init__(self, settings=None, auxiliary=True, config=True):
        self.hooks = {}
        self.commands = {}
        self.tools = {}
        self.auxiliary = {}
        self.settings = dict(settings or {})
        self._has_aux = auxiliary
        self._has_config = config
        if not auxiliary:
            # An older host has no such method at all.
            self.register_auxiliary_task = None  # type: ignore[assignment]
        if not config:
            self.get_config = None  # type: ignore[assignment]

    def register_hook(self, name, fn):
        self.hooks[name] = fn

    def register_command(self, name, **_kwargs):
        self.commands[name] = _kwargs

    def register_tool(self, **_kwargs):
        self.tools[_kwargs.get("name")] = _kwargs

    def register_auxiliary_task(self, key, **kwargs):
        self.auxiliary[key] = kwargs

    def get_config(self, key, default=None):
        if not self._has_config:
            raise AttributeError("get_config")
        return self.settings.get(key, default)


def _plugin():
    spec = importlib.util.spec_from_file_location("antemuse_j1", os.path.join(ROOT, "__init__.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------- session store

def test_material_belongs_to_the_session_that_bound_it():
    assert session.bind("s1", {"candidates": [1]}) is True
    assert session.take("s1") == {"candidates": [1]}
    assert session.take("s1") is None


def test_another_session_cannot_take_it():
    session.bind("s1", {"candidates": [1]})
    before = session.count()
    assert session.take("s2") is None
    assert session.count() == before, "a foreign take must not consume"
    assert session.take("s1") == {"candidates": [1]}, "the owner can still take it"


def test_an_empty_session_id_binds_and_takes_nothing():
    assert session.bind("", {"x": 1}) is False
    assert session.take("") is None
    assert session.release("") == 0


def test_release_drops_only_that_session():
    session.bind("s1", {"a": 1})
    session.bind("s2", {"b": 2})
    assert session.release("s1") == 1
    assert session.take("s1") is None
    assert session.take("s2") == {"b": 2}


def test_release_is_idempotent_and_quiet_for_unknown_sessions():
    session.bind("s1", {"a": 1})
    assert session.release("s1") == 1
    assert session.release("s1") == 0
    assert session.release("never-existed") == 0


def test_a_full_store_refuses_a_new_session_instead_of_dropping_an_old_one():
    for i in range(session.MAX_SESSIONS):
        assert session.bind(f"s{i}", {"i": i}) is True
    assert session.bind("late", {"i": "late"}) is False, "a full store must refuse"
    assert session.take("late") is None, "a refused bind must store nothing"
    for i in range(session.MAX_SESSIONS):
        assert session.take(f"s{i}") == {"i": i}, f"s{i} was dropped"


def test_rebinding_the_same_session_keeps_it_alive():
    session.bind("s1", {"v": 1})
    for i in range(session.MAX_SESSIONS - 1):
        session.bind(f"other{i}", {"i": i})
    assert session.bind("s1", {"v": 2}) is True, "a re-bind is not a new session"
    assert session.take("s1") == {"v": 2}


# ------------------------------------------------------------- registration

def test_the_four_session_boundaries_release():
    ctx = FakeCtx()
    _plugin().register(ctx)
    for name in ("on_session_end", "on_session_finalize", "on_session_reset", "on_session_delete"):
        assert name in ctx.hooks, f"{name} not registered"
    session.bind("s1", {"a": 1})
    ctx.hooks["on_session_reset"](session_id="s1")
    assert session.take("s1") is None


def test_a_session_hook_without_an_id_releases_nothing():
    ctx = FakeCtx()
    _plugin().register(ctx)
    session.bind("s1", {"a": 1})
    ctx.hooks["on_session_end"]()
    assert session.take("s1") == {"a": 1}


def test_auxiliary_tasks_are_registered_under_the_plugin_namespace():
    ctx = FakeCtx()
    _plugin().register(ctx)
    assert set(ctx.auxiliary) == {"antemuse_generate", "antemuse_select", "antemuse_refresh"}
    for key, entry in ctx.auxiliary.items():
        assert entry["display_name"], key
        assert entry["description"], key
        assert entry["defaults"]["timeout"] >= 30, key


def test_registration_survives_a_host_without_auxiliary_tasks():
    ctx = FakeCtx(auxiliary=False)
    _plugin().register(ctx)          # must not raise
    assert ctx.auxiliary == {}
    assert "pre_llm_call" in ctx.hooks


def test_experimental_is_off_until_the_operator_turns_it_on():
    module = _plugin()
    assert module.experimental_enabled(FakeCtx()) is False
    assert module.experimental_enabled(FakeCtx({"experimental.enabled": False})) is False
    assert module.experimental_enabled(FakeCtx({"experimental.enabled": True})) is True
    assert module.experimental_enabled(FakeCtx(config=False)) is False, "no config read means off"


# ------------------------------------------------------------ enter fields

def test_no_method_fields_means_todays_behaviour():
    assert options.parse({}) == {}
    assert options.parse({"action": "enter", "name": "walk"}) == {}
    msg = engine.enter("walk")
    assert "WALKING" in msg
    active = engine.watch_state()["active"]
    assert "options" not in active, "an entry without options must not grow a key"


def test_a_method_outside_the_approved_set_is_refused():
    for bad in ("turbo", "sparky", "COLLIDE!"):
        try:
            options.parse({"method": bad})
        except ValueError as exc:
            assert "method" in str(exc)
        else:
            raise AssertionError(f"{bad!r} was accepted")


def test_a_budget_outside_its_bounds_is_refused():
    for bad in ({"calls": 99}, {"seconds": 0}, {"tokens": -1}, {"calls": "3"}, {},
                {"depth": 2}, {"calls": 3, "depth": 2}):
        try:
            options.parse({"budget": bad})
        except ValueError as exc:
            assert "budget" in str(exc)
        else:
            raise AssertionError(f"{bad!r} was accepted")


def test_approved_options_normalise():
    assert options.parse({"method": "Spark", "seed": 7}) == {"method": "spark", "seed": "7"}
    assert options.parse({"budget": {"calls": 3, "seconds": 30}}) == {"budget": {"calls": 3, "seconds": 30}}


def test_the_tool_schema_fields_are_optional():
    schema = _plugin().STATE_SCHEMA
    assert schema["parameters"]["required"] == ["action"]
    fields = schema["parameters"]["properties"]
    for name in ("method", "seed", "budget"):
        assert name in fields, name
    assert fields["method"]["enum"] == ["collide", "deep", "chaos", "spark"]


def test_entering_with_a_method_while_disabled_is_refused():
    module = _plugin()
    ctx = FakeCtx()
    module.register(ctx)
    handle = ctx.tools["state"]["handler"]
    out = handle({"action": "enter", "name": "walk", "method": "spark"})
    assert "experimental" in out.lower()
    assert engine.watch_state().get("active") is None, "a refused entry must not open a state"


def test_the_registered_handler_reads_the_host_it_was_registered_with():
    """The gate must follow the invoking host, not whatever registered last."""
    module = _plugin()
    off, on = FakeCtx(), FakeCtx({"experimental.enabled": True})
    module.register(off)
    module.register(on)                       # a second registration must not leak into the first
    off_handle = off.tools["state"]["handler"]
    on_handle = on.tools["state"]["handler"]
    assert "experimental" in off_handle({"action": "enter", "name": "walk", "method": "spark"}).lower()
    assert engine.watch_state().get("active") is None
    out = on_handle({"action": "enter", "name": "walk", "method": "spark", "seed": 3,
                     "budget": {"calls": 2}})
    assert "WALKING" in out, out
    active = engine.watch_state()["active"]
    assert active["options"] == {"method": "spark", "seed": "3", "budget": {"calls": 2}}


def test_the_session_hooks_accept_the_hosts_documented_payload():
    """hermes_cli/hooks.py sends session_id plus task/completion fields."""
    ctx = FakeCtx()
    _plugin().register(ctx)
    session.bind("s1", {"a": 1})
    ctx.hooks["on_session_end"](session_id="s1", task_id="t", turn_id="u", completed=True,
                                failed=False, interrupted=False, turn_exit_reason="text_response(stop)",
                                model="m", platform="cli")
    assert session.take("s1") is None
    session.bind("s2", {"b": 2})
    ctx.hooks["on_session_delete"](session_id="s2", reason="delete", profile="default")
    assert session.take("s2") is None
