"""Joining, shuffling seats, removing players and starting."""

import random

import pytest

from game_engine.errors import NotAllowed, WrongPhase
from game_engine.game import add_player, kick, new_game, shuffle_seats, start
from game_engine.models import MAX_PLAYERS, Phase
from tests.game_engine.conftest import lobby, started


def test_a_new_game_starts_in_the_lobby() -> None:
    game = new_game("g1", "KQFM")

    assert game.phase is Phase.LOBBY
    assert game.players == []
    assert game.round == 0


def test_the_first_player_to_join_is_the_host() -> None:
    game = lobby(3)

    assert game.host_idx == 0
    assert [p.is_host for p in game.players] == [True, False, False]


def test_players_are_seated_in_join_order() -> None:
    game = lobby(4)

    assert [p.name for p in game.players] == ["p0", "p1", "p2", "p3"]
    assert [p.idx for p in game.players] == [0, 1, 2, 3]


def test_names_are_trimmed_and_required() -> None:
    game = new_game("g1", "KQFM")
    add_player(game, "  Jo  ", "t")

    assert game.players[0].name == "Jo"
    with pytest.raises(NotAllowed):
        add_player(game, "   ", "t2")


def test_an_over_long_name_is_rejected() -> None:
    game = new_game("g1", "KQFM")

    with pytest.raises(NotAllowed):
        add_player(game, "x" * 21, "t")


def test_a_room_holds_at_most_ten_players() -> None:
    game = lobby(MAX_PLAYERS)

    with pytest.raises(NotAllowed):
        add_player(game, "one too many", "t")


# -- shuffling -----------------------------------------------------------


def test_shuffling_reseats_everyone_and_keeps_indices_consistent() -> None:
    game = lobby(6)
    before = {p.token for p in game.players}

    shuffle_seats(game, random.Random(3))

    assert {p.token for p in game.players} == before
    assert [p.idx for p in game.players] == list(range(6))


def test_shuffling_moves_the_host_flag_with_the_player() -> None:
    """host_idx is derived, so the host follows their seat rather than a number."""
    game = lobby(6)
    host_token = game.players[game.host_idx].token

    shuffle_seats(game, random.Random(3))

    assert game.players[game.host_idx].token == host_token


def test_shuffling_is_deterministic_for_a_seed() -> None:
    first, second = lobby(8), lobby(8)

    shuffle_seats(first, random.Random(99))
    shuffle_seats(second, random.Random(99))

    assert [p.name for p in first.players] == [p.name for p in second.players]


# -- removing ------------------------------------------------------------


def test_removing_a_player_closes_the_gap() -> None:
    game = lobby(5)

    removed = kick(game, 2)

    assert removed.name == "p2"
    assert [p.name for p in game.players] == ["p0", "p1", "p3", "p4"]
    assert [p.idx for p in game.players] == [0, 1, 2, 3]


def test_a_removed_players_token_stops_working() -> None:
    game = lobby(4)
    token = game.players[1].token

    kick(game, 1)

    assert game.player_by_token(token) is None


def test_the_host_cannot_be_removed() -> None:
    game = lobby(4)

    with pytest.raises(NotAllowed):
        kick(game, game.host_idx)


def test_removing_an_unknown_seat_is_rejected() -> None:
    game = lobby(3)

    with pytest.raises(NotAllowed):
        kick(game, 9)


# -- starting ------------------------------------------------------------


def test_starting_needs_three_players() -> None:
    game = lobby(2)

    with pytest.raises(NotAllowed):
        start(game, random.Random(0))


@pytest.mark.parametrize("player_count", range(3, 11))
def test_starting_makes_one_book_per_player(player_count: int) -> None:
    game = started(player_count)

    assert game.phase is Phase.ROUND
    assert game.round == 0
    assert [b.owner_idx for b in game.books] == list(range(player_count))
    assert all(b.word is None and b.pages == [] for b in game.books)


@pytest.mark.parametrize("player_count", range(3, 11))
def test_starting_deals_everyone_three_distinct_words(player_count: int) -> None:
    game = started(player_count)
    assert game.bank is not None

    dealt = [w for seat in range(player_count) for w in game.bank.options_for(seat)]

    assert len(dealt) == player_count * 3
    assert len(set(dealt)) == len(dealt)


# -- the frozen seat order -----------------------------------------------


def test_seats_cannot_be_shuffled_after_the_start() -> None:
    game = started(4)

    with pytest.raises(WrongPhase):
        shuffle_seats(game, random.Random(0))


def test_players_cannot_be_removed_after_the_start() -> None:
    game = started(4)

    with pytest.raises(WrongPhase):
        kick(game, 1)


def test_players_cannot_join_after_the_start() -> None:
    game = started(4)

    with pytest.raises(WrongPhase):
        add_player(game, "latecomer", "t")


def test_a_game_cannot_be_started_twice() -> None:
    game = started(3)

    with pytest.raises(WrongPhase):
        start(game, random.Random(0))


def test_a_game_with_no_players_has_no_host() -> None:
    """Defensive: host_idx says so loudly rather than returning seat 0."""
    game = new_game("g1", "KQFM")

    with pytest.raises(LookupError):
        _ = game.host_idx
