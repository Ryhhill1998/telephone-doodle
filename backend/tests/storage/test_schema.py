"""The schema is created on startup, on every startup."""

import psycopg
import pytest

from storage import TABLES, Database


async def table_names(conn: psycopg.AsyncConnection) -> set[str]:
    cursor = await conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    return {row["table_name"] for row in await cursor.fetchall()}


async def test_create_schema_creates_every_table(conn: psycopg.AsyncConnection) -> None:
    assert set(TABLES) <= await table_names(conn)


async def test_create_schema_is_idempotent(db: Database, conn: psycopg.AsyncConnection) -> None:
    """Startup runs it unconditionally, so the second run must be a no-op.

    The fixture has already created the schema once; this is the third time.
    """
    await db.create_schema()
    await db.create_schema()

    assert set(TABLES) <= await table_names(conn)


async def test_the_active_code_index_is_partial(conn: psycopg.AsyncConnection) -> None:
    """A plain unique index would burn a room code permanently.

    Four letters minus the ambiguous ones is a small space, so codes have to
    come back round once a game is over. Asserting on the definition catches
    the `WHERE` clause being dropped, which no insert of a fresh code would.
    """
    cursor = await conn.execute(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'games_active_code_idx'"
    )
    row = await cursor.fetchone()

    assert row is not None, "the partial unique index on games.code is missing"
    assert "UNIQUE" in row["indexdef"]
    assert "WHERE (status <> 'finished'::text)" in row["indexdef"]


async def test_from_env_refuses_to_guess_a_connection_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No localhost default: production must fail loudly, not quietly wrongly."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        Database.from_env()
