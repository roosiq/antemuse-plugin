"""How a finished state is handed back to be spoken.

The plugin knows the facts. The model knows how to say them. So the plugin never writes the
sentence itself: it hands over what happened and the voice it should be said in, and the model
speaks in the turn it was already going to take. One line, said once.

Voice rules come from docs/brand.md: sentence case, the agent in the third person when the
person is the audience, the person in the second, no exclamation marks, short, and never explain
the mechanism. The account names the steps; it never quotes the material.
"""
from __future__ import annotations

from typing import Any, Dict

PREFIX = "[ANTEMUSE REPORT]"


def directive(report: Dict[str, Any], label: str = "") -> str:
    """The block text that asks the model to say what the state did, in the house voice."""
    what = (label or report.get("state") or "state").upper()
    facts = str(report.get("text") or "").strip()
    return "\n".join([
        f"{PREFIX} A state has just ended. Tell the person what the agent did.",
        f"Facts: {facts}",
        f"Say it in one line, sentence case, starting \"{what} ended · \". "
        "The agent in the third person (\"the agent walked\"), the person in the second. "
        "No exclamation marks. Name the steps it took.",
        "Do not quote the material the state supplied, and do not explain how the state works. "
        "One line, then carry on with what the person asked.",
    ])
