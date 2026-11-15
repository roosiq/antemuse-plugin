"""Where walk material comes from."""
from __future__ import annotations

import importlib.util
from typing import List


def ready(kind: str) -> str | None:
    """Why the walk cannot run, or None when its WordNet graph is available."""
    if kind != "walk":
        return None
    if importlib.util.find_spec("nltk") is None:
        return ("nltk is not importable in the interpreter Hermes runs. "
                "Install it there, then restart Hermes: "
                "uv pip install --python \"$(python3 -c 'import sys;print(sys.executable)')\" "
                "'nltk>=3.8,<4'")
    import nltk
    for target in ("corpora/wordnet", "corpora/wordnet.zip"):
        try:
            nltk.data.find(target)
            return None
        except Exception:
            continue
    return ("the wordnet corpus is not installed for nltk. "
            "Run: python3 -c \"import nltk; nltk.download('wordnet')\"")


def walk_text(steps: int = 1) -> List[str]:
    """Run the selected walk; a path is recorded but never injected as material."""
    from . import engine, walks
    active = engine.watch_state().get("active") or {}
    name = str(active.get("walk") or "wander")
    try:
        return walks.get(name).step(steps)
    except Exception as exc:
        try:
            engine.record("state", f"walk '{name}' produced nothing · "
                          f"{type(exc).__name__}: {str(exc).splitlines()[0][:90]}", event="walk")
        except Exception:
            pass
        return []


# Only agent states have providers. Explore has no provider because its material is what the
# person picked in the cockpit, and it ends only on /return.
PROVIDERS = {"walk": walk_text}
