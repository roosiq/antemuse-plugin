"""Open the full-screen takeover straight from a shell.

    python3 __main__.py          # from this directory
    ./bin/antemuse               # from anywhere
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import tui

if __name__ == "__main__":
    print(tui.run())
