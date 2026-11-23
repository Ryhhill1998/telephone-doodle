"""Picking a word, submitting pages, and moving the books round the circle."""

from itertools import pairwise

import pytest

from game_engine.errors import InvalidSubmission, NotAllowed, WrongPhase
from game_engine.game import (
    advance_round,
    all_submitted,
    book_for,
    has_submitted,
    pick_word,
    previous_page,
    shuffle_words,
    skip_player,
    submit,
)
from game_engine.models import PageKind, Phase
from game_engine.rotation import book_index
from tests.game_engine.conftest import play_round, play_to_reveal, started

PLAYER_COUNTS = range(3, 11)


def draw(game, seat):
    submit(game, seat, strokes={"v": 1, "w": 800, "h": 600, "ops": []})


# -- round 0: pick then draw ---------------------------------------------


def test_a_word_must_be_picked_before_it_can_be_drawn() -> None:
    game = started(3)

    with pytest.raises(InvalidSubmission):
        draw(game, 0)


def test_the_picked_word_lands_on_your_own_book() -> None:
    game = started(4)

    pick_word(game, 2, "volcano")

    assert game.books[2].word == "volcano"


def test_a_typed_word_is_accepted() -> None:
    game = started(3)

    pick_word(game, 0, "  nana's cat  ")

    assert game.books[0].word == "nana's cat"


def test_an_empty_or_over_long_word_is_rejected() -> None:
    game = started(3)

    with pytest.raises(InvalidSubmission):
        pick_word(game, 0, "   ")
    with pytest.raises(InvalidSubmission):
        pick_word(game, 0, "x" * 101)


def test_shuffling_words_replaces_the_options() -> None:
    game = started(3)
    assert game.bank is not None
    before = game.bank.options_for(0)

    after = shuffle_words(game, 0)

    assert set(before).isdisjoint(after)


def test_words_cannot_be_shuffled_after_choosing() -> None:
    game = started(3)
    pick_word(game, 0, "castle")

    with pytest.raises(NotAllowed):
        shuffle_words(game, 0)


def test_a_word_cannot_be_changed_once_the_drawing_is_in() -> None:
    game = started(3)
    pick_word(game, 0, "castle")
    draw(game, 0)

    with pytest.raises(NotAllowed):
        pick_word(game, 0, "second thoughts")


def test_an_over_long_guess_is_rejected() -> None:
    game = started(3)
    play_round(game)

    with pytest.raises(InvalidSubmission):
        submit(game, 0, text="x" * 101)


def test_words_are_only_picked_in_the_first_round() -> None:
    game = started(3)
    play_round(game)

    with pytest.raises(WrongPhase):
        pick_word(game, 0, "late")
    with pytest.raises(WrongPhase):
        shuffle_words(game, 0)


# -- submitting ----------------------------------------------------------


def test_submitting_is_idempotent_per_player_per_round() -> None:
    """A flaky connection retrying must not look like an error, or double-file."""
    game = started(3)
    pick_word(game, 0, "robot")

    draw(game, 0)
    draw(game, 0)

    assert len(game.books[0].pages) == 1


def test_a_guess_is_rejected_when_a_drawing_is_due() -> None:
    game = started(3)
    pick_word(game, 0, "robot")

    with pytest.raises(InvalidSubmission):
        submit(game, 0, text="not a drawing")


def test_a_drawing_is_rejected_when_a_guess_is_due() -> None:
    game = started(3)
    play_round(game)

    with pytest.raises(InvalidSubmission):
        draw(game, 0)


def test_an_empty_guess_is_rejected() -> None:
    game = started(3)
    play_round(game)

    with pytest.raises(InvalidSubmission):
        submit(game, 0, text="  ")


def test_has_submitted_tracks_the_round() -> None:
    game = started(3)
    pick_word(game, 1, "kite")

    assert not has_submitted(game, 1)
    draw(game, 1)
    assert has_submitted(game, 1)


def test_a_round_ends_only_when_everyone_has_filed() -> None:
    game = started(4)
    for seat in range(3):
        pick_word(game, seat, f"w{seat}")
        draw(game, seat)

    assert not all_submitted(game)
    with pytest.raises(NotAllowed):
        advance_round(game)


# -- rotation through a whole game ---------------------------------------


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_a_full_game_gives_every_book_a_page_per_round(player_count: int) -> None:
    game = play_to_reveal(player_count)

    assert game.phase is Phase.REVEAL
    assert all(len(book.pages) == player_count for book in game.books)


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_every_book_is_written_by_every_player_exactly_once(player_count: int) -> None:
    game = play_to_reveal(player_count)

    for book in game.books:
        authors = [page.author_idx for page in book.pages]
        assert sorted(authors) == list(range(player_count))


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_page_kinds_alternate_in_every_book(player_count: int) -> None:
    game = play_to_reveal(player_count)

    for book in game.books:
        kinds = [page.kind for page in book.pages]
        assert kinds[0] is PageKind.STROKES
        assert all(a is not b for a, b in pairwise(kinds))


@pytest.mark.parametrize("player_count", [3, 5, 7, 9])
def test_odd_games_end_on_a_drawing_nobody_guesses(player_count: int) -> None:
    game = play_to_reveal(player_count)

    assert all(book.pages[-1].kind is PageKind.STROKES for book in game.books)


def test_you_work_on_the_book_of_the_seat_before_you_in_round_one() -> None:
    game = started(5)
    play_round(game)

    assert book_for(game, 0) is game.books[4]
    assert book_for(game, 3) is game.books[2]


# -- what a player can see -----------------------------------------------


def test_round_zero_has_no_previous_page() -> None:
    game = started(4)

    assert previous_page(game, 0) is None


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_you_only_ever_see_the_immediately_previous_page(player_count: int) -> None:
    game = started(player_count)
    for _ in range(player_count - 1):
        play_round(game)

        for seat in range(player_count):
            expected_book = game.books[book_index(seat, game.round, player_count)]
            assert previous_page(game, seat) is expected_book.pages[game.round - 1]


# -- skipping ------------------------------------------------------------


def test_skipping_files_a_blank_drawing_and_a_word() -> None:
    game = started(3)

    skip_player(game, 2)

    page = game.books[2].pages[0]
    assert page.skipped is True
    assert page.strokes == {"v": 1, "w": 800, "h": 600, "ops": []}
    assert game.books[2].word is not None, "a skipped book still needs a word to reveal"


def test_skipping_files_a_blank_guess_in_a_guessing_round() -> None:
    game = started(3)
    play_round(game)

    skip_player(game, 1)

    page = book_for(game, 1).pages[game.round]
    assert page.kind is PageKind.TEXT
    assert page.text == ""
    assert page.skipped is True


def test_skipping_someone_who_already_submitted_does_nothing() -> None:
    game = started(3)
    pick_word(game, 0, "snail")
    draw(game, 0)

    skip_player(game, 0)

    assert len(game.books[0].pages) == 1
    assert game.books[0].pages[0].skipped is False


def test_a_skipped_player_lets_the_round_finish() -> None:
    game = started(3)
    play_round(game, skip={2})

    skip_player(game, 2)

    assert all_submitted(game)
    advance_round(game)
    assert game.round == 1
