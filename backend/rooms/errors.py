"""Errors about finding a room or a player, as opposed to a rule a game broke.

`game_engine.GameError` and its subclasses cover "this message is not legal
right now"; these cover "there is no room or player to send it to", which
`game_engine` has no concept of. `api` turns both families into a response.
"""

from __future__ import annotations

__all__ = ["InvalidToken", "RoomError", "RoomGone", "RoomNotFound"]


class RoomError(Exception):
    """Base class for routing failures `rooms` can raise."""


class RoomNotFound(RoomError):
    """No live room holds this code, and none can be loaded for it either."""


class RoomGone(RoomError):
    """This instance's copy of the room was just dropped mid-request.

    Raised when a version-guarded snapshot write loses to another instance:
    the room is already gone from memory and every one of its sockets is
    already closed with 1012 by the time this reaches the caller, so there
    is nothing left to retry against on this instance.
    """


class InvalidToken(RoomError):
    """The token does not match any player currently seated in this room."""
