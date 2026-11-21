"""The transitions: every legal way a game can change.

Each function takes the `Game` and mutates it, or raises one of the errors in
`errors.py` if the move is not legal right now. Nothing here does I/O, and all
randomness arrives as an injected `random.Random`, so any game can be replayed
exactly from a seed.
"""

from __future__ import annotations

import random

from game_engine.errors import NotAllowed, WrongPhase
from game_engine.models import (
    MAX_NAME_LENGTH,
    MAX_PLAYERS,
    MIN_PLAYERS,
    Book,
    Game,
    Phase,
    Player,
)
from game_engine.words import WordBank, load_words

__all__ = [
    "add_player",
    "deal_words",
    "kick",
    "new_game",
    "shuffle_seats",
    "start",
]


def new_game(game_id: str, code: str) -> Game:
    """An empty lobby. The first player to join becomes the host."""
    return Game(id=game_id, code=code)


def _require_phase(game: Game, phase: Phase, action: str) -> None:
    if game.phase is not phase:
        raise WrongPhase(f"cannot {action} while the game is {game.phase}")


def _reindex(game: Game) -> None:
    """Make every player's `idx` match its position after the list changes."""
    for position, player in enumerate(game.players):
        player.idx = position


# -- lobby ---------------------------------------------------------------


def add_player(game: Game, name: str, token: str) -> Player:
    """Seat a new player. The first one becomes the host.

    No special case for the host: whoever arrives first carries the flag, and
    `Game.host_idx` reads it back wherever the seat happens to be.
    """
    _require_phase(game, Phase.LOBBY, "join")

    name = name.strip()
    if not name:
        raise NotAllowed("a player needs a name")
    if len(name) > MAX_NAME_LENGTH:
        raise NotAllowed(f"names are at most {MAX_NAME_LENGTH} characters")
    if len(game.players) >= MAX_PLAYERS:
        raise NotAllowed(f"a room holds at most {MAX_PLAYERS} players")

    player = Player(
        idx=len(game.players),
        name=name,
        token=token,
        is_host=not game.players,
    )
    game.players.append(player)
    return player


def shuffle_seats(game: Game, rng: random.Random) -> None:
    """Randomise the seat order. Lobby only: starting freezes it."""
    _require_phase(game, Phase.LOBBY, "shuffle the seats")
    rng.shuffle(game.players)
    _reindex(game)


def kick(game: Game, seat: int) -> Player:
    """Remove a player and invalidate their token.

    Removing them from the list is what invalidates the token: nothing looks it
    up any more. Only legal in the lobby, where seats are not yet frozen.
    """
    _require_phase(game, Phase.LOBBY, "remove a player")

    if not 0 <= seat < len(game.players):
        raise NotAllowed(f"no player in seat {seat}")
    if game.players[seat].is_host:
        raise NotAllowed("the host cannot be removed")

    removed = game.players.pop(seat)
    _reindex(game)
    return removed


def start(game: Game, rng: random.Random) -> None:
    """Begin the game: freeze the seats, make the books, deal the first words."""
    _require_phase(game, Phase.LOBBY, "start the game")

    if len(game.players) < MIN_PLAYERS:
        raise NotAllowed(f"a game needs at least {MIN_PLAYERS} players")

    game.books = [Book(owner_idx=seat) for seat in range(len(game.players))]
    game.bank = WordBank(list(load_words()), rng)
    game.phase = Phase.ROUND
    game.round = 0
    deal_words(game)


def deal_words(game: Game) -> None:
    """Deal each player their round-0 options from the shared bank."""
    assert game.bank is not None
    for seat in range(len(game.players)):
        game.bank.deal(seat)
