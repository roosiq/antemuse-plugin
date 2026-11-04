"""Optional engine deal: ask concept.cooking for reference cards ("the par").

The public MCP endpoint is stateless (no session header, no initialize needed for
a bare tools/call). On any failure we return source="deck" and the error string:
a starter-direction fallback is never presented as engine output, because that
is how the live site currently degrades and it would corrupt the game.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List

DEFAULT_URL = "https://concept.cooking/mcp"
TIMEOUT = 20


def _call(url: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "cook_ideas", "arguments": arguments},
    }).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
            "user-agent": "hermes-concept-kitchen/0.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        body = json.loads(response.read().decode())
    if "error" in body:
        raise RuntimeError(str(body["error"].get("message") or body["error"]))
    result = body.get("result") or {}
    content = result.get("content") or []
    if not content:
        raise RuntimeError("empty MCP result")
    text = content[0].get("text") or ""
    if result.get("isError"):
        raise RuntimeError(text.strip() or "engine error")
    return json.loads(text)


def deal(move: str, seed: str, distance: str, context: str, limit: int = 3,
         url: str = DEFAULT_URL) -> Dict[str, Any]:
    arguments = {
        "seed": seed[:500],
        "technique": move if move in ("unpack", "connect", "flip", "shift") else "quick_mix",
        "distance": distance if distance in ("near", "lateral", "far", "mixed") else "mixed",
        "context": context if context in ("open", "daily_life", "work", "creative_practice") else "open",
        "limit": max(1, min(6, limit)),
    }
    try:
        payload = _call(url, arguments)
    except Exception as exc:  # noqa: BLE001 - any failure means: play from the deck
        return {"source": "deck", "cards": [], "error": _short(exc)}
    cards: List[Dict[str, Any]] = []
    for card in (payload.get("cards") or [])[:limit]:
        cards.append({
            "title": str(card.get("title") or "").strip(),
            "direction": str(card.get("direction") or "").strip(),
            "why": str(card.get("whyItConnects") or card.get("why_it_connects") or "").strip(),
            "try_next": str(card.get("tryNext") or card.get("try_next") or "").strip(),
        })
    if not cards:
        return {"source": "deck", "cards": [], "error": "engine returned no cards"}
    return {"source": "engine", "cards": cards, "error": ""}


def _short(exc: Exception) -> str:
    text = str(exc).strip().replace("\n", " ")
    return (text[:160] + "…") if len(text) > 160 else text
