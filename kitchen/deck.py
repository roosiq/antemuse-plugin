"""Seed deck and service structure.

A service is five rounds. Moves are fixed so the ladder teaches one skill at a
time; the seed for round n+1 is the player's own round-n spark, so the chain is
the score that keeps compounding.

The deck exists so the game is playable with no network. It is never presented
as engine output: rounds are labelled `engine` or `deck`.
"""
from __future__ import annotations

import hashlib
import random
from typing import Dict, List

SEEDS: List[str] = [
    "a plugin that refuses to answer until it has asked one better question",
    "a way to make a long train ride feel like a working day",
    "a small kitchen appliance that improves with age",
    "a tool for noticing when a document has stopped meaning anything",
    "a neighbourhood service that runs on gossip",
    "a way to prove a meeting was unnecessary",
    "a library that lends attention instead of books",
    "a receipt for a conversation",
    "a version of a notebook that forgets on purpose",
    "a way to price a favour",
    "a garden that reports its own neglect",
    "a game where the score is how few moves you used",
    "a mechanism for handing a decision to the person most affected by it",
    "a way to make an apology auditable",
    "an editor that argues back once and then stops",
    "a way to see which of your habits is load-bearing",
    "a machine that converts boredom into a plan",
    "a shop that only sells unfinished things",
    "a way to rehearse a hard conversation without anyone's feelings",
    "a rule that makes a group slower but wiser",
    "a way to keep a good idea alive when its author leaves",
    "a lunch break that changes what you think about the afternoon",
    "a way to tell a fresh idea from a remembered one",
    "a small ceremony for deleting something important",
]

MOVES: List[str] = ["unpack", "flip", "shift", "connect", "flip"]
DISTANCES: List[str] = ["near", "lateral", "lateral", "far", "far"]
CONTEXTS: List[str] = ["work", "daily_life", "creative_practice", "open", "work"]

ROUNDS = 5


def deal_seed(service_id: str, round_no: int, previous_seed: str | None = None) -> str:
    if previous_seed:
        return previous_seed
    digest = hashlib.sha256(f"{service_id}:{round_no}".encode()).hexdigest()
    return SEEDS[int(digest[:8], 16) % len(SEEDS)]


def round_spec(service_id: str, round_no: int, previous_seed: str | None = None) -> Dict:
    i = max(0, min(round_no - 1, ROUNDS - 1))
    return {
        "service": service_id,
        "round": round_no,
        "rounds": ROUNDS,
        "move": MOVES[i],
        "expected_distance": DISTANCES[i],
        "context": CONTEXTS[i],
        "seed": deal_seed(service_id, round_no, previous_seed),
    }


def new_service_id(rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return "svc_" + "".join(rng.choice("abcdefghijkmnpqrstuvwxyz23456789") for _ in range(6))
