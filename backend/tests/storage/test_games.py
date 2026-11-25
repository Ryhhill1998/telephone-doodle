"""Creating a game, loading it back, and the version-guarded snapshot write."""

from datetime import timedelta
from typing import Any

import psycopg
import pytest

from storage import ActiveGame, Database, GameStatus, RoomCodeTaken

# Storage knows nothing about the engine's state, so the tests use a snapshot
# that is simply "some JSON". Whether `game_engine.to_dict` round-trips is the
# engine's own business, tested in tests/game_engine/test_snapshots.py.
SNAPSHOT: dict[str, Any] = {"phase": "round", "round": 1, "players": [{"idx": 0}]}


async def game_row(conn: psycopg.AsyncConnection, game_id: str) -> dict[str, Any]:
    cursor = await conn.execute("SELECT * FROM games WHERE id = %s", (game_id,))
    row = await cursor.fetchone()
    assert row is not None, f"no games row for {game_id}"
    return row


async def save(db: Database, game_id: str, **overrides: Any) -> int | None:
    """`save_snapshot` with the arguments a caller usually has."""
    return await db.save_snapshot(
        game_id,
        **{
            "status": GameStatus.IN_PROGRESS,
            "host_idx": 0,
            "player_count": 3,
            "snapshot": SNAPSHOT,
            "expected_version": 0,
            **overrides,
        },
    )


# -- create_game ----------------------------------------------------------


async def test_create_game_records_a_lobby_row(db: Database, conn: psycopg.AsyncConnection) -> None:
    game_id = await db.create_game("KQFM")

    assert len(game_id) == 8
    row = await game_row(conn, game_id)
    assert row["code"] == "KQFM"
    assert row["status"] == GameStatus.LOBBY
    assert row["version"] == 0
    assert row["player_count"] == 1
    assert row["snapshot"] is None
    assert row["started_at"] is None
    assert row["finished_at"] is None


async def test_create_game_gives_every_game_its_own_id(db: Database) -> None:
    ids = {await db.create_game(code) for code in ("KQFM", "ZTPR", "BWNX")}

    assert len(ids) == 3


async def test_create_game_refuses_a_code_an_unfinished_game_holds(db: Database) -> None:
    """The index is the authority, not `RoomManager`'s in-memory set of codes.

    After a cold start that set is empty while the database still remembers
    every unfinished game, so this is the check that actually runs.
    """
    await db.create_game("KQFM")

    with pytest.raises(RoomCodeTaken):
        await db.create_game("KQFM")


# -- load_game ------------------------------------------------------------


async def test_load_game_returns_the_unfinished_game_for_a_code(db: Database) -> None:
    game_id = await db.create_game("KQFM")

    assert await db.load_game("KQFM") == ActiveGame(id=game_id, version=0, snapshot=None)


async def test_load_game_returns_none_for_a_code_nobody_is_using(db: Database) -> None:
    await db.create_game("KQFM")

    assert await db.load_game("ZTPR") is None


async def test_load_game_returns_the_latest_snapshot(db: Database) -> None:
    game_id = await db.create_game("KQFM")
    await save(db, game_id)

    loaded = await db.load_game("KQFM")

    assert loaded == ActiveGame(id=game_id, version=1, snapshot=SNAPSHOT)


async def test_load_game_does_not_resurrect_a_stale_row(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    """A code nobody has touched in `max_age` is gone to `get_or_load`, not just
    to the cleanup sweep that eventually deletes its row.
    """
    game_id = await db.create_game("KQFM")
    await conn.execute(
        "UPDATE games SET updated_at = now() - %s WHERE id = %s",
        (timedelta(hours=25), game_id),
    )

    assert await db.load_game("KQFM", max_age=timedelta(hours=24)) is None


# -- save_snapshot --------------------------------------------------------


async def test_save_snapshot_returns_the_new_version(db: Database) -> None:
    game_id = await db.create_game("KQFM")

    assert await save(db, game_id, expected_version=0) == 1
    assert await save(db, game_id, expected_version=1) == 2


async def test_save_snapshot_overwrites_the_previous_one(db: Database) -> None:
    """Snapshots replace, they do not accumulate: one row holds the game."""
    game_id = await db.create_game("KQFM")
    await save(db, game_id, expected_version=0, snapshot={"phase": "lobby"})

    await save(db, game_id, expected_version=1, snapshot={"phase": "reveal"})

    loaded = await db.load_game("KQFM")
    assert loaded is not None
    assert loaded.snapshot == {"phase": "reveal"}


async def test_save_snapshot_keeps_the_head_count_and_the_host_current(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    """Both change after creation: players join, and shuffling moves the host."""
    game_id = await db.create_game("KQFM")

    await save(db, game_id, host_idx=4, player_count=7)

    row = await game_row(conn, game_id)
    assert (row["host_idx"], row["player_count"]) == (4, 7)


async def test_save_snapshot_rejects_a_stale_version(db: Database) -> None:
    """The deploy-overlap guard: the slow writer must lose, not overwrite.

    Two instances briefly share a room while Cloud Run swaps revisions. The
    one holding the older version gets `None` and, from Step 5, drops its copy
    of the room and closes its sockets with 1012.
    """
    game_id = await db.create_game("KQFM")
    await save(db, game_id, expected_version=0, snapshot={"phase": "lobby"})

    refused = await save(db, game_id, expected_version=0, snapshot={"phase": "clobbered"})

    assert refused is None
    loaded = await db.load_game("KQFM")
    assert loaded is not None
    assert loaded.version == 1
    assert loaded.snapshot == {"phase": "lobby"}


async def test_save_snapshot_returns_none_for_a_game_that_is_not_there(db: Database) -> None:
    assert await save(db, "nosuchid") is None


# -- started_at -----------------------------------------------------------


async def test_a_game_in_the_lobby_has_not_started(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    game_id = await db.create_game("KQFM")

    await save(db, game_id, status=GameStatus.LOBBY)

    assert (await game_row(conn, game_id))["started_at"] is None


async def test_started_at_is_stamped_once_and_never_moved(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    game_id = await db.create_game("KQFM")
    await save(db, game_id, status=GameStatus.LOBBY, expected_version=0)

    await save(db, game_id, status=GameStatus.IN_PROGRESS, expected_version=1)
    started = (await game_row(conn, game_id))["started_at"]

    await save(db, game_id, status=GameStatus.IN_PROGRESS, expected_version=2)

    assert started is not None
    assert (await game_row(conn, game_id))["started_at"] == started
