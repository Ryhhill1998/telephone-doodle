"""Shared helpers for engine tests."""

import random

import pytest

from game_engine.game import add_player, new_game, start
from game_engine.models import Game


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
