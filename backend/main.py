"""Telephone Doodle API.

The FastAPI application. HTTP routes and the WebSocket handler move into `api/`
from Step 4 onward; for now this module exposes the health check and owns the
database for the lifetime of the process.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from storage import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the database on startup, close it on shutdown.

    The schema is created here because this is the only moment the plan gives
    it: there is no migration step and no deploy hook, just an idempotent
    `CREATE TABLE IF NOT EXISTS` on every boot (BUILD_PLAN.md, Step 3).

    Connecting before the app serves anything means a wrong `DATABASE_URL`
    fails the deploy rather than the first game. The pool is parked on
    `app.state` so Step 4's `RoomManager` can be handed it instead of reaching
    for a global.
    """
    database = Database.from_env()
    await database.connect()
    await database.create_schema()
    app.state.db = database

    try:
        yield
    finally:
        await database.close()


app = FastAPI(title="Telephone Doodle API", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness and startup probe.

    Deliberately does not touch the database. Neon's free-plan compute suspends
    after five minutes idle, and a probe that woke it would make a sleeping
    database able to fail a deploy (BUILD_PLAN.md, section 3).
    """
    return {"status": "ok"}
