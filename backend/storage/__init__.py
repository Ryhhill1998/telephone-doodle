"""Postgres access for Telephone Doodle.

Everything that touches the database lives here: the connection pool, the
schema, and plain SQL for the handful of things the app stores. No ORM and no
migration tool (BUILD_PLAN.md, Step 3).

`storage` and `game_engine` are *siblings* in the dependency order, not a
stack: neither may import the other, and `rooms` sits above both and
translates between them. That is why nothing here mentions `Game`, `Book` or
`Page` -- a finished game arrives as the plain rows this package defines.
"""

from storage.database import ActiveGame, Database, RoomCodeTaken
from storage.schema import ACTIVE_CODE_INDEX, SCHEMA_SQL, TABLES, GameStatus

__all__ = [
    "ACTIVE_CODE_INDEX",
    "SCHEMA_SQL",
    "TABLES",
    "ActiveGame",
    "Database",
    "GameStatus",
    "RoomCodeTaken",
]
