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
from typing import Self

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from storage.schema import SCHEMA_SQL

__all__ = ["Database"]

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
