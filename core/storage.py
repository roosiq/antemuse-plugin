"""Where a state lives on disk.

The active state is one `state.json` per profile rather than per-session state
because policy is agent-wide: a per-session copy would let the agent be walking
in one place and unrestricted in the next. Rendering follows origin; policy does
not. `engine` owns that file; everything else a state produces — journal frames,
photographs, saved walks — is written beside it in the same directory.
"""
from __future__ import annotations

import os
from pathlib import Path

PLUGIN_NAME = "antemuse"
ENV_HOME = "ANTEMUSE_STATES_HOME"


def data_dir() -> Path:
    """The plugin data dir, or an explicit override for tests and tinkering."""
    override = os.environ.get(ENV_HOME)
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    try:
        from plugins.plugin_storage import plugin_data_dir  # type: ignore
        return plugin_data_dir(PLUGIN_NAME)
    except Exception:  # standalone/test use
        path = Path.home() / ".antemuse"
        path.mkdir(parents=True, exist_ok=True)
        return path
