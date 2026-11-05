"""`python -m antemuse_states` — open the takeover straight from any shell."""
from __future__ import annotations

import sys

if __package__ in (None, ""):
    sys.path.insert(0, "/home/ryan/antemuse-states")

from kitchen import tui

if __name__ == "__main__":
    print(tui.run())
