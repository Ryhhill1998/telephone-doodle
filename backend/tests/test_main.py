"""Tests for the application entry point."""

import os

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql

from main import app
from storage import TABLES, Database

# Built outside a `with` block on purpose: no lifespan runs, so this client has
# no database behind it at all. Every test using it therefore proves its route
# works without one.
client = TestClient(app)


def table_names() -> set[str]:
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchall()
    return {name for (name,) in rows}


def drop_schema() -> None:
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conn.execute(
            sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.SQL(", ").join(map(sql.Identifier, TABLES))
            )
        )


def test_healthz_returns_ok() -> None:
    """And does it without a database, which is the point of the probe.

    Neon suspends a free-plan compute after five minutes idle. A health check
    that woke it would let a sleeping database fail a deploy, so this route
    must keep working when nothing has connected to Postgres -- which is
    exactly the situation this module-level client is in.
    """
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_creates_the_schema() -> None:
    """There is no migration step: booting the app is what makes the tables.

    Dropping them first means this cannot pass on the strength of an earlier
    test having created them.
    """
    drop_schema()
    assert not set(TABLES) & table_names()

    with TestClient(app):
        pass

    assert set(TABLES) <= table_names()


def test_startup_leaves_the_database_where_step_4_can_find_it() -> None:
    with TestClient(app):
        assert isinstance(app.state.db, Database)
