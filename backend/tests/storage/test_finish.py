"""Finishing a game: the one transaction that writes what is kept forever."""

import psycopg
import pytest

from storage import Database, GameStatus, PageRow
from tests.storage.conftest import BOOKS, PAGES, PLAYERS, STROKES, finish, played


async def test_a_game_survives_the_round_trip(db: Database) -> None:
    """Names, words and pages all come back, in seat and page order."""
    game_id = await played(db)

    await finish(db, game_id)

    finished = await db.get_finished_game(game_id)
    assert finished is not None
    assert finished.code == "KQFM"
    assert finished.player_count == 3
    assert finished.players == PLAYERS
    assert finished.books == BOOKS
    assert finished.pages == PAGES


async def test_drawings_come_back_as_the_json_they_went_in_as(db: Database) -> None:
    """Strokes are the one thing here with structure worth losing."""
    game_id = await played(db)
    await finish(db, game_id)

    finished = await db.get_finished_game(game_id)

    assert finished is not None
    assert finished.pages[0].strokes == STROKES
    assert finished.pages[0].text is None


async def test_finishing_marks_the_row_and_drops_the_snapshot(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    """Clearing the snapshot is what removes the player tokens."""
    game_id = await played(db)

    await finish(db, game_id)

    cursor = await conn.execute(
        "SELECT status, snapshot, finished_at, version FROM games WHERE id = %s", (game_id,)
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["status"] == GameStatus.FINISHED
    assert row["snapshot"] is None
    assert row["finished_at"] is not None


async def test_a_finished_game_stops_being_loadable(db: Database) -> None:
    """`load_game` serves rooms that can still be played, and this one cannot."""
    game_id = await played(db)

    await finish(db, game_id)

    assert await db.load_game("KQFM") is None


async def test_a_snapshot_write_still_in_flight_is_refused_after_finishing(db: Database) -> None:
    """Finishing bumps the version, so a late writer cannot resurrect the game."""
    game_id = await played(db)
    await finish(db, game_id)

    refused = await db.save_snapshot(
        game_id,
        status=GameStatus.IN_PROGRESS,
        host_idx=0,
        player_count=3,
        snapshot={"phase": "round"},
        expected_version=1,
    )

    assert refused is None


async def test_a_finished_code_can_be_used_again(db: Database) -> None:
    """The partial unique index exists for this: four letters is a small space."""
    first = await played(db, "KQFM")
    await finish(db, first)

    second = await db.create_game("KQFM")

    assert second != first
    loaded = await db.load_game("KQFM")
    assert loaded is not None
    assert loaded.id == second


async def test_nothing_is_written_when_part_of_the_game_cannot_be(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    """All or nothing. A game marked finished whose pages failed has lost them.

    The extra page repeats a (book, round) that is already in the list, so the
    pages primary key rejects it *after* players and books have been inserted
    -- precisely where a partial write would otherwise be possible.
    """
    game_id = await played(db)
    duplicate = PageRow(book_idx=0, round=0, author_idx=0, kind="text", text="again")

    with pytest.raises(psycopg.errors.UniqueViolation):
        await db.finish_game(game_id, players=PLAYERS, books=BOOKS, pages=[*PAGES, duplicate])

    cursor = await conn.execute("SELECT count(*) AS n FROM players WHERE game_id = %s", (game_id,))
    counted = await cursor.fetchone()
    assert counted is not None and counted["n"] == 0, "players were left behind by a failed finish"
    loaded = await db.load_game("KQFM")
    assert loaded is not None, "the game should still be playable after a failed finish"


async def test_get_finished_game_returns_none_while_the_game_is_being_played(
    db: Database,
) -> None:
    game_id = await played(db)

    assert await db.get_finished_game(game_id) is None


async def test_get_finished_game_returns_none_for_a_game_that_is_not_there(db: Database) -> None:
    assert await db.get_finished_game("nosuchid") is None
