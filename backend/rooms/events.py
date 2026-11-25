"""Structured logging: one JSON object per line, to stdout.

Cloud Run ships stdout to Cloud Logging for free, so this is the whole
observability story for v0 (BUILD_PLAN.md, Step 4). Event names are fixed so a
later dashboard can filter on them; `rate_limited` and `snapshot_conflict` are
listed even though nothing raises them until Steps 5 and 6, so those steps add
a call site rather than inventing a new convention.

Never pass a player's name or any drawing content here -- seat indexes, codes
and counts only.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Literal

__all__ = ["Event", "log_event"]

Event = Literal[
    "room_created",
    "room_loaded",
    "player_joined",
    "game_started",
    "game_finished",
    "ws_connected",
    "ws_closed",
    "snapshot_conflict",
    "stale_games_deleted",
    "rate_limited",
]


def log_event(event: Event, **fields: Any) -> None:
    print(json.dumps({"event": event, **fields}), file=sys.stdout, flush=True)
