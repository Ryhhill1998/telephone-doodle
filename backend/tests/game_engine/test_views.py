"""What each player is allowed to see.

These are the tests that matter most in this package: a leak here would let a
player read another book before the reveal, which quietly ruins the game.
"""

import json
import re

import pytest

from game_engine.game import pick_word, reveal_next, shuffle_words
from game_engine.models import Phase
from game_engine.rotation import book_index
from game_engine.views import view_for
from tests.game_engine.conftest import lobby, play_to_reveal, started, tagged_round

PLAYER_COUNTS = range(3, 11)


def tags_in(view: dict) -> set[str]:
    """Every page tag and word visible anywhere in a serialised view."""
    blob = json.dumps(view)
    return set(re.findall(r"(?:PAGE-\d+-R\d+|WORD-\d+)", blob))


def tagged_game(player_count: int, rounds: int):
    game = started(player_count)
    for _ in range(rounds):
        tagged_round(game)
    return game


# -- secrecy -------------------------------------------------------------


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_round_zero_shows_you_only_your_own_word(player_count: int) -> None:
    game = started(player_count)
    for seat in range(player_count):
        pick_word(game, seat, f"WORD-{seat}")

    for seat in range(player_count):
        assert tags_in(view_for(game, seat)) == {f"WORD-{seat}"}


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_you_see_exactly_one_previous_page_and_nothing_else(player_count: int) -> None:
    """The heart of it: one page in, one page out, no history, no other books."""
    for rounds in range(1, player_count):
        game = tagged_game(player_count, rounds)

        for seat in range(player_count):
            book = book_index(seat, game.round, player_count)
            author = (book + game.round - 1) % player_count
            expected = {f"PAGE-{author}-R{game.round - 1}"}

            assert tags_in(view_for(game, seat)) == expected, (
                f"{player_count} players, round {game.round}, seat {seat}"
            )


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_the_earlier_pages_of_your_own_book_stay_hidden(player_count: int) -> None:
    """You hold the book, but you may not read the story so far."""
    game = tagged_game(player_count, 2)

    for seat in range(player_count):
        visible = tags_in(view_for(game, seat))
        assert not any(tag.endswith("R0") for tag in visible)


def test_a_word_you_typed_is_never_shown_to_anyone_else() -> None:
    game = started(4)
    pick_word(game, 1, "WORD-1")

    for seat in (0, 2, 3):
        assert "WORD-1" not in json.dumps(view_for(game, seat))


def test_your_dealt_options_are_only_yours() -> None:
    game = started(5)
    assert game.bank is not None
    mine = set(game.bank.options_for(0))

    for seat in range(1, 5):
        theirs = set(view_for(game, seat)["options"])
        assert not mine & theirs


def test_shuffling_updates_only_your_own_options() -> None:
    game = started(4)

    fresh = shuffle_words(game, 2)

    assert view_for(game, 2)["options"] == list(fresh)
    assert view_for(game, 0)["options"] != list(fresh)


# -- tokens --------------------------------------------------------------


@pytest.mark.parametrize("phase_builder", [lambda: lobby(4), lambda: started(4)])
def test_a_view_never_contains_a_token(phase_builder) -> None:
    game = phase_builder()
    tokens = [p.token for p in game.players]

    for seat in range(game.player_count):
        blob = json.dumps(view_for(game, seat))
        assert not any(token in blob for token in tokens)


def test_no_token_appears_during_the_reveal() -> None:
    game = play_to_reveal(4)
    tokens = [p.token for p in game.players]

    blob = json.dumps(view_for(game, 0))

    assert not any(token in blob for token in tokens)


# -- lobby ---------------------------------------------------------------


def test_the_lobby_view_lists_seats_in_order_with_the_host_marked() -> None:
    game = lobby(4)

    view = view_for(game, 2)

    assert view["phase"] == Phase.LOBBY
    assert view["you"] == 2
    assert view["host"] == 0
    assert [p["name"] for p in view["players"]] == ["p0", "p1", "p2", "p3"]
    assert [p["host"] for p in view["players"]] == [True, False, False, False]


def test_the_lobby_view_has_no_round_or_reveal_data() -> None:
    view = view_for(lobby(3), 0)

    assert "previous" not in view
    assert "reveal" not in view


# -- round ---------------------------------------------------------------


def test_the_round_view_reports_who_has_finished() -> None:
    game = started(3)
    pick_word(game, 1, "kite")
    from game_engine.game import submit

    submit(game, 1, strokes={"v": 1, "w": 800, "h": 600, "ops": []})

    view = view_for(game, 0)

    assert [p["submitted"] for p in view["players"]] == [False, True, False]
    assert view["submitted"] is False
    assert view_for(game, 1)["submitted"] is True


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_the_round_view_counts_rounds_from_the_player_count(player_count: int) -> None:
    view = view_for(started(player_count), 0)

    assert view["round"] == 0
    assert view["round_count"] == player_count


def test_round_zero_has_no_previous_page() -> None:
    assert view_for(started(3), 0)["previous"] is None


def test_later_rounds_carry_the_previous_pages_kind_and_author() -> None:
    game = tagged_game(4, 1)

    previous = view_for(game, 0)["previous"]

    assert previous["kind"] == "strokes"
    assert previous["author"] == 3
    assert previous["skipped"] is False


# -- reveal --------------------------------------------------------------


def test_the_reveal_opens_every_book_to_everyone() -> None:
    game = play_to_reveal(4)

    for seat in range(4):
        reveal = view_for(game, seat)["reveal"]
        assert len(reveal["books"]) == 4
        assert all(book["word"] for book in reveal["books"])
        assert all(len(book["pages"]) == 4 for book in reveal["books"])


def test_every_player_sees_the_same_pointer() -> None:
    """This is what keeps all the screens together."""
    game = play_to_reveal(5)
    reveal_next(game, game.host_idx)
    reveal_next(game, game.host_idx)

    pointers = {
        (view_for(game, s)["reveal"]["book"], view_for(game, s)["reveal"]["step"]) for s in range(5)
    }

    assert pointers == {(0, 2)}


def test_the_reveal_view_drops_the_round_fields() -> None:
    view = view_for(play_to_reveal(3), 0)

    assert "previous" not in view
    assert "options" not in view


def test_the_done_view_is_just_the_players() -> None:
    from game_engine.game import finish_reveal, is_last_step

    game = play_to_reveal(3)
    while not is_last_step(game):
        reveal_next(game, game.host_idx)
    finish_reveal(game, game.host_idx)

    view = view_for(game, 0)

    assert view["phase"] == Phase.DONE
    assert "reveal" not in view


# -- json safety ---------------------------------------------------------


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_every_view_survives_json(player_count: int) -> None:
    game = tagged_game(player_count, 1)

    for seat in range(player_count):
        view = view_for(game, seat)
        assert json.loads(json.dumps(view)) == view
