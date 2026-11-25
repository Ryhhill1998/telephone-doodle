"""Who works on which book, in which round, and what they produce.

The seats form a circle and every book moves on one seat per round, so with N
players there are N books and N rounds and every player touches every book
exactly once.

These are the only two places the direction of travel is decided, so the
passing stays predictable from the lobby list.
"""

from __future__ import annotations

from game_engine.models import PageKind

__all__ = ["book_index", "page_kind", "seat_holding"]


def book_index(seat: int, round_: int, player_count: int) -> int:
    """The book a seat works on in a given round.

    Round 0 is your own book; round 1 is the book of the seat before you, and
    so on round the circle.
    """
    return (seat - round_) % player_count


def seat_holding(book: int, round_: int, player_count: int) -> int:
    """The inverse: who holds a given book in a given round.

    Exactly one seat holds each book each round, which is what makes "every
    book moves on one seat" true rather than merely intended.
    """
    return (book + round_) % player_count


def page_kind(round_: int) -> PageKind:
    """What a player produces in a round.

    Round 0 is a drawing (of the word they picked), odd rounds are a guess at
    the drawing before them, and later even rounds are a drawing of the guess
    before them. With an odd number of players the last round is even, so every
    book ends on a drawing nobody guesses — which section 1 accepts for v0.
    """
    return PageKind.STROKES if round_ % 2 == 0 else PageKind.TEXT
