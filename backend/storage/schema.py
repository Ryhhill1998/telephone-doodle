"""The database schema, created idempotently on startup.

There is no ORM and no migration tool (BUILD_PLAN.md, section 2 and Step 3's
review checklist). v0 has four tables and one index; a migration framework
would be more machinery than the thing it manages. When a column does need to
change, the statements here are edited and an `ALTER TABLE ... IF EXISTS` is
added alongside.

Every statement is `IF NOT EXISTS`, so running this against an existing
database is a no-op. It runs on every startup.
"""

__all__ = ["SCHEMA_SQL", "TABLES"]

# Written in dependency order: the three child tables reference `games`.
TABLES = ("games", "players", "books", "pages")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS games (
    id           TEXT PRIMARY KEY,
    code         TEXT        NOT NULL,
    status       TEXT        NOT NULL CHECK (status IN ('lobby', 'in_progress', 'finished')),
    host_idx     INT         NOT NULL,
    player_count INT         NOT NULL,
    version      INT         NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    snapshot     JSONB
);

-- Room codes are four letters, so they have to be reusable. Making the
-- uniqueness partial means only one *unfinished* game can hold a code at a
-- time, while every finished game keeps the code it was played under.
CREATE UNIQUE INDEX IF NOT EXISTS games_active_code_idx
    ON games (code)
    WHERE status <> 'finished';

-- `players`, `books` and `pages` are written once, when the game finishes, so
-- that a finished game records who drew or wrote what (BUILD_PLAN.md, §3).
-- While a game is in progress all of that lives in `games.snapshot` instead.
CREATE TABLE IF NOT EXISTS players (
    game_id TEXT NOT NULL REFERENCES games (id) ON DELETE CASCADE,
    idx     INT  NOT NULL,
    name    TEXT NOT NULL,
    PRIMARY KEY (game_id, idx)
);

CREATE TABLE IF NOT EXISTS books (
    game_id   TEXT NOT NULL REFERENCES games (id) ON DELETE CASCADE,
    idx       INT  NOT NULL,
    owner_idx INT  NOT NULL,
    word      TEXT NOT NULL,
    PRIMARY KEY (game_id, idx)
);

CREATE TABLE IF NOT EXISTS pages (
    game_id    TEXT  NOT NULL REFERENCES games (id) ON DELETE CASCADE,
    book_idx   INT   NOT NULL,
    round      INT   NOT NULL,
    author_idx INT   NOT NULL,
    kind       TEXT  NOT NULL CHECK (kind IN ('text', 'strokes')),
    text       TEXT,
    strokes    JSONB,
    PRIMARY KEY (game_id, book_idx, round)
);
"""
