"""Shared fixtures for the storage tests.

These run against a real Postgres -- the container from
`docker-compose.dev.yml` locally (`make db`), the service container in CI --
because the things worth testing here are the things only Postgres decides: a
partial unique index, a version-guarded `UPDATE`, a transaction that has to be
all or nothing. A fake would only test the fake.
"""

import os
from collections.abc import AsyncIterator
from typing import Any

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row

from storage import TABLES, BookRow, Database, GameStatus, PageRow, PlayerRow


@pytest.fixture
async def db() -> AsyncIterator[Database]:
    """A `Database` pointed at an empty schema.

    Function-scoped deliberately. psycopg's async pool belongs to the event
    loop it was opened in, and pytest-asyncio gives every test a fresh loop, so
    a session-scoped pool would outlive its loop and hang on first use.
    Opening one against local Postgres costs a few milliseconds.
    """
    database = Database.from_env()
    await database.connect()
    await database.create_schema()
    await _truncate()

    yield database

    await database.close()


@pytest.fixture
async def conn(db: Database) -> AsyncIterator[psycopg.AsyncConnection]:
    """A connection for tests to look at the database with.

    Separate from the pool inside `Database` so that assertions read committed
    state from outside, the way another instance would.
    """
    async with await psycopg.AsyncConnection.connect(
        os.environ["DATABASE_URL"], autocommit=True, row_factory=dict_row
    ) as connection:
        yield connection


async def _truncate() -> None:
    """Empty every table before a test runs.

    Kept out of `Database` on purpose: wiping the database is something only
    the harness needs, and production code should not ship a method that can.
    """
    async with await psycopg.AsyncConnection.connect(
        os.environ["DATABASE_URL"], autocommit=True
    ) as connection:
        await connection.execute(
            sql.SQL("TRUNCATE {}").format(sql.SQL(", ").join(map(sql.Identifier, TABLES)))
        )


# -- a game worth storing ------------------------------------------------
#
# Three players, three books, three rounds. Shared by the tests that write a
# finished game and the ones that check it survives the housekeeping.

STROKES: dict[str, Any] = {
    "v": 1,
    "w": 800,
    "h": 600,
    "ops": [{"t": "brush", "c": "#C8381F", "s": 12, "p": [[0.1, 0.2], [0.3, 0.4]]}],
}

PLAYERS = [PlayerRow(idx=0, name="Jo"), PlayerRow(idx=1, name="Sam"), PlayerRow(idx=2, name="Ali")]

BOOKS = [
    BookRow(idx=0, owner_idx=0, word="penguin"),
    BookRow(idx=1, owner_idx=1, word="volcano"),
    BookRow(idx=2, owner_idx=2, word="toaster"),
]

# Three books, three rounds, in the order the reveal walks them: book by book,
# page by page. Round 0 is a drawing, round 1 a guess, round 2 a drawing again.
# The seat holding book `b` in round `r` is `(b + r) % n`, the inverse of the
# engine's `book_index`.
PAGES = [
    PageRow(
        book_idx=book,
        round=rnd,
        author_idx=(book + rnd) % 3,
        kind="text" if rnd % 2 else "strokes",
        text=f"guess {book}" if rnd % 2 else None,
        strokes=None if rnd % 2 else STROKES,
    )
    for book in range(3)
    for rnd in range(3)
]


async def played(db: Database, code: str = "KQFM") -> str:
    """A game taken from creation to the point of finishing."""
    game_id = await db.create_game(code)
    await db.save_snapshot(
        game_id,
        status=GameStatus.IN_PROGRESS,
        host_idx=0,
        player_count=3,
        snapshot={"phase": "reveal", "players": [{"token": "secret"}]},
        expected_version=0,
    )
    return game_id


async def finish(db: Database, game_id: str) -> None:
    await db.finish_game(game_id, players=PLAYERS, books=BOOKS, pages=PAGES)
