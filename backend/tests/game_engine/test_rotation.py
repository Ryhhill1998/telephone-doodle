"""Rotation is the heart of the game, so it is tested exhaustively for N = 3..10.

If these pass, books cannot be lost, duplicated or handed to the same player
twice, whatever the player count.
"""

from itertools import pairwise

import pytest

from game_engine.models import PageKind
from game_engine.rotation import book_index, page_kind, seat_holding

PLAYER_COUNTS = range(3, 11)


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_round_zero_is_your_own_book(player_count: int) -> None:
    for seat in range(player_count):
        assert book_index(seat, 0, player_count) == seat


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_every_book_is_held_by_exactly_one_seat_each_round(player_count: int) -> None:
    for round_ in range(player_count):
        held = [book_index(seat, round_, player_count) for seat in range(player_count)]

        assert sorted(held) == list(range(player_count)), (
            f"round {round_} with {player_count} players is not a permutation"
        )


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_every_player_touches_every_book_exactly_once(player_count: int) -> None:
    for seat in range(player_count):
        books = [book_index(seat, round_, player_count) for round_ in range(player_count)]

        assert sorted(books) == list(range(player_count))


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_each_book_moves_on_exactly_one_seat_per_round(player_count: int) -> None:
    """The same direction every round, so the passing is predictable."""
    for book in range(player_count):
        for round_ in range(player_count - 1):
            here = seat_holding(book, round_, player_count)
            there = seat_holding(book, round_ + 1, player_count)

            assert there == (here + 1) % player_count


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_seat_holding_inverts_book_index(player_count: int) -> None:
    for round_ in range(player_count):
        for seat in range(player_count):
            book = book_index(seat, round_, player_count)

            assert seat_holding(book, round_, player_count) == seat


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_seat_zero_follows_the_last_seat(player_count: int) -> None:
    """The circle closes: book 0 reaches seat 0 again only after a full lap."""
    assert seat_holding(0, player_count - 1, player_count) == player_count - 1
    assert seat_holding(0, player_count, player_count) == 0


# -- page kinds ----------------------------------------------------------


def test_round_zero_is_a_drawing() -> None:
    assert page_kind(0) is PageKind.STROKES


@pytest.mark.parametrize("round_", range(0, 10))
def test_kinds_alternate(round_: int) -> None:
    expected = PageKind.STROKES if round_ % 2 == 0 else PageKind.TEXT

    assert page_kind(round_) is expected


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_a_book_alternates_drawing_and_guess(player_count: int) -> None:
    kinds = [page_kind(round_) for round_ in range(player_count)]

    assert kinds[0] is PageKind.STROKES
    for earlier, later in pairwise(kinds):
        assert earlier is not later, "two pages of the same kind in a row"


@pytest.mark.parametrize("player_count", [3, 5, 7, 9])
def test_odd_player_counts_end_on_an_unguessed_drawing(player_count: int) -> None:
    assert page_kind(player_count - 1) is PageKind.STROKES


@pytest.mark.parametrize("player_count", [4, 6, 8, 10])
def test_even_player_counts_end_on_a_guess(player_count: int) -> None:
    assert page_kind(player_count - 1) is PageKind.TEXT
