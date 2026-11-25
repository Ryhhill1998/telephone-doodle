"""Live rooms: the engine's in-memory half, and the only thing `api` talks to.

`rooms` sits between `api` and the two packages below it (BUILD_PLAN.md,
section 2): it calls `game_engine` for the rules and `storage` for the two
writes a room makes (created, finished), and translates between the engine's
models and the plain rows `storage` deals in. `api` never touches
`game_engine` or `storage` directly.
"""

from game_engine import GameError, NotAllowed, Player, WrongPhase
from rooms.codes import ALPHABET, CODE_LENGTH, generate_code
from rooms.errors import InvalidToken, RoomError, RoomGone, RoomNotFound
from rooms.manager import Room, RoomManager

__all__ = [
    "ALPHABET",
    "CODE_LENGTH",
    "GameError",
    "InvalidToken",
    "NotAllowed",
    "Player",
    "Room",
    "RoomError",
    "RoomGone",
    "RoomManager",
    "RoomNotFound",
    "WrongPhase",
    "generate_code",
]
