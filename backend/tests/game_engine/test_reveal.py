"""The shared reveal pointer, which is what keeps every screen on the same page."""

import pytest

from game_engine.errors import NotAllowed, WrongPhase
from game_engine.game import (
    finish_reveal,
    is_last_step,
    reveal_next,
    reveal_prev,
    reveal_step_count,
)
from game_engine.models import Phase
from tests.game_engine.conftest import play_to_reveal, started

PLAYER_COUNTS = range(3, 11)


def host(game) -> int:
    return game.host_idx


def walk_forward(game) -> list[tuple[int, int]]:
    """Every pointer position from the start to the end, in order."""
    assert game.reveal is not None
    seen = [(game.reveal.book, game.reveal.step)]
    while not is_last_step(game):
        reveal_next(game, host(game))
        seen.append((game.reveal.book, game.reveal.step))
    return seen


def test_the_reveal_starts_on_the_first_word_card() -> None:
    game = play_to_reveal(3)

    assert game.phase is Phase.REVEAL
    assert game.reveal is not None
    assert (game.reveal.book, game.reveal.step) == (0, 0)


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_a_book_has_a_word_card_then_one_step_per_page(player_count: int) -> None:
    game = play_to_reveal(player_count)

    for book in range(player_count):
        assert reveal_step_count(game, book) == player_count + 1


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_the_pointer_walks_every_step_of_every_book_in_order(player_count: int) -> None:
    game = play_to_reveal(player_count)

    walked = walk_forward(game)

    expected = [(book, step) for book in range(player_count) for step in range(player_count + 1)]
    assert walked == expected


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_walking_back_retraces_the_walk_forward(player_count: int) -> None:
    game = play_to_reveal(player_count)
    forward = walk_forward(game)

    backward = [(game.reveal.book, game.reveal.step)]
    while (game.reveal.book, game.reveal.step) != (0, 0):
        reveal_prev(game, host(game))
        backward.append((game.reveal.book, game.reveal.step))

    assert backward == list(reversed(forward))


def test_the_end_of_a_book_leads_to_the_next_word_card() -> None:
    game = play_to_reveal(4)
    for _ in range(reveal_step_count(game, 0) - 1):
        reveal_next(game, host(game))

    reveal_next(game, host(game))

    assert (game.reveal.book, game.reveal.step) == (1, 0)


def test_back_from_a_word_card_lands_on_the_previous_books_last_page() -> None:
    game = play_to_reveal(4)
    while (game.reveal.book, game.reveal.step) != (1, 0):
        reveal_next(game, host(game))

    reveal_prev(game, host(game))

    assert (game.reveal.book, game.reveal.step) == (0, reveal_step_count(game, 0) - 1)


def test_back_does_nothing_on_the_very_first_step() -> None:
    game = play_to_reveal(3)

    reveal_prev(game, host(game))

    assert (game.reveal.book, game.reveal.step) == (0, 0)


def test_next_does_nothing_on_the_very_last_step() -> None:
    """The host is shown Finish there, so a stray Next is a double-tap."""
    game = play_to_reveal(3)
    walk_forward(game)
    end = (game.reveal.book, game.reveal.step)

    reveal_next(game, host(game))

    assert (game.reveal.book, game.reveal.step) == end


# -- only the host drives ------------------------------------------------


@pytest.mark.parametrize("action", [reveal_next, reveal_prev])
def test_only_the_host_can_move_the_pointer(action) -> None:
    game = play_to_reveal(4)
    guest = next(p.idx for p in game.players if not p.is_host)

    with pytest.raises(NotAllowed):
        action(game, guest)


def test_only_the_host_can_finish() -> None:
    game = play_to_reveal(3)
    walk_forward(game)
    guest = next(p.idx for p in game.players if not p.is_host)

    with pytest.raises(NotAllowed):
        finish_reveal(game, guest)


# -- finishing -----------------------------------------------------------


def test_finishing_early_is_rejected() -> None:
    game = play_to_reveal(3)

    with pytest.raises(NotAllowed):
        finish_reveal(game, host(game))


def test_finishing_on_the_last_step_ends_the_game() -> None:
    game = play_to_reveal(3)
    walk_forward(game)

    finish_reveal(game, host(game))

    assert game.phase is Phase.DONE


def test_the_pointer_cannot_move_before_the_reveal() -> None:
    game = started(3)

    with pytest.raises(WrongPhase):
        reveal_next(game, host(game))


def test_the_pointer_cannot_move_after_the_game_is_done() -> None:
    game = play_to_reveal(3)
    walk_forward(game)
    finish_reveal(game, host(game))

    with pytest.raises(WrongPhase):
        reveal_next(game, host(game))
