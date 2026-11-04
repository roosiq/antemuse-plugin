"""The full loop: five rounds, a chain, a board row, and an honest engine failure."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["CONCEPT_KITCHEN_HOME"] = tempfile.mkdtemp(prefix="ck-game-")

from kitchen import game, store  # noqa: E402


def setup_function(_):
    game.configure({"use_engine": False, "word_budget": 60})
    store.save_active(None)


def test_service_chains_five_rounds_and_lands_on_the_board():
    p = game.player("tester", kind="human")
    brief = game.start(p)
    assert "round 1/5" in brief
    assert "engine disabled" in brief

    sparks = [
        ("Ask one better question first", "Instead of assuming the request is ready, the plugin withholds the answer until one vague noun is concrete, because the follow-up is the product.", "Write one follow-up question for the next request by Friday."),
        ("Withhold until the noun is concrete", "Rather than accepting the first phrasing, it forces the user to name the thing they mean, which lets a vague ask become a testable one.", "Ask two clarifying questions before the next build."),
        ("Give the question to the person who will answer it", "Normally the asker writes the question; shift the actor so the person who will do the work writes it, because they know which noun is vague.", "Send the draft question to one builder before the next standup."),
        ("Borrow the triage desk's first move", "Borrowed from an emergency department, the first move sorts by reversibility rather than by who is asking, so loud requests stop winning.", "Sort the next ten requests by how hard they are to undo."),
        ("Reverse the definition of answered", "Instead of assuming an answer ends the exchange, reverse the success condition: it is answered when the asker can restate the question in their own words.", "Test one reply by asking the user to restate it by Friday."),
    ]
    for i, (title, why, nxt) in enumerate(sparks):
        text = f"{title} :: {why} :: {nxt}"
        out = game.submit(p, text)
        if i < 4:
            assert f"round {i + 2}/5" in out, out
        else:
            assert "SERVICE COMPLETE" in out, out

    assert store.load_active() is None
    rows = store.leaderboard()
    assert rows and rows[0]["player"] == "tester"
    assert rows[0]["sparks"] == 5


def test_agent_and_human_share_one_board():
    game.configure({"use_engine": False})
    human = game.player("ryan", kind="human")
    agent = game.player("kitchen-agent", kind="agent", model="terra")
    game.start(human)
    game.submit(human, "Name the cost out loud :: The overlooked ingredient is the maintenance nobody budgeted, because it is paid by a different team, which is why it stays invisible. :: Write the maintenance line into the next two estimates.")
    game.pass_service(agent)
    game.start(agent)
    game.submit(agent, "Publish the maintenance bill :: Instead of assuming the feature is free after launch, reverse the resource dimension and show the yearly upkeep next to the price, so buyers compare the whole cost. :: Add one upkeep number to the pricing page by Friday.")

    names = {row["player"]: row for row in store.leaderboard()}
    assert names["ryan"]["kind"] == "human"
    assert names["kitchen-agent"]["kind"] == "agent"
    assert names["kitchen-agent"]["model"] == "terra"


def test_submission_needs_three_parts():
    p = game.player("tester", kind="human")
    game.start(p)
    out = game.submit(p, "just a title")
    assert "THREE PARTS" in out


def test_engine_failure_is_labelled_not_faked():
    game.configure({"use_engine": True, "engine_url": "http://127.0.0.1:9/mcp"})
    p = game.player("tester", kind="human")
    out = game.start(p)
    assert "PAR   deck" in out
    assert "engine unavailable" in out
