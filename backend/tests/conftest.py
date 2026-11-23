"""Fixtures shared across the backend test suite.

These run against a real Postgres -- the container from
`docker-compose.dev.yml` locally (`make db`), the service container in CI --
because the things worth testing here are the things only Postgres decides: a
partial unique index, a version-guarded `UPDATE`, a transaction that has to be
all or nothing. A fake would only test the fake.
"""

import os
from collections.abc import AsyncIterator

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row

from storage import TABLES, Database


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
