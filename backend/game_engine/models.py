"""The data a game is made of.

Plain mutable dataclasses. Nothing here knows about sockets, databases or
clocks; the transitions in `game.py` move these structures from one valid state
to the next.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from game_engine.words import WordBank

__all__ = [
    "MAX_NAME_LENGTH",
    "MAX_PLAYERS",
    "MAX_TEXT_LENGTH",
    "MIN_PLAYERS",
    "Book",
    "Game",
    "Page",
    "PageKind",
    "Phase",
    "Player",
    "Reveal",
]

# The rules live here so that `api` can import them rather than restate them;
# a limit written down twice is a limit that will disagree with itself.
MIN_PLAYERS = 3
MAX_PLAYERS = 10
MAX_NAME_LENGTH = 20
MAX_TEXT_LENGTH = 100


class Phase(StrEnum):
    """LOBBY -> ROUND(r) -> REVEAL -> DONE."""

    LOBBY = "lobby"
    ROUND = "round"
    REVEAL = "reveal"
    DONE = "done"


class PageKind(StrEnum):
    TEXT = "text"
    STROKES = "strokes"


@dataclass
class Player:
    """A seat at the table.

    `idx` is the seat number and the player's identity everywhere after the
    game starts; before that it shifts as players join, leave or are shuffled.
    """

    idx: int
    name: str
    token: str
    connected: bool = True
    is_host: bool = False


@dataclass
class Page:
    """One side of one page: either a guess or a drawing, never both."""

    kind: PageKind
    author_idx: int
    text: str | None = None
    strokes: dict | None = None
    skipped: bool = False


@dataclass
class Book:
    """One player's book: the word they chose, then a page per round.

    `pages` is indexed by round, because every book gains exactly one page per
    round. `word` stays hidden until the reveal.
    """

    owner_idx: int
    word: str | None = None
    pages: list[Page] = field(default_factory=list)


@dataclass
class Reveal:
    """The shared pointer every player's screen follows.

    Step 0 of a book is its word card; steps 1..N are its pages. Only the host
    moves it, and the server broadcasts the result, so no client can drift.
    """

    book: int = 0
    step: int = 0


@dataclass
class Game:
    """A whole game. One room hosts exactly one of these."""

    id: str
    code: str
    phase: Phase = Phase.LOBBY
    players: list[Player] = field(default_factory=list)
    books: list[Book] = field(default_factory=list)
    round: int = 0
    reveal: Reveal | None = None
    bank: WordBank | None = None

    # -- derived ----------------------------------------------------------

    @property
    def player_count(self) -> int:
        return len(self.players)

    @property
    def host_idx(self) -> int:
        """Seat of the host.

        Derived rather than stored: shuffling seats and removing players would
        otherwise both need to remember to move a stored index, and forgetting
        once hands the game to the wrong person.
        """
        for player in self.players:
            if player.is_host:
                return player.idx
        raise LookupError("game has no host")

    @property
    def round_count(self) -> int:
        """N players means N books and N rounds."""
        return len(self.books) or len(self.players)

    def player_by_token(self, token: str) -> Player | None:
        return next((p for p in self.players if p.token == token), None)
