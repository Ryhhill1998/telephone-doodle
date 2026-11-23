"""Postgres access for Telephone Doodle.

Everything that touches the database lives here: the connection pool, the
schema, and plain SQL for the handful of things the app stores. No ORM and no
migration tool (BUILD_PLAN.md, Step 3).

`storage` and `game_engine` are *siblings* in the dependency order, not a
stack: neither may import the other, and `rooms` sits above both and
translates between them. That is why nothing here mentions `Game`, `Book` or
`Page` -- a finished game arrives as the plain rows this package defines.
"""

from storage.database import Database
from storage.schema import SCHEMA_SQL, TABLES

__all__ = [
    "SCHEMA_SQL",
    "TABLES",
    "Database",
]
