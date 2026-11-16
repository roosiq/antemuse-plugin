"""Explicit credentials for development experiments.

These scripts use only ``NOUS_ACCESS_TOKEN`` supplied by the operator. They never
consult Hermes configuration or credential files.
"""
from __future__ import annotations

import os


def require_nous_token() -> str:
    """Return the experiment token or stop before a request can be made."""
    token = os.environ.get("NOUS_ACCESS_TOKEN")
    if not token:
        raise SystemExit(
            "NOUS_ACCESS_TOKEN is required for a remote Nous experiment; set it explicitly."
        )
    return token
