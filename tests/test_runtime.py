"""J2 — one bounded run, two audiences, and no raw material crossing over."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="runtime-test-")

from core import runtime, session  # noqa: E402


def setup_function(_):
    session.clear()
    runtime.clear()



def via_tool(ctx, **args):
    """Exploration is a tool action now: `/spark` and `/keep` are gone."""
    return ctx.tools["state"]["handler"](args)

def test_a_run_produces_candidates_from_the_real_bank():
    run = runtime.plan("make the weekly report less boring")
    assert run.candidates, "no candidates from the collider bank"
    assert run.kept, "selection kept nothing"
    assert run.sources, "no sources recorded"
    assert run.run_id


def test_the_person_gets_counts_and_never_candidate_text():
    """The account is the only human-facing artefact; it must not carry injection."""
    run = runtime.plan("make the weekly report less boring")
    account = run.account()
    for candidate in run.candidates:
        thesis = str(candidate.get("thesis") or "")
        mechanism = str(candidate.get("mechanism") or "")
        if len(thesis) > 12:
            assert thesis not in account
        if len(mechanism) > 12:
            assert mechanism not in account
    assert "candidate" in account
    assert len(account) <= runtime.HUMAN_MAX_CHARS


def test_the_model_gets_the_candidates_with_the_caveat():
    run = runtime.plan("make the weekly report less boring")
    block = run.for_model()
    assert "[EXPLORATION:" in block
    assert "the person sees only pictures" in block
    assert "not findings" in block
    first = str(run.kept[0].get("thesis") or "")[:24]
    assert first and first in block


def test_a_run_needs_a_goal():
    for bad in ("", "   "):
        try:
            runtime.plan(bad)
        except ValueError as exc:
            assert "goal" in str(exc)
        else:
            raise AssertionError(f"{bad!r} was accepted")


def test_the_budget_takes_the_operator_bounds():
    budget = runtime._budget({"budget": {"calls": 3, "tokens": 900, "seconds": 30}})
    assert budget.max_calls == 3
    assert budget.max_output_tokens == 900
    assert budget.timeout_seconds == 30.0
    default = runtime._budget({})
    assert default.max_calls == runtime.DEFAULT_BUDGET["calls"]


def test_prepared_material_is_consumed_once_and_only_by_its_session():
    run = runtime.plan("make the weekly report less boring")
    assert runtime.prepare("s1", run) is True
    assert runtime.injection("s2") is None, "another session must not take it"
    assert runtime.injection("s1") is not None
    assert runtime.injection("s1") is None, "material is consumed, not repeated"
    assert runtime.take_account("s1") is not None, "the account survives for the footer"
    assert runtime.take_account("s1") is None


def test_feedback_routes_the_next_strategy():
    run = runtime.plan("make the weekly report less boring")
    candidate_id = str(run.kept[0].get("candidate_id") or "c1")
    assert runtime.next_strategy("s1") is None
    runtime.keep("s1", "like", candidate_id)
    assert runtime.next_strategy("s1") == "refresh"
    runtime.keep("s1", "love", candidate_id)
    assert runtime.next_strategy("s1") == "deepen"


def test_trash_alone_never_routes_a_strategy():
    runtime.keep("s1", "trash", "c1")
    assert runtime.next_strategy("s1") is None
    assert "not kept" in runtime.keep("s1", "banish", "c1")


# ----------------------------------------------------------------- the wiring
import importlib.util  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Ctx:
    def __init__(self, settings=None):
        self.hooks, self.commands, self.tools, self.auxiliary = {}, {}, {}, {}
        self.settings = dict(settings or {})

    def register_hook(self, name, fn):
        self.hooks[name] = fn

    def register_command(self, name, **kw):
        self.commands[name] = kw

    def register_tool(self, **kw):
        self.tools[kw.get("name")] = kw

    def register_auxiliary_task(self, key, **kw):
        self.auxiliary[key] = kw

    def get_config(self, key, default=None):
        return self.settings.get(key, default)


def _plugin():
    spec = importlib.util.spec_from_file_location("antemuse_j2", os.path.join(ROOT, "__init__.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_the_commands_are_registered():
    ctx = _Ctx()
    _plugin().register(ctx)
    assert set(ctx.commands) == {"walk", "daydream", "doomscroll", "dream", "trailhead",
                                "return"}, (
        "the public surface is the five states and the way out"
    )
    assert {"spark", "keep"} <= set(ctx.tools["state"]["schema"]["parameters"]
                                     ["properties"]["action"]["enum"])


def test_spark_accounts_to_the_person_and_hands_candidates_to_the_model():
    module = _plugin()
    ctx = _Ctx()
    module.register(ctx)
    from core import engine
    engine.remember_platform("discord", "sess-x")

    human = via_tool(ctx, action="spark", goal="make the weekly report less boring")
    assert "spark" in human and "candidate" in human

    block = module._pre_llm_call(platform="discord", session_id="sess-x")
    assert block and "[EXPLORATION:" in block, "the model must receive the candidates"
    assert "not findings" in block

    # nothing from the injected block leaked into the human line
    for line in block.splitlines():
        probe = line.strip().lstrip("· ")[:20]
        if probe and len(probe) > 12:
            assert probe not in human

    footer = module._transform("the answer", session_id="sess-x")
    assert footer and "— spark ·" in footer, footer
    assert "the answer" in footer


def test_spark_without_a_goal_says_how_to_use_it():
    ctx = _Ctx()
    _plugin().register(ctx)
    assert "usage" in via_tool(ctx, action="spark")


def test_keep_and_spark_again_route_the_person_feedback():
    module = _plugin()
    ctx = _Ctx()
    module.register(ctx)
    from core import engine
    engine.remember_platform("discord", "sess-y")
    via_tool(ctx, action="spark", goal="a goal")
    run = runtime.plan("a goal")
    candidate_id = str(run.kept[0].get("candidate_id") or "c1")

    assert "nothing loved" in via_tool(ctx, action="spark", goal="again")
    assert "kept as love" in via_tool(ctx, action="keep", verdict="love", candidate=candidate_id)
    assert "deepen" in via_tool(ctx, action="spark", goal="again")
    assert "routes to deepen" in via_tool(ctx, action="spark", goal="again refresh")
    assert "usage" in via_tool(ctx, action="keep", verdict="love")


# ------------------------------------------------------- the branch path (J2b)
import asyncio  # noqa: E402


class _FakeLlm:
    """A host that answers like ctx.llm does, and counts what it was asked."""

    def __init__(self, fail=False, tokens=120):
        self.calls = 0
        self.fail = fail
        self.tokens = tokens
        self.seen = []

    async def acomplete_structured(self, **kwargs):
        self.calls += 1
        self.seen.append(kwargs)
        if self.fail:
            raise RuntimeError("provider said no")
        return {
            "parsed": {
                "thesis": f"branch {self.calls} thesis about the goal",
                "mechanism": "a mechanism worth transferring",
                "application": "apply it to the report",
                "first_step": "write one sentence",
                "source_ids": [],
            },
            "text": "raw model text that the person must never see",
            "usage": {"total_tokens": self.tokens},
        }


def test_the_branch_path_calls_the_host_and_keeps_candidates():
    host = _FakeLlm()
    run = asyncio.run(runtime.run_branches(host, "make the weekly report less boring"))
    assert host.calls == runtime.DEFAULT_BUDGET["calls"], "one call per budgeted branch"
    assert run.branches == len(run.sources) > host.calls, "every source is a planned branch"
    assert run.skipped == run.branches - host.calls, "the rest are skipped by budget, not failed"
    assert run.failed == 0
    assert run.candidates, "no candidates from the branches"
    assert run.kept
    assert str(run.status) in ("ok", "partial")
    assert run.usage.get("total_tokens", 0) > 0


def test_the_branch_account_counts_and_never_quotes():
    host = _FakeLlm(tokens=321)
    run = asyncio.run(runtime.run_branches(host, "make the weekly report less boring"))
    account = run.account()
    assert "branch(es)" in account
    assert "skipped by budget" in account
    assert "642 tokens" in account, account
    assert "thesis about the goal" not in account
    assert "worth transferring" not in account


def test_a_failing_branch_is_reported_not_hidden():
    host = _FakeLlm(fail=True)
    run = asyncio.run(runtime.run_branches(host, "make the weekly report less boring"))
    assert run.failed == host.calls > 0
    assert run.skipped == run.branches - host.calls
    assert run.status in ("error", "partial")
    assert not run.kept
    assert "failed" in run.account()


def test_a_host_without_the_structured_call_is_refused():
    try:
        asyncio.run(runtime.run_branches(object(), "a goal"))
    except TypeError as exc:
        assert "acomplete_structured" in str(exc)
    else:
        raise AssertionError("a host without the method was accepted")


def test_run_sync_works_from_inside_a_running_loop():
    """Hooks fire inside the host's loop; the runner must not break it."""
    host = _FakeLlm()

    async def inside_a_loop():
        return runtime.run_sync(host, "make the weekly report less boring")

    run = asyncio.run(inside_a_loop())
    assert run.branches >= 1
    assert host.calls >= 1


def test_spark_only_calls_the_host_when_the_flag_is_on():
    module = _plugin()
    from core import engine

    off = _Ctx()
    off.llm = _FakeLlm()
    module.register(off)
    engine.remember_platform("discord", "sess-off")
    human = via_tool(off, action="spark", goal="a goal for the off case")
    assert off.llm.calls == 0, "the deterministic path must not call a model"
    assert "branch(es)" not in human

    on = _Ctx({"experimental.enabled": True})
    on.llm = _FakeLlm(tokens=111)
    module.register(on)
    engine.remember_platform("discord", "sess-on")
    human = via_tool(on, action="spark", goal="a goal for the on case")
    assert on.llm.calls == runtime.DEFAULT_BUDGET["calls"], "the branch path must call the host"
    assert "branch(es)" in human and "skipped by budget" in human, human


# ------------------------------------------- feedback steering (J2b)
from core import collider, collision  # noqa: E402


def test_selection_can_be_steered_by_a_verdict():
    bank = collider.load_bank()
    loved = ["collider_selective_autophagy"]

    deepened = collision.collide({"id": "a goal", "brief": "a goal"}, bank, seed="s",
                                 count=6, strategy="deepen", loved=loved)
    assert set(deepened.source_ids) == set(loved), deepened.source_ids

    fresh = collision.collide({"id": "a goal", "brief": "a goal"}, bank, seed="s", count=6)
    assert set(fresh.source_ids) != set(loved)


def test_a_verdict_that_is_not_in_the_bank_says_so():
    bank = collider.load_bank()
    try:
        collision.collide({"id": "a goal", "brief": "a goal"}, bank, seed="s",
                          strategy="deepen", loved=["not_a_real_source"])
    except ValueError as exc:
        assert "not_a_real_source" in str(exc)
    else:
        raise AssertionError("a filter with no family was accepted")


def test_feedback_ids_resolve_candidate_ids_to_source_ids():
    """Verdicts are recorded against `<run>:<source>`; selection wants the source."""
    run = runtime.plan("make the weekly report less boring")
    assert runtime.prepare("sess-map", run) is True
    candidate_id = str(run.kept[0].get("candidate_id") or "")
    assert candidate_id.split(":")[-1].startswith("collider_"), candidate_id

    runtime.keep("sess-map", "love", candidate_id)
    ids = runtime.feedback_ids("sess-map")
    assert ids["loved"], ids
    assert all(i.startswith("collider_") for i in ids["loved"]), ids


def test_the_whole_chain_from_a_verdict_to_a_steered_run():
    module = _plugin()
    ctx = _Ctx()
    module.register(ctx)
    from core import engine
    engine.remember_platform("discord", "sess-fb")

    first = via_tool(ctx, action="spark", goal="make the weekly report less boring")
    assert "candidate" in first
    assert "kept as love" in via_tool(ctx, action="keep", verdict="love", candidate="#1")

    ids = runtime.feedback_ids("sess-fb")
    assert ids["loved"], "the verdict did not resolve to a source"

    second = via_tool(ctx, action="spark", goal="again")
    assert second.startswith("deepen"), second
    assert "candidate(s)" in second

    # the re-run was bound to the session too, so the model gets the new material
    assert runtime.injection("sess-fb") is not None


def test_spark_again_refuses_when_feedback_points_the_other_way():
    module = _plugin()
    ctx = _Ctx()
    module.register(ctx)
    from core import engine
    engine.remember_platform("discord", "sess-again")
    via_tool(ctx, action="spark", goal="a goal")
    via_tool(ctx, action="keep", verdict="like", candidate="#1")
    assert "routes to refresh" in via_tool(ctx, action="spark", goal="again deepen")


def test_a_steered_run_does_not_call_excluded_sources_skipped():
    """deepen/refresh exclude by strategy; saying 'skipped by budget' would lie."""
    host = _FakeLlm()
    run = asyncio.run(runtime.run_branches(
        host, "make the weekly report less boring",
        strategy="deepen", loved=["collider_selective_autophagy"], method="deepen",
    ))
    assert run.branches < 6, run.branches
    assert run.skipped == 0, run.skipped
    assert "skipped by budget" not in run.account()
    assert run.account().startswith("deepen")


# ---------------------------------------------------------- J3: origin, cleanup
def test_material_is_dropped_when_the_turn_arrives_from_another_project():
    """Dropped, not rerouted: another project's turn must not receive the run."""
    run = runtime.plan("make the weekly report less boring")
    runtime.prepare("sess-origin", run, origin={"project": "/home/ryan/antemuse"})
    assert runtime.injection("sess-origin", origin={"project": "/home/ryan/toslop"}) is None
    assert runtime.take_account("sess-origin") is None, "no account leaks either"


def test_material_is_delivered_in_the_project_that_prepared_it():
    run = runtime.plan("make the weekly report less boring")
    runtime.prepare("sess-same", run, origin={"project": "/home/ryan/antemuse"})
    assert runtime.injection("sess-same", origin={"project": "/home/ryan/antemuse"}) is not None


def test_an_unknown_origin_does_not_block_delivery():
    """No project at prepare time is ignorance, not a mismatch."""
    run = runtime.plan("make the weekly report less boring")
    runtime.prepare("sess-blind", run, origin={})
    assert runtime.injection("sess-blind", origin={"project": "/home/ryan/toslop"}) is not None


def test_release_forgets_every_runtime_book_for_that_session():
    run = runtime.plan("make the weekly report less boring")
    runtime.prepare("sess-end", run)
    candidate_id = str(run.kept[0].get("candidate_id") or "")
    runtime.keep("sess-end", "love", candidate_id)
    assert runtime.next_strategy("sess-end") == "deepen"
    assert runtime.last_goal("sess-end")
    assert runtime.feedback_ids("sess-end")["loved"]

    runtime.release("sess-end")

    assert runtime.next_strategy("sess-end") is None
    assert runtime.last_goal("sess-end") is None
    assert runtime.feedback_ids("sess-end") == {"loved": [], "liked": []}
    assert runtime.injection("sess-end") is None


def test_the_session_boundary_hook_clears_the_runtime_books():
    module = _plugin()
    ctx = _Ctx()
    module.register(ctx)
    from core import engine
    engine.remember_platform("discord", "sess-hook")
    via_tool(ctx, action="spark", goal="a goal to forget")
    via_tool(ctx, action="keep", verdict="like", candidate="#1")
    assert runtime.next_strategy("sess-hook") == "refresh"

    ctx.hooks["on_session_end"](session_id="sess-hook")

    assert runtime.next_strategy("sess-hook") is None
    assert runtime.last_goal("sess-hook") is None


def test_returning_from_a_state_keeps_a_run_that_is_still_waiting():
    """/return ends the state; it must not eat prepared exploration material."""
    module = _plugin()
    ctx = _Ctx()
    module.register(ctx)
    from core import engine
    engine.remember_platform("discord", "sess-return")
    ctx.commands["walk"]["handler"]("1")
    via_tool(ctx, action="spark", goal="a goal that survives the return")
    ctx.commands["return"]["handler"]("")
    assert runtime.injection("sess-return") is not None


# ---------------------------------------- review gate 2 repairs (2026-11-08)
def test_a_run_with_no_session_is_refused_not_parked():
    """No shared slot: an unbound run must not wait for the next session to claim it."""
    run = runtime.plan("make the weekly report less boring")
    assert runtime.prepare("", run) is False
    assert runtime.injection("") is None
    assert runtime.injection("some-session") is None, "nothing may be claimable"


def test_one_sessions_goal_and_verdicts_never_answer_for_another():
    run = runtime.plan("a goal owned by s1")
    assert runtime.prepare("s1", run) is True
    candidate_id = str(run.kept[0].get("candidate_id") or "")
    runtime.keep("s1", "love", candidate_id)

    assert runtime.last_goal("s2") is None
    assert runtime.next_strategy("s2") is None
    assert runtime.feedback_ids("s2") == {"loved": [], "liked": []}
    assert runtime.last_goal("s1") == "a goal owned by s1"


def test_clear_forgets_the_goal_as_well():
    run = runtime.plan("a goal to clear")
    runtime.prepare("s-clear", run)
    runtime.clear("s-clear")
    assert runtime.last_goal("s-clear") is None


def test_the_branch_timeout_is_real_and_bounded():
    """A pool future cannot be cancelled; the deadline must still return."""
    import time

    async def slow(host, goal, **kwargs):
        await asyncio.sleep(3)
        return runtime.plan(goal)

    original = runtime.run_branches
    runtime.run_branches = slow
    try:
        async def inside():
            return runtime.run_sync(
                _FakeLlm(), "a goal",
                options={"budget": {"calls": 1, "tokens": 100, "seconds": 1}},
                timeout_slack=0.2,
            )

        started = time.monotonic()
        try:
            asyncio.run(inside())
        except TimeoutError as exc:
            assert "discarded" in str(exc)
        else:
            raise AssertionError("an overrunning run was not reported")
        elapsed = time.monotonic() - started
        assert elapsed < 2.5, f"the caller waited {elapsed:.1f}s for a 1.2s deadline"
    finally:
        runtime.run_branches = original


def test_an_error_cannot_crowd_the_counts_out_of_the_line():
    run = runtime.plan("a goal")
    run.error = "x" * 200
    account = run.account()
    assert account.startswith("spark · ")
    assert "…" in account
    assert len(account) <= runtime.HUMAN_MAX_CHARS


def test_the_account_follows_the_turns_own_session_not_the_remembered_one():
    """A host multiplexing chats can have the state point at the next turn's session."""
    module = _plugin()
    ctx = _Ctx()
    module.register(ctx)
    from core import engine

    run = runtime.plan("a goal for session A")
    runtime.prepare("A", run, origin={})
    engine.remember_platform("discord", "B")          # the next turn's chat
    block = module._pre_llm_call(platform="discord", session_id="A")
    assert block and "[EXPLORATION:" in block

    footer = module._transform("the answer", session_id="A")
    assert footer and "— spark ·" in footer, "session A's account must reach session A"
    assert module._transform("another answer", session_id="B") is None, "B has no account"
