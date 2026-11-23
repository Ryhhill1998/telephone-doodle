"""Deleting games nobody is coming back to."""

from datetime import timedelta

import psycopg

from storage import Database, GameStatus
from tests.storage.conftest import finish

A_DAY = timedelta(hours=24)


async def age(conn: psycopg.AsyncConnection, game_id: str, by: timedelta) -> None:
    """Backdate a game so a cutoff can be tested without waiting for one."""
    await conn.execute("UPDATE games SET updated_at = now() - %s WHERE id = %s", (by, game_id))


async def test_a_game_abandoned_in_the_lobby_is_deleted(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    game_id = await db.create_game("KQFM")
    await age(conn, game_id, timedelta(hours=25))

    assert await db.delete_stale_games(A_DAY) == 1
    assert await db.load_game("KQFM") is None


async def test_a_game_still_being_played_is_left_alone(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    """Rounds have no timer, so a slow game is not an abandoned one."""
    game_id = await db.create_game("KQFM")
    await db.save_snapshot(
        game_id,
        status=GameStatus.IN_PROGRESS,
        host_idx=0,
        player_count=3,
        snapshot={"phase": "round"},
        expected_version=0,
    )
    await age(conn, game_id, timedelta(hours=23))

    assert await db.delete_stale_games(A_DAY) == 0
    assert await db.load_game("KQFM") is not None


async def test_finished_games_are_kept_however_old(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    """They are the reason the rows exist: v1 reads them, v0 just keeps them."""
    game_id = await db.create_game("KQFM")
    await finish(db, game_id)
    await age(conn, game_id, timedelta(days=400))

    assert await db.delete_stale_games(A_DAY) == 0
    assert await db.get_finished_game(game_id) is not None


async def test_only_the_stale_games_go(db: Database, conn: psycopg.AsyncConnection) -> None:
    stale = await db.create_game("KQFM")
    fresh = await db.create_game("ZTPR")
    await age(conn, stale, timedelta(hours=30))

    assert await db.delete_stale_games(A_DAY) == 1

    survivor = await db.load_game("ZTPR")
    assert survivor is not None and survivor.id == fresh
    assert await db.load_game("KQFM") is None
