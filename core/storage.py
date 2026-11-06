"""Where a state lives on disk: one active record per profile.

The active state is a single file rather than per-session state because policy
is agent-wide: a per-session copy would let the agent be walking in one place
and unrestricted in the next. Rendering follows origin; policy does not.

Everything else a state produces — journal frames, photographs, saved walks —
is written beside it under the same directory.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

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


def _active_path() -> Path:
    return data_dir() / "active.json"


def load_active() -> Dict[str, Any] | None:
    path = _active_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def save_active(state: Dict[str, Any] | None) -> None:
    path = _active_path()
    if state is None:
        path.unlink(missing_ok=True)
        return
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(path)
