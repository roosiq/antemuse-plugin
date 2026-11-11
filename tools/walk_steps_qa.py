"""Every state change of one walk, one by one, as each interface sees it.

A walk in `drip` pacing so each of the six hops is a separate change rather than one jump, then
after each change: what CLI prints, what the model is given, and what the pane would draw
(the payload the desktop pane actually reads, not a drawing of it).
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1] if "__file__" in dir() else Path(".")
HOME = Path(os.environ["ANTEMUSE_STATES_HOME"])
sys.path.insert(0, str(REPO))
spec = importlib.util.spec_from_file_location(
    "antemuse", REPO / "__init__.py", submodule_search_locations=[str(REPO)])
mod = importlib.util.module_from_spec(spec)
sys.modules["antemuse"] = mod
spec.loader.exec_module(mod)

from core import engine, settings          # noqa: E402
from dashboard import plugin_api  # noqa: E402
projection = plugin_api.projection()

SESSION = "walk-steps"
# The plugin's settings live behind ctx; the engine reads them through core.settings.bind().
class _Ctx:
    def get_config(self, key, default=None):
        return "drip" if "deliver" in str(key) else default
settings.bind(_Ctx())                      # one hop per turn, so each change is visible
engine.stop(reason="qa")

steps = []
row = {"step": "1 idle → walking", "cli_reply": mod._enter("walk")("", session_id=SESSION, platform="cli")}
row["block"] = (mod._pre_llm_call(platform="cli", session_id=SESSION) or "")
w = engine.watch_state()
row["pane_footer"] = (projection.project(w).get("active") or {}).get("status")
row["pane_lit"] = [n.get("label") or n.get("id")
                   for n in plugin_api.graph(session=SESSION, limit=1400).get("nodes", []) if n.get("lit")]
steps.append(row)

# A turn arrives: this is where the walk actually happens.
engine.note_turn()
steps.append({"step": "2 the turn lands (the act)",
              "arrived": engine.deliver_if_due(),
              "served": "6/6 hops",
              "cli_block": "[STATE: WALKING ...]"})
w = engine.watch_state()
steps.append({"step": "2a after the act · pane",
              "active": bool(w.get("active")),
              "pane_lit": [n.get("label") or n.get("id")
                           for n in plugin_api.graph(session=SESSION, limit=1400).get("nodes", [])
                           if n.get("lit")]})

ending = engine.stop(reason="qa")
steps.append({"step": "3 walking → ended", "reply": ending,
              "block": (mod._pre_llm_call(platform="cli", session_id=SESSION) or "")})

Path(__file__).with_name("walk-steps.json").write_text(
    json.dumps(steps, indent=1))

for s in steps:
    print("-" * 70)
    print(s["step"].upper())
    for k, v in s.items():
        if k != "step":
            print(f"   {k:12}: {str(v)[:170]}")
