"""Shared helpers for engine tests."""

import random

import pytest

from game_engine.game import add_player, advance_round, new_game, pick_word, start, submit
from game_engine.models import Game, PageKind
from game_engine.rotation import page_kind


@pytest.fixture
def rng() -> random.Random:
    return random.Random(1234)


def lobby(player_count: int = 3) -> Game:
    """A lobby with `player_count` players named p0, p1, ... and tokens t0, t1, ..."""
    game = new_game("g1", "KQFM")
    for seat in range(player_count):
        add_player(game, f"p{seat}", f"t{seat}")
    return game


def started(player_count: int = 3, seed: int = 7) -> Game:
    game = lobby(player_count)
    start(game, random.Random(seed))
    return game


def play_round(game: Game, skip: set[int] | None = None) -> None:
    """Every seat submits a page of the right kind for the current round."""
    skip = skip or set()
    kind = page_kind(game.round)
    for seat in range(game.player_count):
        if seat in skip:
            continue
        if game.round == 0 and game.books[seat].word is None:
            assert game.bank is not None
            pick_word(game, seat, game.bank.options_for(seat)[0])
        if kind is PageKind.TEXT:
            submit(game, seat, text=f"guess-{seat}-r{game.round}")
        else:
            submit(game, seat, strokes={"v": 1, "w": 800, "h": 600, "ops": [], "by": seat})
    if not skip:
        advance_round(game)


def play_to_reveal(player_count: int = 3, seed: int = 7) -> Game:
    game = started(player_count, seed)
    for _ in range(player_count):
        play_round(game)
    return game


def tagged_round(game: Game) -> None:
    """Play a round where every page carries a tag identifying who wrote it.

    Lets a test assert exactly which pages ended up in a player's view.
    """
    kind = page_kind(game.round)
    for seat in range(game.player_count):
        if game.round == 0:
            pick_word(game, seat, f"WORD-{seat}")
        tag = f"PAGE-{seat}-R{game.round}"
        if kind is PageKind.TEXT:
            submit(game, seat, text=tag)
        else:
            submit(game, seat, strokes={"v": 1, "w": 800, "h": 600, "ops": [], "tag": tag})
    advance_round(game)
