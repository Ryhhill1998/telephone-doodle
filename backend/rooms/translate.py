"""Translate a finished `Game` into the plain rows `storage` writes.

`storage` and `game_engine` are siblings that may not import each other
(BUILD_PLAN.md, section 2), so `rooms` sits between them and does this by
hand. Listing the columns explicitly is what stops a field that must not
survive a finished game -- a token, the undealt word pool, the reveal
pointer -- from drifting into the database by accident.
"""

from __future__ import annotations

from game_engine import Game
from storage import BookRow, PageRow, PlayerRow

__all__ = ["finished_game_rows"]


def finished_game_rows(game: Game) -> tuple[list[PlayerRow], list[BookRow], list[PageRow]]:
    players = [PlayerRow(idx=player.idx, name=player.name) for player in game.players]

    books = []
    pages = []
    for book_idx, book in enumerate(game.books):
        # Every book has a word by the time the game reaches the reveal: round
        # 0 cannot be submitted without picking one first (game_engine.submit).
        assert book.word is not None, f"book {book_idx} was never given a word"
        books.append(BookRow(idx=book_idx, owner_idx=book.owner_idx, word=book.word))
        for round_, page in enumerate(book.pages):
            pages.append(
                PageRow(
                    book_idx=book_idx,
                    round=round_,
                    author_idx=page.author_idx,
                    kind=str(page.kind),
                    text=page.text,
                    strokes=page.strokes,
                )
            )

    return players, books, pages
