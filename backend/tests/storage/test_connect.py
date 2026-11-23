"""Opening the pool: the paths that only a misbehaving database takes.

A Neon compute that has auto-suspended takes about a second to wake, so the
first connection after a quiet spell fails and then works. Getting that wrong
is invisible locally and fails every cold start in production, which is
exactly the kind of code that needs a test rather than a comment.
"""

import secrets
from typing import Any

import pytest
from psycopg.errors import UniqueViolation
from psycopg_pool import PoolTimeout

from storage import Database, RoomCodeTaken
from storage import database as database_module


class StubPool:
    """Stands in for the real pool so the retry can be driven, not waited on."""

    def __init__(self, failures: int) -> None:
        self._failures = failures
        self.waits = 0

    async def open(self) -> None:
        pass

    async def wait(self, timeout: float) -> None:
        self.waits += 1
        if self.waits <= self._failures:
            raise PoolTimeout("still waking up")


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """The delay between attempts is real seconds; the tests need none of them."""
    monkeypatch.setattr(database_module, "RETRY_DELAY_SECONDS", 0)


def with_pool(failures: int) -> tuple[Database, StubPool]:
    database = Database("postgresql:///unused")
    pool = StubPool(failures)
    database._pool = pool  # type: ignore[assignment]  # the narrowest seam there is
    return database, pool


async def test_connect_waits_out_a_database_that_is_waking_up() -> None:
    database, pool = with_pool(failures=database_module.CONNECT_ATTEMPTS - 1)

    await database.connect()

    assert pool.waits == database_module.CONNECT_ATTEMPTS


async def test_connect_stops_at_the_first_success() -> None:
    database, pool = with_pool(failures=0)

    await database.connect()

    assert pool.waits == 1


async def test_connect_gives_up_on_a_database_that_is_simply_not_there() -> None:
    """A wrong DATABASE_URL has to fail the deploy, not retry forever."""
    database, pool = with_pool(failures=database_module.CONNECT_ATTEMPTS)

    with pytest.raises(PoolTimeout):
        await database.connect()

    assert pool.waits == database_module.CONNECT_ATTEMPTS


async def test_an_id_collision_is_not_mistaken_for_a_taken_room_code(
    db: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two unique constraints on one table, and only one of them is recoverable.

    A duplicate room code means "pick another code". A duplicate game id means
    something is wrong with the id generator, and swallowing it as RoomCodeTaken
    would send the caller round a loop of new codes that could never succeed.
    """

    def always_the_same(_: Any) -> str:
        return "collision"

    monkeypatch.setattr(secrets, "token_urlsafe", always_the_same)
    await db.create_game("KQFM")

    with pytest.raises(UniqueViolation) as caught:
        await db.create_game("ZTPR")

    assert not isinstance(caught.value, RoomCodeTaken)
