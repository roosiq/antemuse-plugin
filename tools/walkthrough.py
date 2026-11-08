"""End-to-end walkthrough of the Antemuse runtime, with a stubbed model.

Everything here is the real plugin: real registration, real state engine, real
collider bank, real selection, real hooks. Only `ctx.llm` is a stub, because a
script has no agent host to borrow. Run it:

    env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
        python3 tools/walkthrough.py

It is a demonstration, not a test: `tests/` is the authority on behaviour. Uses
a temporary state home, so it never touches the live agent's state.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys

PLUGIN = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN))


def say(label, body=""):
    print(f"\n\033[1m{label}\033[0m")
    for line in str(body).splitlines():
        print("  " + line)


class StubLlm:
    """Stands in for ctx.llm. Real shape, fake provider."""

    def __init__(self):
        self.calls = 0
        self.requests = []

    async def acomplete_structured(self, **kwargs):
        self.calls += 1
        self.requests.append(kwargs)
        source = "a transfer source"
        return {
            "parsed": {
                "thesis": f"Borrow the far edge of {source} for this report.",
                "mechanism": "Species partition a shared space so nothing competes inside one band.",
                "application": "Give each section its own voice channel instead of one continuous register.",
                "first_step": "Write one sentence that assigns a channel to the closing section.",
                "source_ids": [],
            },
            "text": "RAW MODEL TEXT — must never reach the person",
            "usage": {"total_tokens": 173, "provider": "stub", "model": "stub"},
        }


class Ctx:
    def __init__(self, settings):
        self.hooks, self.commands, self.tools, self.aux = {}, {}, {}, {}
        self.settings = settings
        self.llm = StubLlm()

    def register_hook(self, name, fn): self.hooks[name] = fn
    def register_command(self, name=None, **kw): self.commands[kw.get("name", name)] = kw
    def register_tool(self, **kw): self.tools[kw["name"]] = kw
    def register_auxiliary_task(self, key, **kw): self.aux[key] = kw
    def get_config(self, key, default=None): return self.settings.get(key, default)


def load(settings):
    spec = importlib.util.spec_from_file_location("antemuse_e2e", os.path.join(PLUGIN, "__init__.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ctx = Ctx(settings)
    module.register(ctx)
    return module, ctx


def main():
    module, ctx = load({"experimental.enabled": True})
    from core import engine, session, states

    session.clear()
    print("\033[1m1. THE HUMAN ENTERS A STATE\033[0m")
    say("/walk 3", ctx.commands["walk"]["handler"]("3").splitlines()[0])
    active = engine.watch_state()["active"]
    say("engine record", f"{active['label']} · {active['contract']} · turns_left={active['turns_left']}")

    print("\n\033[1m2. THE HUMAN ASKS FOR A RUN\033[0m")
    say("/spark make the weekly report less boring",
        ctx.commands["spark"]["handler"]("make the weekly report less boring", session_id="e2e-session"))
    say("stub host calls", ctx.llm.calls)

    print("\n\033[1m3. THE MODEL'S NEXT TURN — WHAT IT RECEIVES\033[0m")
    block = module._pre_llm_call(platform="discord", session_id="e2e-session")
    say("injected", block)

    print("\n\033[1m4. THE MODEL ANSWERS — WHAT THE HUMAN SEES\033[0m")
    reply = "I gave the closing section its own channel and cut the middle by a third."
    say("final message", module._transform(reply, session_id="e2e-session"))

    print("\n\033[1m5. FEEDBACK\033[0m")
    run = engine.watch_state()
    say("/keep love #1", ctx.commands["keep"]["handler"]("love #1", session_id="e2e-session"))
    say("/again", ctx.commands["again"]["handler"]("", session_id="e2e-session"))

    print("\n\033[1m6. THE STATE ENDS\033[0m")
    say("/return", ctx.commands["return"]["handler"]("").splitlines()[0])
    say("residue kept", json.dumps(engine.watch_state()["residue"], indent=2)[:320])

    print("\n\033[1m7. NEXT TURN — THE RETURN BLOCK\033[0m")
    say("injected", module._pre_llm_call(platform="discord", session_id="e2e-session"))

    print("\n\033[1m8. SESSION END — PREPARED MATERIAL DIES WITH IT\033[0m")
    session.bind("e2e-session", {"model": "never delivered"})
    say("before", f"pending={session.pending('e2e-session')}")
    ctx.hooks["on_session_end"](session_id="e2e-session")
    say("after on_session_end", f"pending={session.pending('e2e-session')}")

    print("\n\033[1m9. WHAT THE PERSON NEVER SAW\033[0m")
    say("candidate text occurrences in human surfaces",
        "0 (asserted by tests: test_the_person_gets_counts_and_never_candidate_text)")


if __name__ == "__main__":
    main()
