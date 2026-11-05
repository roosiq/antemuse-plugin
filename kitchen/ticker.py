"""Periodic events while a state is running.

A daemon thread, one per process, asks the state's provider for material on its
cadence and writes it into the journal as `who="state"`. No model calls: the
thread is the clock, the sources are the content.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional

from . import definitions, engine, sources

_LOCK = threading.Lock()
_STOP: Optional[threading.Event] = None
_THREAD: Optional[threading.Thread] = None
_KEY: str = ""


def _loop(stop: threading.Event, key: str, cadence: float) -> None:
    provider = sources.PROVIDERS.get(key)
    if provider is None:
        return
    # first event quickly: a state that is silent for 18s reads as broken
    delay = min(2.5, cadence)
    while not stop.wait(delay):
        try:
            for line in provider(1):
                engine.record("state", line, event=key)
        except Exception as exc:  # a provider failing must not kill the state
            engine.record("state", f"{key} provider failed · {exc}", event=key)
        delay = cadence
        if engine.peek() is None:
            return


def start(key: str, cadence: Optional[float] = None) -> bool:
    """Start emitting for `key`; replaces any previous ticker."""
    global _STOP, _THREAD, _KEY
    stop()
    spec = definitions.STATES.get(key)
    if not spec:
        return False
    delay = float(cadence if cadence is not None else spec.get("cadence", 20))
    with _LOCK:
        _STOP = threading.Event()
        _KEY = key
        _THREAD = threading.Thread(
            target=_loop, args=(_STOP, key, delay), daemon=True, name=f"antemuse-{key}"
        )
        _THREAD.start()
    return True


def stop() -> None:
    global _STOP, _THREAD, _KEY
    with _LOCK:
        if _STOP is not None:
            _STOP.set()
        _STOP = None
        _THREAD = None
        _KEY = ""


def running() -> bool:
    return _THREAD is not None and _THREAD.is_alive()
