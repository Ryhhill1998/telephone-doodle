"""Fixtures specific to the storage tests.

The `db` and `conn` fixtures these build on are shared across the whole
backend suite and live in `tests/conftest.py`.
"""

from typing import Any

from storage import BookRow, Database, GameStatus, PageRow, PlayerRow

# -- a game worth storing ------------------------------------------------
#
# Three players, three books, three rounds. Shared by the tests that write a
# finished game and the ones that check it survives the housekeeping.

STROKES: dict[str, Any] = {
    "v": 1,
    "w": 800,
    "h": 600,
    "ops": [{"t": "brush", "c": "#C8381F", "s": 12, "p": [[0.1, 0.2], [0.3, 0.4]]}],
}

PLAYERS = [PlayerRow(idx=0, name="Jo"), PlayerRow(idx=1, name="Sam"), PlayerRow(idx=2, name="Ali")]

BOOKS = [
    BookRow(idx=0, owner_idx=0, word="penguin"),
    BookRow(idx=1, owner_idx=1, word="volcano"),
    BookRow(idx=2, owner_idx=2, word="toaster"),
]

# Three books, three rounds, in the order the reveal walks them: book by book,
# page by page. Round 0 is a drawing, round 1 a guess, round 2 a drawing again.
# The seat holding book `b` in round `r` is `(b + r) % n`, the inverse of the
# engine's `book_index`.
PAGES = [
    PageRow(
        book_idx=book,
        round=rnd,
        author_idx=(book + rnd) % 3,
        kind="text" if rnd % 2 else "strokes",
        text=f"guess {book}" if rnd % 2 else None,
        strokes=None if rnd % 2 else STROKES,
    )
    for book in range(3)
    for rnd in range(3)
]


async def played(db: Database, code: str = "KQFM") -> str:
    """A game taken from creation to the point of finishing."""
    game_id = await db.create_game(code)
    await db.save_snapshot(
        game_id,
        status=GameStatus.IN_PROGRESS,
        host_idx=0,
        player_count=3,
        snapshot={"phase": "reveal", "players": [{"token": "secret"}]},
        expected_version=0,
    )
    return game_id


async def finish(db: Database, game_id: str) -> None:
    await db.finish_game(game_id, players=PLAYERS, books=BOOKS, pages=PAGES)
