"""The rows a finished game is made of.

`storage` and `game_engine` are siblings in the dependency order and may not
import each other, so a finished game cannot arrive here as `Game`, `Book` and
`Page`. It arrives as these, and `rooms` does the translation.

That is a feature rather than a tax. The engine's models carry things a
finished game must *not* keep -- player tokens, the undealt word pool, the
reveal pointer -- and listing the columns explicitly is what stops one of them
drifting into the database by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

__all__ = ["BookRow", "FinishedGame", "PageRow", "PlayerRow"]


@dataclass(frozen=True, slots=True)
class PlayerRow:
    """A display name against a seat. No tokens: the game is over."""

    idx: int
    name: str


@dataclass(frozen=True, slots=True)
class BookRow:
    """A book and the word it started from, now that it can be shown."""

    idx: int
    owner_idx: int
    word: str


@dataclass(frozen=True, slots=True)
class PageRow:
    """One page: a guess or a drawing, never both.

    `round` is both the round it was made in and its position in the book,
    which are the same number because every book gains exactly one page per
    round.
    """

    book_idx: int
    round: int
    author_idx: int
    kind: str
    text: str | None = None
    strokes: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class FinishedGame:
    """A whole finished game, read back.

    Nothing in v0 serves this: there is no archive page and no permalink
    (BUILD_PLAN.md, section 1). It exists so the tests can prove the write
    kept everything, and because the v1 features the rows are being stored for
    will need exactly this.
    """

    id: str
    code: str
    host_idx: int
    player_count: int
    finished_at: datetime
    players: list[PlayerRow]
    books: list[BookRow]
    pages: list[PageRow]
