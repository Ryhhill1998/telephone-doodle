"""Errors about finding a room or a player, as opposed to a rule a game broke.

`game_engine.GameError` and its subclasses cover "this message is not legal
right now"; these two cover "there is no room or player to send it to", which
`game_engine` has no concept of. `api` turns both families into a response.
"""

from __future__ import annotations

__all__ = ["InvalidToken", "RoomError", "RoomNotFound"]


class RoomError(Exception):
    """Base class for routing failures `rooms` can raise."""


class RoomNotFound(RoomError):
    """No live room holds this code."""


class InvalidToken(RoomError):
    """The token does not match any player currently seated in this room."""
