"""Tests for the word bank.

The headline guarantee is that no two players are ever dealt the same word, so
most of these hammer that invariant from different directions.
"""

import random

import pytest

from game_engine.words import (
    DEFAULT_OPTION_COUNT,
    WordBank,
    WordBankExhausted,
    load_words,
)

PLAYER_COUNTS = range(3, 11)


def make_bank(seed: int = 0, words: list[str] | None = None) -> WordBank:
    return WordBank(words if words is not None else list(load_words()), random.Random(seed))


# -- the bundled list ----------------------------------------------------


def test_bundled_word_list_is_usable() -> None:
    words = load_words()

    assert len(words) >= 200
    assert len(set(words)) == len(words), "duplicate words would break uniqueness"
    assert all(word == word.lower().strip() for word in words)
    assert all(1 <= len(word) <= 20 for word in words), "must fit the 100-char text cap"


def test_bundled_list_covers_the_worst_case_table() -> None:
    """10 players shuffling repeatedly must never exhaust the bank."""
    bank = make_bank()
    for _ in range(20):
        for seat in range(10):
            bank.deal(seat)


# -- uniqueness ----------------------------------------------------------


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_no_two_players_are_dealt_the_same_word(player_count: int) -> None:
    bank = make_bank(seed=player_count)

    dealt = [word for seat in range(player_count) for word in bank.deal(seat)]

    assert len(dealt) == player_count * DEFAULT_OPTION_COUNT
    assert len(set(dealt)) == len(dealt)


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_uniqueness_survives_repeated_shuffles(player_count: int) -> None:
    """Every seat shuffles ten times; at no point may two seats share a word."""
    bank = make_bank(seed=player_count)
    for seat in range(player_count):
        bank.deal(seat)

    for _ in range(10):
        for seat in range(player_count):
            bank.deal(seat)

            live = [word for s in range(player_count) for word in bank.options_for(s)]
            assert len(set(live)) == len(live), "two seats are holding the same word"


def test_a_shuffle_never_returns_a_word_another_player_holds() -> None:
    bank = make_bank(seed=7)
    for seat in range(4):
        bank.deal(seat)
    others = {word for seat in (1, 2, 3) for word in bank.options_for(seat)}

    for _ in range(30):
        assert not set(bank.deal(0)) & others


def test_a_shuffle_replaces_every_option() -> None:
    bank = make_bank(seed=3)
    first = bank.deal(0)

    second = bank.deal(0)

    assert set(first).isdisjoint(second)
    assert bank.options_for(0) == second


# -- picking -------------------------------------------------------------


def test_a_picked_word_is_never_dealt_again() -> None:
    """Two books must never start from the same word."""
    bank = make_bank(seed=11, words=[f"w{i}" for i in range(12)])
    chosen = bank.deal(0)[0]
    bank.pick(0, chosen)

    for _ in range(40):
        for seat in range(3):
            assert chosen not in bank.deal(seat)


def test_unpicked_options_return_to_circulation() -> None:
    """A tiny bank only works if the two rejected options come back."""
    bank = make_bank(seed=5, words=["a", "b", "c"])
    options = bank.deal(0)
    bank.pick(0, options[0])

    recycled = bank.deal(1, count=2)

    assert set(recycled) == set(options[1:])


def test_a_typed_word_is_not_retired() -> None:
    """Typed words are deliberately not compared with other players' (section 1)."""
    bank = make_bank(seed=2, words=[f"w{i}" for i in range(6)])
    bank.deal(0)

    bank.pick(0, "something nobody was dealt")

    assert bank.options_for(0) == ()


def test_picking_releases_the_seats_other_options() -> None:
    bank = make_bank(seed=4)
    options = bank.deal(0)

    bank.pick(0, options[0])

    assert bank.options_for(0) == ()


# -- recycling and limits ------------------------------------------------


def test_the_pool_recycles_before_it_runs_dry() -> None:
    """Six words, two seats, many shuffles: only recycling makes this possible."""
    bank = make_bank(seed=9, words=[f"w{i}" for i in range(6)])

    for _ in range(25):
        first = bank.deal(0)
        second = bank.deal(1)
        assert set(first).isdisjoint(second)


def test_an_exhausted_bank_fails_loudly() -> None:
    bank = make_bank(words=["only", "four", "words", "here"])
    bank.deal(0, count=2)

    with pytest.raises(WordBankExhausted):
        bank.deal(1, count=3)


def test_a_retired_word_is_not_recycled_to_fill_the_pool() -> None:
    bank = make_bank(seed=6, words=["a", "b", "c", "d"])
    options = bank.deal(0, count=2)
    bank.pick(0, options[0])

    with pytest.raises(WordBankExhausted):
        bank.deal(1, count=4)


def test_an_empty_bank_is_rejected() -> None:
    with pytest.raises(ValueError):
        WordBank([], random.Random(0))


def test_duplicate_input_words_are_collapsed() -> None:
    bank = WordBank(["a", "a", "b"], random.Random(0))

    assert set(bank.deal(0, count=2)) == {"a", "b"}


def test_a_non_positive_count_is_rejected() -> None:
    bank = make_bank()

    with pytest.raises(ValueError):
        bank.deal(0, count=0)


# -- determinism ---------------------------------------------------------


def test_the_same_seed_deals_the_same_words() -> None:
    """Injected randomness, so a failing game can be replayed exactly."""
    assert make_bank(seed=42).deal(0) == make_bank(seed=42).deal(0)


def test_different_seeds_deal_differently() -> None:
    assert make_bank(seed=1).deal(0) != make_bank(seed=2).deal(0)
