"""The settings a person may change, read through the host, clamped, never guessed.

Declared in `plugin.yaml`'s `config_schema`, which the Hermes desktop app renders as a
form under Settings ▸ Plugins ▸ Antemuse and writes to
`plugins.entries.antemuse.settings.<key>`. There is no second settings store: the plugin
reads what the host stored, and the schema is the single definition of the surface.

A setting may change how loud or how long a state is. It may not change what a state is.
"""
from __future__ import annotations

from typing import Any, Dict

_TRUE = {"1", "true", "yes", "on", "t"}

#: (key, default, low, high) — bounds are clamped in both directions.
INT_BOUNDS = {
    "recommend_cooling_turns": (10, 2, 60),
    "long_stretch_turns": (0, 0, 200),
    "journal_cap": (60, 20, 60),
}
BOOL_DEFAULTS = {
    "recommend_enabled": True,
    # Recommendations are measured either way; this decides whether they are ever
    # shown. Off by default: the plugin observes, it does not tell the person what to do.
    "show_recommendations": False,
    "suggest_autofollow": False,
    # The past-session scan reads recent session text as daydream/dream material. On by
    # default (it is the plugin's own well), and off here rather than through an environment
    # variable: a person's control belongs in the settings form, not in their shell.
    "session_scan": True,
}

#: Free-text settings. Only ones that are a list or a path, never a secret: a secret belongs
#: in requires_env, where the host keeps it.
TEXT_DEFAULTS = {
    "dream_projects": "",
}

_host: Any = None
_warned: set = set()
#: Test-only: the suite has no host to bind, and a scan that ran for real would read the
#: developer's own sessions. Production code never writes this.
_OVERRIDES: Dict[str, Any] = {}


def override(**values: Any) -> None:
    """Set settings without a host. Tests only."""
    _OVERRIDES.update(values)


def clear_overrides() -> None:
    _OVERRIDES.clear()


def bind(ctx: Any) -> None:
    """Keep the host context so reads go through it, not through a file."""
    global _host
    _host = ctx


def _raw(key: str, default: Any) -> Any:
    if key in _OVERRIDES:
        return _OVERRIDES[key]
    host = _host
    get = getattr(host, "get_config", None)
    if callable(get):
        try:
            return get(key, default)
        except Exception:
            return default
    return default


def flag(key: str) -> bool:
    default = BOOL_DEFAULTS.get(key, False)
    value = _raw(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in _TRUE
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def text(key: str, default: str = "") -> str:
    """A plain string setting. Unknown keys fall back — a typo in config is not a crash."""
    if not default:
        default = TEXT_DEFAULTS.get(key, default)
    value = _raw(key, default)
    return str(value) if isinstance(value, (str, int, float)) else default


def number(key: str) -> int:
    default, low, high = INT_BOUNDS[key]
    value = _raw(key, default)
    try:
        got = int(value)
    except Exception:
        got = default
    # long_stretch_turns treats 0 as "keep the measured threshold", so the floor there
    # is 0 or 5..200: a three-turn override is not a stretch, it is a fidget.
    if key == "long_stretch_turns" and 0 < got < 5:
        got = 5
    clamped = max(low, min(high, got))
    if clamped != got and key not in _warned:
        _warned.add(key)
        try:
            import logging
            logging.getLogger(__name__).warning(
                "antemuse: settings.%s=%r out of range, using %d", key, value, clamped)
        except Exception:
            pass
    return clamped


def all_values() -> Dict[str, Any]:
    out: Dict[str, Any] = {k: flag(k) for k in BOOL_DEFAULTS}
    out.update({k: number(k) for k in INT_BOUNDS})
    out.update({k: text(k) for k in TEXT_DEFAULTS})
    return out


def reset_warnings() -> None:
    _warned.clear()
