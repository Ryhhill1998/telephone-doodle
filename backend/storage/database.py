"""The connection pool, and the statements the application runs through it.

Plain SQL over `psycopg` 3's async pool. No ORM: the whole schema is four
tables and the queries are short enough to read (BUILD_PLAN.md, Step 3).

`Database` is an object rather than a module of functions over a global pool.
Call sites read the same either way (`storage.create_game(...)`), but an
instance can be handed to `RoomManager` in Step 4 and thrown away per test,
which a module-level pool cannot.
"""

from __future__ import annotations

import asyncio
import os
import secrets
from typing import Any, NamedTuple, Self

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from storage.schema import ACTIVE_CODE_INDEX, SCHEMA_SQL, GameStatus

__all__ = ["ActiveGame", "Database", "RoomCodeTaken"]

#: Neon's free-plan compute suspends after five minutes idle and takes about a
#: second to wake, so the first connection after a quiet spell is slow but not
#: broken. A generous timeout and a couple of retries ride that out instead of
#: failing a deploy (BUILD_PLAN.md, section 3, "Connection notes for Neon").
CONNECT_TIMEOUT_SECONDS = 10.0
CONNECT_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1.0

#: The API runs as a single Cloud Run instance (`max-instances=1`) and writes a
#: snapshot per event, not per stroke, so a handful of connections is plenty.
#: Idle connections cost Neon compute-hours, hence the small floor.
MIN_POOL_SIZE = 1
MAX_POOL_SIZE = 10

#: `secrets.token_urlsafe(6)` is eight characters, which is what Step 3 asks
#: for. The id is internal -- nothing in v0 links to it -- so it only has to be
#: unguessable enough that a future permalink feature is not born broken.
GAME_ID_BYTES = 6


class RoomCodeTaken(Exception):
    """A game that is still being played already holds this room code.

    The partial unique index is the only authority on this. `RoomManager` keeps
    its own set of live codes, but that set is empty after a cold start while
    the database still remembers every unfinished game, so the insert is what
    actually decides. The caller's answer is to pick another code.
    """


class ActiveGame(NamedTuple):
    """An unfinished game, as `load_game` returns it."""

    id: str
    version: int
    snapshot: dict[str, Any] | None


class Database:
    """Owns one `psycopg` pool and every query the app makes through it."""

    def __init__(self, conninfo: str) -> None:
        self._pool = AsyncConnectionPool(
            conninfo,
            kwargs={
                # Neon's *pooled* host runs PgBouncer in transaction mode, which
                # cannot see server-side prepared statements made on an earlier
                # connection. Disabling them is what makes the pooled string
                # usable at all; psycopg would otherwise fail intermittently
                # with "prepared statement does not exist".
                "prepare_threshold": None,
                "connect_timeout": CONNECT_TIMEOUT_SECONDS,
                # Rows come back as dicts so the queries below can name their
                # columns instead of counting tuple positions.
                "row_factory": dict_row,
            },
            min_size=MIN_POOL_SIZE,
            max_size=MAX_POOL_SIZE,
            # Opened explicitly in `connect()`: the pool must be created inside
            # the running event loop it will serve.
            open=False,
        )

    @classmethod
    def from_env(cls) -> Self:
        """Build a database from `DATABASE_URL` and nothing else.

        The connection string has exactly one source (BUILD_PLAN.md, Step 3's
        review checklist). There is deliberately no default: a fallback to a
        localhost URL would let production start up pointed at nothing and only
        fail once somebody tried to play.

        `sslmode` is left to the URL rather than forced here. Neon's string
        already carries `sslmode=require`, while the local Postgres from
        `docker-compose.dev.yml` serves no TLS at all, so a hard-coded value
        would be wrong in one environment or the other.
        """
        conninfo = os.environ.get("DATABASE_URL")
        if not conninfo:
            raise RuntimeError(
                "DATABASE_URL is not set. `make db` starts the local Postgres and the "
                "Makefile exports a URL pointing at it; in production the value comes "
                "from Secret Manager."
            )
        return cls(conninfo)

    # -- lifecycle --------------------------------------------------------

    async def connect(self) -> None:
        """Open the pool and wait until it really has a connection.

        `open()` on its own returns before any connection exists, so a database
        that is unreachable would surface as a failure on the first query
        rather than at startup. Waiting here means a broken `DATABASE_URL`
        fails the deploy, and a merely sleeping Neon is retried.
        """
        await self._pool.open()

        for attempt in range(1, CONNECT_ATTEMPTS + 1):
            try:
                await self._pool.wait(timeout=CONNECT_TIMEOUT_SECONDS)
            except PoolTimeout:
                if attempt == CONNECT_ATTEMPTS:
                    raise
                await asyncio.sleep(RETRY_DELAY_SECONDS)
            else:
                return

    async def close(self) -> None:
        await self._pool.close()

    async def create_schema(self) -> None:
        """Create the tables and indexes if they are not already there.

        Runs on every startup. Each statement is `IF NOT EXISTS`, so this is a
        no-op against an existing database.

        Two instances overlap briefly during a Cloud Run deploy, and Postgres's
        `IF NOT EXISTS` is not atomic against a concurrent `CREATE`, so the
        loser of that race can see a duplicate-object error. It is not retried:
        the new instance fails its health check, the deploy keeps serving the
        old one, and the next attempt finds the schema already there.
        """
        async with self._pool.connection() as conn:
            await conn.execute(SCHEMA_SQL)

    # -- games in progress ------------------------------------------------

    async def create_game(self, code: str) -> str:
        """Record a new game and return its id.

        Called when the room is created, not when it starts: one room hosts
        exactly one game, and "play again" makes a new room (BUILD_PLAN.md,
        section 3). The creator is the only player and holds seat 0, so
        `host_idx` and `player_count` have exactly one possible value here;
        `save_snapshot` keeps them true from then on.

        Raises `RoomCodeTaken` if an unfinished game already has the code.
        """
        game_id = secrets.token_urlsafe(GAME_ID_BYTES)

        try:
            async with self._pool.connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO games (id, code, status, host_idx, player_count)
                    VALUES (%s, %s, %s, 0, 1)
                    """,
                    (game_id, code, GameStatus.LOBBY),
                )
        except psycopg.errors.UniqueViolation as exc:
            if exc.diag.constraint_name == ACTIVE_CODE_INDEX:
                raise RoomCodeTaken(code) from exc
            raise

        return game_id

    async def load_game(self, code: str) -> ActiveGame | None:
        """The unfinished game holding this code, if there is one.

        Finished games are excluded rather than merely ordered last: their
        codes are free to be reused, so a code can match both an old finished
        game and the one being played right now. The partial unique index
        guarantees at most one of the latter.
        """
        async with self._pool.connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, version, snapshot
                  FROM games
                 WHERE code = %s AND status <> %s
                """,
                (code, GameStatus.FINISHED),
            )
            row = await cursor.fetchone()

        if row is None:
            return None
        return ActiveGame(id=row["id"], version=row["version"], snapshot=row["snapshot"])

    async def save_snapshot(
        self,
        game_id: str,
        *,
        status: GameStatus,
        host_idx: int,
        player_count: int,
        snapshot: dict[str, Any],
        expected_version: int,
    ) -> int | None:
        """Write the whole game state, guarded by its version.

        Returns the new version, or `None` if the write was refused because
        somebody else got there first.

        The guard is the whole point. Cloud Run overlaps the old and new
        instances during a deploy, so two processes can briefly hold the same
        room; without `WHERE version = ...` the slower one would quietly
        overwrite the faster one's moves. A `None` here tells the caller to
        drop its in-memory room and close its sockets with 1012, which is
        wired up in Step 5.

        `host_idx` and `player_count` are passed in rather than left at their
        creation values: players join, and the host moves when seats are
        shuffled, so the columns would otherwise describe a game nobody played.
        """
        async with self._pool.connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE games
                   SET status       = %(status)s,
                       host_idx     = %(host_idx)s,
                       player_count = %(player_count)s,
                       snapshot     = %(snapshot)s,
                       version      = version + 1,
                       updated_at   = now(),
                       -- Stamped once, on the move out of the lobby, and never
                       -- touched again.
                       started_at   = CASE
                                        WHEN started_at IS NOT NULL THEN started_at
                                        WHEN %(status)s = %(lobby)s THEN NULL
                                        ELSE now()
                                      END
                 WHERE id = %(id)s AND version = %(expected_version)s
                RETURNING version
                """,
                {
                    "id": game_id,
                    "status": status,
                    "host_idx": host_idx,
                    "player_count": player_count,
                    "snapshot": Jsonb(snapshot),
                    "expected_version": expected_version,
                    "lobby": GameStatus.LOBBY,
                },
            )
            row = await cursor.fetchone()

        return None if row is None else row["version"]
