"""Antemuse — the agent can take a walk, daydream, doomscroll, dream.

A state is a temporary change to how the agent behaves, not a place it goes:

  tools      which tools it may still use
  directive  what shape the turn takes, injected into the user message
  contract   the one line the state is judged by
  residue    what it carries back when the state ends

Surfaces:
  pre_llm_call         inject the active state into the turn
  pre_tool_call        block tools the state forbids
  transform_llm_output make the state visible on the reply
  commands             see docs/spec.md §10 and specs/changes/command-surface;
                       one verb, one name — /state is the text frame, /states the picture
  tool                 state(action=…) — twelve actions, defined in the same place
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path as _Path
from typing import Any, Dict

logger = logging.getLogger("antemuse")

# Imported as a package when the host really loaded us as one, flat when it loaded this file
# directly (a spec load, a synthetic module name, the CLI's own loader). The choice is made by
# looking at what is in sys.modules, not by catching ImportError: a blanket except turned a real
# failure inside `core` into "No module named 'core'", which is the wrong diagnosis and sends the
# person who sees it looking for a packaging problem that is not there (it is how a registration
# failure looked on Windows).
_here = _Path(__file__).resolve().parent
_as_package = bool(__package__) and getattr(sys.modules.get(__package__), "__path__", None) is not None

if _as_package:
    from .core import (engine, history, options, panel, recall, runtime, session, settings,
                       states, surfaces, tui, walks)  # noqa: F401
else:  # flat load: this file is or is not on sys.path, but its directory is what `core` needs
    sys.path.insert(0, str(_here))
    from core import (engine, history, options, panel, recall, runtime, session, settings,
                      states, surfaces, tui, walks)  # type: ignore[no-redef]  # noqa: F401

__version__ = "0.9.7"

STATE_SCHEMA: Dict[str, Any] = {
    "name": "state",
    "description": (
        "Enter or leave a cognitive state for the agent itself. "
        "state(action='enter', name='walk'|'daydream'|'dream'|'doomscroll') changes what tools "
        "you may use and what shape your next replies take, for a bounded number of minutes and turns. "
        "state(action='exit') ends it and keeps the residue. state(action='status') reports what you are in. "
        "state(action='break') recommends one and state(action='break', name='walk') takes it; "
        "state(action='mood', feeling='stuck') records how the work feels. "
        "state(action='list') shows every state with its tools, duration, and contract. "
        "Walks are user-definable: state(action='walks') lists them, "
        "state(action='walk_new') saves one, state(action='walk_del') removes your own."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string",
                       "enum": ["enter", "exit", "status", "list", "walks", "walk_new",
                                "walk_del", "break", "mood", "spark", "keep", "complete",
                                "watch", "card", "image"]},
            "name": {"type": "string",
                     "description": "State to enter (walk, daydream, dream, doomscroll) or the walk to use."},
            "minutes": {"type": "integer", "description": "Optional override for how long the state lasts."},
            "walk": {"type": "string", "description": "Which walk to traverse: wander, upward, downward, lateral, or one you saved."},
            "goal": {"type": "string",
                     "description": "For action='spark': what the run is for. The person sees counts, never candidates."},
            "verdict": {"type": "string", "enum": ["love", "like", "trash"],
                        "description": "For action='keep': how the run's candidates landed."},
            "candidate": {"type": "string",
                          "description": "For action='keep': '#2' from the run account, or a full id."},
            "feeling": {"type": "string", "enum": ["stuck", "tired", "sharp", "flat", "saturated"],
                        "description": "For action='mood': how the work feels right now."},
            "spec": {"type": "object",
                     "description": ("A walk definition: {name, graph: wordnet|manual, relations, seed: "
                                     "{mode: continue|random|word|fixed, word|node}, avoid_backtrack, edges, labels}.")},
            "method": {"type": "string", "enum": ["collide", "deep", "chaos", "spark"],
                       "description": ("Experimental exploration method for this entry. Off unless the operator "
                                       "enables plugins.entries.antemuse.settings.experimental.enabled.")},
            "seed": {"type": "string",
                     "description": ("Optional deterministic seed for an experimental method. "
                                     "Integers are accepted and kept as text.")},
            "budget": {"type": "object",
                       "description": ("Optional bounds for an experimental method: "
                                       "{calls: 0-32, tokens: 0-200000, seconds: 1-900}."),
                       "properties": {"calls": {"type": "integer"},
                                      "tokens": {"type": "integer"},
                                      "seconds": {"type": "integer"}}},
        },
        "required": ["action"],
    },
}


AUXILIARY_TASKS = (
    ("antemuse_generate", "Antemuse generation",
     "Structured generation for one Antemuse exploration branch. Experimental: called only when "
     "plugins.entries.antemuse.settings.experimental.enabled is true."),
    ("antemuse_select", "Antemuse selection",
     "Structured scoring of Antemuse candidates. A selection aid, never evidence of improvement. "
     "Experimental: called only when plugins.entries.antemuse.settings.experimental.enabled is true."),
    ("antemuse_refresh", "Antemuse refresh",
     "Structured revision of a kept Antemuse candidate, after the person asked for deeper. "
     "Experimental: called only when plugins.entries.antemuse.settings.experimental.enabled is true."),
)


def _tool_handler(host: Any):
    """Bind the tool handler to the context it was registered with.

    The handler is called by the host with arguments only, so the flag it reads
    has to travel with the function. Closing over the registration context is
    what makes the gate the invoking host's setting rather than whatever was
    registered last.
    """
    def handle(args: Dict[str, Any] | None = None, **_kwargs: Any) -> str:
        return _handler(args, host=host)

    return handle


def experimental_enabled(host: Any = None) -> bool:
    """The operator's opt-in for auxiliary exploration.

    Off unless the setting says otherwise, and off when it cannot be read: a
    failed config read must never switch a model call on. With no host in hand
    the answer is off, so a caller that cannot name the host cannot enable it.
    """
    reader = getattr(host, "get_config", None)
    if not callable(reader):
        return False
    try:
        return bool(reader("experimental.enabled", False))
    except Exception:
        return False


def _session_boundary(session_id: str = "", **_kwargs: Any) -> None:
    """A session is over: the material it prepared dies with it. Never raises."""
    try:
        session.release(session_id)
        runtime.release(session_id)
    except Exception as exc:
        logger.warning("antemuse: session %r release failed: %s", session_id, exc)


def _walks_report() -> str:
    active = (engine.watch_state() or {}).get("active") or {}
    current = active.get("walk") or "outer"
    lines = ["WALKS" + ("   (in the walk: " + current + ")" if active.get("key") == "walk" else "")]
    for w in walks.list_walks(walks.CURSOR):
        mark = "*" if w["name"] == current else " "
        lines.append(f" {mark} {w['name']:<12} {w['graph']:<8} {'/'.join(w['relations'])[:44]}")
        lines.append(f"     {w['title']}")
    lines.append("")
    lines.append(" define your own: state(action='walk_new', spec={...}) or a JSON file in "
                 + str(walks.walks_dir(walks.CURSOR)))
    return "\n".join(lines)


def _handler(args: Dict[str, Any] | None = None, host: Any = None, **_kwargs: Any) -> str:
    a = args or {}
    action = str(a.get("action") or "status").lower()
    if action == "enter":
        try:
            opts = options.parse(a)
        except ValueError as exc:
            return f"cannot enter · {exc}"
        # Only the exploration options are experimental. `block` and `allow` are
        # ordinary state arguments, so they must not need that switch.
        if any(k in opts for k in ("method", "seed", "budget")) and not experimental_enabled(host):
            return ("cannot enter with method, seed, or budget · experimental methods are off "
                    "(plugins.entries.antemuse.settings.experimental.enabled: true)")
        return engine.enter(str(a.get("name") or ""), a.get("minutes"), a.get("walk"), opts or None)
    if action == "walks":
        return _walks_report()
    if action == "walk_new":
        try:
            spec = dict(a.get("spec") or {})
            spec.setdefault("name", a.get("name") or "")
            saved = walks.save(spec, walks.CURSOR)
        except Exception as exc:
            return f"walk not saved · {exc}"
        return f"saved walk '{saved['name']}' · {saved['graph']} · {'/'.join(saved['relations'])}\n" + _walks_report()
    if action == "walk_del":
        name = str(a.get("name") or "")
        ok = walks.remove(name, walks.CURSOR)
        return (f"removed walk '{name}'" if ok else f"'{name}' is built-in or does not exist") + "\n" + _walks_report()
    if action == "break":
        return engine.take_break(a.get("name"))
    if action == "mood":
        return engine.record_mood(str(a.get("feeling") or ""), str(a.get("note") or ""))
    if action == "spark":
        # `/spark` was a person's command; the run itself belongs to the agent, which
        # is the only one who ever saw the candidates. Same handler, no command.
        return _spark_handler(host)(str(a.get("goal") or ""),
                                    session_id=str(a.get("session") or ""))
    if action == "keep":
        verdict, candidate = str(a.get("verdict") or ""), str(a.get("candidate") or "")
        if verdict not in ("love", "like", "trash") or not candidate:
            return "usage: keep love|like|trash <#n|id>  (the run account publishes #1–#n)"
        return runtime.keep(engine.current_session(), verdict, candidate)
    if action == "complete":
        # the act is done, even if the dose count disagrees: the agent is the one who
        # can see whether the move was made
        return engine.complete()
    if action == "exit":
        return engine.stop()
    if action == "list":
        return states.palette() + "\n\n" + panel.render(engine.watch_state())
    if action == "watch":
        return tui.run()
    if action == "card":
        return surfaces.card(engine.watch_state(),
                             str(a.get("name") or engine.platform() or "discord"))
    if action == "image":
        return f"MEDIA:{surfaces.snapshot_path(engine.watch_state(), str(a.get('name') or 'discord'))}\n" + surfaces.record(engine.watch_state())
    if action in ("status", ""):
        return panel.render(engine.watch_state())
    # An unrecognised action used to fall through to the status picture, so a caller
    # that mistyped got art instead of an answer. Say what exists.
    return ("no such action: " + repr(action) + ". try: enter, exit, status, list, break, "
            "mood, walks, walk_new, walk_del, spark, keep, complete, watch, card, image.")


# ------------------------------------------------------------------ hooks

def _text_of(content: Any) -> str:
    """Provider-neutral flattening: a string stays a string, block lists become text.

    Anthropic-style content blocks, OpenAI-style strings and whatever a new provider
    invents should all land here as the person's words, not as a repr of a dict.
    """
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(str(part.get("text") or part.get("content") or ""))
            elif isinstance(part, str):
                parts.append(part)
        return " ".join(p for p in parts if p).strip()
    return str(content or "").strip()


def _person_text(kwargs: Dict[str, Any]) -> str:
    """The person's own words from the turn about to be sent.

    `/note` asked a person to retype what they had already said; while a state runs
    their message *is* the note. The host passes it as ``user_message`` (confirmed in
    ``agent/turn_context.py::_collect_pre_llm_call_context``); `messages` and
    `conversation_history` are accepted as older-host fallbacks. Bounded: a state's
    account is a page, not a transcript.
    """
    direct = kwargs.get("user_message")
    if direct is not None:
        text = _text_of(direct)
        if text:
            return text[:400]
    for key in ("messages", "conversation_history"):
        history = kwargs.get(key) or []
        if not isinstance(history, list):
            continue
        for message in reversed(history):
            if not isinstance(message, dict):
                continue
            if str(message.get("role") or "").lower() not in ("user", "human", "person"):
                continue
            text = _text_of(message.get("content"))
            if text:
                return text[:400]
    return ""


#: The host context, kept only so a state can speak on its own behalf. Slash commands
#: are not the only channel: Discord caps app commands at 100 and this machine already
#: syncs 95, so an update that has to be typed is an update that may not be reachable.
_HOST: Any = None
_LAST_UPDATE = ""


def _post(text: str) -> bool:
    """Send one line through the host's own message channel, on any platform."""
    host = _HOST
    post = getattr(host, "post_message", None)
    if not callable(post) or not text:
        return False
    try:
        post(text)
        return True
    except Exception as exc:  # a platform refusing a message must not cost the turn
        logger.debug("antemuse: update not posted: %s", exc)
        return False


def _pre_llm_call(platform: str = "", session_id: str = "", **kwargs: Any) -> str | None:
    engine.remember_platform(platform, session_id)
    # Once per session, bounded and in the background: a ledger nobody fills is a ledger no
    # move can use. It returns immediately, so the turn never waits for it.
    history.autoscan(session_id or engine.current_session())
    engine.note_turn()
    engine.tick()
    said = _person_text(kwargs)
    if said:
        # Every provider hands a plugin the turn it is governing, so this is the one
        # memory-ish source that is the same under hindsight, honcho, mem0 or builtin.
        recall.remember(said, "person")
        if engine.peek():
            engine.record("person", said)
    parts = [
        engine.inject() or "",
        runtime.injection(session_id or engine.current_session(),
                          origin=engine.current_origin()) or "",
    ]
    block = "\n\n".join(part for part in parts if part)
    # A recommendation is the one thing worth pushing as its own message: it arrives
    # once per 45 minutes, and waiting for someone to type a command would defeat it.
    global _LAST_UPDATE
    advice = next((line for line in block.splitlines() if line.startswith("this looks like a ")), "")
    if advice and advice != _LAST_UPDATE:
        if _post(advice):
            _LAST_UPDATE = advice
    return block or None


def _post_tool_call(tool_name: str = "", status: str | None = None,
                    error_type: str | None = None, **kwargs: Any) -> None:
    """The only honest signal about how the work is going: did the tool work."""
    engine.note_tool(status in (None, "ok", "success") and not error_type)


def _pre_tool_call(tool_name: str = "", **kwargs: Any) -> Dict[str, Any] | None:
    return engine.policy(tool_name)


def _transform(response_text: str = "", session_id: str = "", **kwargs: Any) -> str | None:
    if response_text:
        recall.remember(response_text, "agent")
    if engine.peek():
        engine.record("agent", response_text)   # the page shows both sides
    out = engine.annotate(response_text)
    # The person's account of any run this turn. Counts, never candidates.
    # The hook's own session id wins: on a host multiplexing chats over one
    # platform, the remembered session can already belong to the next turn.
    account = runtime.take_account(session_id or engine.current_session())
    if account:
        base = out or response_text
        out = f"{base}\n\n— {account}"
    return out if out and out != response_text else None


# --------------------------------------------------------------- commands

def _enter(key: str, minutes: int | None = None):
    # The host hands every command handler the same context (source, session_id, session_key,
    # platform) when the handler names it. A command carries no turn with it, so the session has
    # to come from here — otherwise the state is filed under whichever channel spoke last, and a
    # state entered from the desktop is attributed to Discord.
    def handler(raw_args: str, session_id: str | None = None,
                session_key: str | None = None, platform: str | None = None,
                source: str | None = None) -> str:
        arg = (raw_args or "").strip()
        where = {"session": session_id or session_key or None,
                 "platform": platform or source or None}
        if arg and not arg.isdigit():
            # /walk upward  →  walk that graph; /walk 5  →  five minutes
            if key != "walk":
                return f"only /walk takes a walk name (got '{arg}')"
            line = engine.enter(key, minutes, walk=arg, **where)
            _picture()
            return line + "\n" + states.palette()
        override = int(arg) if arg.isdigit() else minutes
        line = engine.enter(key, override, **where)
        _picture()
        return line + "\n" + states.palette()
    return handler


def _picture() -> bool:
    """Post the state's picture into the chat, as its own message.

    The chat is where a person actually watches a state, so the picture belongs there
    rather than behind a command they have to remember. It is still only a picture:
    nothing from the injected material is ever rendered into it.
    """
    try:
        from core import settings, surfaces
        view = engine.watch_state()
        if not view.get("active"):
            return False
        return _post(surfaces.card(view, engine.platform() or "discord",
                                   narrow=settings.flag("picture_narrow")))
    except Exception as exc:
        logger.debug("antemuse: no picture posted: %s", exc)
        return False


def _return(_raw: str, session_id: str | None = None,
            session_key: str | None = None, **_ignored: object) -> str:
    # /return ends the state of the chat that asked, not of whichever chat was remembered.
    return engine.stop(session_id or session_key or engine.current_session())


def _state(raw: str) -> str:
    """One "show me" verb, two answers.

    `/state` is the text frame; `/state picture` is the picture — takeover in a
    terminal, the card in chat. This replaced `/states` and `/watch`, which were the
    same two answers under two more names, one of them misdescribed as a catalogue.
    """
    want = (raw or "").strip().lower()
    if want in ("picture", "image", "frame", "card"):
        if sys.stdout.isatty():
            return tui.run()
        return surfaces.card(engine.watch_state(), engine.platform() or "discord")
    if want in ("", "text", "frame-text"):
        return panel.render(engine.watch_state())
    return "usage: /state  ·  /state picture"


def _break(raw: str) -> str:
    """Recommend a state, and only recommend one.

    `/break walk` used to enter the walk, which made it a second spelling of `/walk`
    with a different name and no extra meaning. It now names the command that enters,
    so there is exactly one way to enter a state.
    """
    arg = (raw or "").strip().split()[0] if (raw or "").strip() else ""
    if not arg:
        return engine.take_break()
    if arg in states.STATES:
        return (f"/break recommends; it does not enter. Use /{arg} to enter it"
                f" (or state(action='enter', name='{arg}')).")
    return engine.take_break(arg)


def _mood(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    if not parts:
        return "usage: /mood stuck|tired|sharp|flat|saturated [what happened]"
    return engine.record_mood(parts[0], parts[1] if len(parts) > 1 else "")


def _states_shim(_raw: str) -> str:
    """`/states` meant the picture; it keeps meaning the picture while it is deprecated."""
    return _state("picture")


def _note(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return "usage: /note <what you noticed>"
    if not engine.peek():
        return "no state running — /walk first, then /note what you notice."
    engine.record("person", text)
    return panel.render(engine.watch_state())


def _spark_handler(ctx: Any):
    """`/spark <goal>` — one bounded run for one goal.

    Deterministic by default. When the operator has enabled experimental
    methods and the host exposes a structured auxiliary call, the branch path
    runs instead; if it fails, the deterministic run still happens and the
    account says what went wrong.
    """
    def handle(raw: str = "", session_id: str = "", **_kwargs: Any) -> str:
        goal = (raw or "").strip()
        if not goal:
            return "usage: /spark <what you are working on>  ·  /spark again [deepen|refresh]"
        if goal.split()[0].lower() == "again":
            # `/again` was a second command for the same run with different sources.
            rest = goal.split(None, 1)[1] if len(goal.split(None, 1)) > 1 else ""
            return _again_handler(ctx)(rest, session_id=session_id)
        # The host passes session_id to command handlers; the state record is the
        # fallback for surfaces that do not.
        key = (session_id or engine.current_session() or "").strip()
        host_llm = getattr(ctx, "llm", None)
        use_branches = (experimental_enabled(ctx)
                        and callable(getattr(host_llm, "acomplete_structured", None)))
        if use_branches:
            try:
                run = runtime.run_sync(host_llm, goal)
            except Exception as exc:
                run = runtime.plan(goal)
                run.error = f"branches unavailable: {exc}"
        else:
            try:
                run = runtime.plan(goal)
            except ValueError as exc:
                return f"no run · {exc}"
        if not runtime.prepare(key, run, origin=engine.current_origin()):
            return run.account() + " · not bound (no session)"
        return run.account()

    return handle


def _keep(raw: str = "", **_kwargs: Any) -> str:
    parts = (raw or "").split()
    if len(parts) < 2:
        return "usage: /keep love|like|trash <candidate-id>"
    return runtime.keep(engine.current_session(), parts[0].lower(), parts[1])


def _again_handler(ctx: Any):
    """`/again [deepen|refresh]` — re-run the last goal with the sources your
    verdicts point at. Reports the routing when it cannot run it.
    """
    def handle(raw: str = "", session_id: str = "", **_kwargs: Any) -> str:
        key = (session_id or engine.current_session() or "").strip()
        strategy = runtime.next_strategy(key)
        if strategy is None:
            return "nothing loved or liked yet · /keep love|like <#n> first"
        asked = (raw or "").strip().lower()
        if asked and asked != strategy:
            return f"feedback routes to {strategy}, not {asked}"
        goal = runtime.last_goal(key)
        if not goal:
            return f"feedback routes to {strategy} · no goal to run it against yet"

        ids = runtime.feedback_ids(key)
        host_llm = getattr(ctx, "llm", None)
        use_branches = (experimental_enabled(ctx)
                        and callable(getattr(host_llm, "acomplete_structured", None)))
        try:
            if use_branches:
                run = runtime.run_sync(host_llm, goal, method=strategy, strategy=strategy,
                                       loved=ids["loved"], liked=ids["liked"])
            else:
                run = runtime.plan(goal, method=strategy, strategy=strategy,
                                   loved=ids["loved"], liked=ids["liked"])
        except ValueError as exc:
            return f"no run · {exc}"
        if not runtime.prepare(key, run, origin=engine.current_origin()):
            return run.account() + " · not bound (no session)"
        return run.account()

    return handle


def register(ctx) -> None:
    global _HOST
    _HOST = ctx
    settings.bind(ctx)
    engine.settle()

    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_hook("transform_llm_output", _transform)
    ctx.register_hook("post_tool_call", _post_tool_call)

    # A session boundary is a place where prepared material would otherwise
    # outlive its turn. All four releases do the same thing: drop what that
    # session bound. They are registered unconditionally because releasing
    # nothing is the correct behaviour when nothing was prepared.
    for hook in ("on_session_end", "on_session_finalize", "on_session_reset", "on_session_delete"):
        try:
            ctx.register_hook(hook, _session_boundary)
        except Exception as exc:
            # An older host may not know every boundary. Losing one is a real
            # gap, so it is logged rather than swallowed.
            logger.warning("antemuse: session hook %s not registered: %s", hook, exc)

    # Declaring the routes is not calling them: this only creates the
    # auxiliary-task picker entries and config blocks. Actual calls stay behind
    # experimental_enabled(); a host without the API still loads the plugin.
    declare = getattr(ctx, "register_auxiliary_task", None)
    if callable(declare):
        for key, display, description in AUXILIARY_TASKS:
            try:
                declare(key, display_name=display, description=description, defaults={"timeout": 60})
            except Exception as exc:
                # A refused or unavailable auxiliary task must not stop the
                # plugin loading: nothing at runtime depends on the route yet.
                # It is still logged, because a silent miss hides a real error.
                logger.warning("antemuse: auxiliary task %s not registered: %s", key, exc)

    ctx.register_tool(
        name="state",
        toolset="state",
        description=STATE_SCHEMA["description"],
        handler=_tool_handler(ctx),
        schema=STATE_SCHEMA,
    )

    for key in states.STATES:
        ctx.register_command(
            name=key,
            handler=_enter(key),
            description=f"Enter the {key} state ({states.STATES[key]['contract']})",
            args_hint="[minutes]",
            argument_mode="text",
        )

    ctx.register_command(name="return", handler=_return,
                         description="End the current state and keep its residue")

    # Five commands. Everything else a person might want is automatic: their message
    # is journalled as a note while a state runs, the recommendation line arrives in
    # the turn by itself, and exploration runs through the tool the agent already has.
    # The picture arrives with the state; there is nothing to ask for.


    try:
        from pathlib import Path
        ctx.register_skill(
            "antemuse",
            Path(__file__).resolve().parent / "SKILL.md",
            description="Take and leave agent states: walk, daydream, doomscroll, unstuck, dream.",
        )
    except Exception:
        pass
