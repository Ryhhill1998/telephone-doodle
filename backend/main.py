"""Telephone Doodle API.

The FastAPI application: the health check, the database and `RoomManager` for
the lifetime of the process, and the `api` router (HTTP routes and the
WebSocket handler, Step 4).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import router
from rooms import RoomManager
from settings import get_settings
from storage import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the database and start the room manager on startup; reverse on shutdown.

    The schema is created here because this is the only moment the plan gives
    it: there is no migration step and no deploy hook, just an idempotent
    `CREATE TABLE IF NOT EXISTS` on every boot.

    Connecting before the app serves anything means a wrong `DATABASE_URL`
    fails the deploy rather than the first game. It's parked on `app.state`
    so `api`'s routes can reach it instead of a global.

    On SIGTERM, uvicorn runs this `finally` block as the ASGI shutdown event:
    every snapshot write already happened synchronously as part of the event
    that caused it, so closing every open socket with 1012 is all that is
    left to do before this instance goes away.
    """
    database = Database.from_env()
    await database.connect()
    await database.create_schema()
    app.state.db = database

    rooms = RoomManager(database)
    await rooms.start()
    app.state.rooms = rooms

    try:
        yield
    finally:
        await rooms.stop()
        await rooms.close_all_rooms()
        await database.close()


app = FastAPI(title="Telephone Doodle API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness and startup probe.

    Deliberately does not touch the database. Neon's free-plan compute suspends
    after five minutes idle, and a probe that woke it would make a sleeping
    database able to fail a deploy.
    """
    return {"status": "ok"}
