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
# The host process (gateway, desktop main) does not necessarily sit in the directory the
# agent is working in: its cwd is wherever it was launched from, often $HOME. The calling
# session's cwd is the honest answer and the host can supply it (see
# set_session_cwd_provider); the environment is the fallback for hosts that only export it.
ENV_WORKDIR = ("ANTEMUSE_PROJECT_ROOT", "TERMINAL_CWD")
_SESSION_CWD = None


def set_session_cwd_provider(fn) -> None:
    """Let the host hand us the *calling session's* cwd.

    The plugin's own process is the gateway, and its cwd is wherever the gateway was
    launched from — on this machine the operator's home, a dotfiles repository with no
    commits, so `dream` refused with "fewer than three local git commit subjects"
    while the chat sat inside a repository with fourteen. The host exposes
    `ctx.session_cwd()` for exactly this; the plugin registers it here at setup.
    """
    global _SESSION_CWD
    _SESSION_CWD = fn if callable(fn) else None


def _workdir() -> Path:
    candidates = []
    if _SESSION_CWD is not None:
        try:
            candidates.append(_SESSION_CWD())
        except Exception:
            pass
    candidates.extend(os.environ.get(name) or "" for name in ENV_WORKDIR)
    for raw in candidates:
        raw = (raw or "").strip()
        if raw:
            try:
                candidate = Path(raw).expanduser()
            except Exception:
                continue
            if candidate.is_dir():
                return candidate
    return Path.cwd()


def project_root(start: Path | None = None) -> Path | None:
    """The repository the agent is working in: nearest ancestor holding .git."""
    here = Path(start or _workdir()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def project_dir(start: Path | None = None) -> Path | None:
    """Where this project's artifacts go, or None when there is no project.

    Nothing here is policy: the state record stays single and global because a
    per-project copy would let the agent be walking in one directory and
    unrestricted in the next. Rendering and cursors follow origin.
    """
    if os.environ.get(ENV_HOME):
        return None                      # an explicit home overrides everything
    root = project_root(start)
    if root is None:
        return None
    path = root / ".antemuse"
    path.mkdir(parents=True, exist_ok=True)
    return path


def hermes_home() -> Path:
    """The active Hermes home: the host's own resolver first, then env, then default.

    Plugins must not assume ``~/.hermes``: profiles and ``HERMES_HOME`` move it, and a
    plugin that hardcodes the path writes one profile's data into another's.
    """
    try:
        from hermes_constants import get_hermes_home  # type: ignore
        return Path(get_hermes_home())
    except Exception:
        override = os.environ.get("HERMES_HOME")
        return Path(override) if override else Path.home() / ".hermes"


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
    except Exception:  # standalone/test use: the same tree the host would use
        path = hermes_home() / "plugin-data" / PLUGIN_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path
