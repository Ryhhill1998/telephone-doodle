"""Pure game rules for Telephone Doodle.

This package holds the rules and nothing else: plain dataclasses and functions
with no FastAPI, no sockets, no clock and no database. `rooms` calls into it;
it never calls back out. All randomness is injected as a `random.Random` so a
game can be replayed exactly in tests.

The surface `rooms` needs:

- `new_game`, `add_player`, `shuffle_seats`, `kick`, `start` -- the lobby
- `pick_word`, `shuffle_words`, `submit`, `skip_player`, `all_submitted`,
  `advance_round` -- the rounds
- `reveal_next`, `reveal_prev`, `finish_reveal` -- the shared pointer
- `view_for` -- the personalised snapshot sent to each player
- `to_dict` / `from_dict` -- the durable snapshot written to Postgres
"""

from game_engine.errors import GameError, InvalidSubmission, NotAllowed, WrongPhase
from game_engine.game import (
    add_player,
    advance_round,
    all_submitted,
    deal_words,
    enter_reveal,
    finish_reveal,
    has_submitted,
    is_last_step,
    kick,
    new_game,
    pick_word,
    previous_page,
    reveal_next,
    reveal_prev,
    reveal_step_count,
    shuffle_seats,
    shuffle_words,
    skip_player,
    start,
    submit,
)
from game_engine.models import (
    MAX_NAME_LENGTH,
    MAX_PLAYERS,
    MAX_TEXT_LENGTH,
    MIN_PLAYERS,
    Book,
    Game,
    Page,
    PageKind,
    Phase,
    Player,
    Reveal,
)
from game_engine.rotation import book_index, page_kind, seat_holding
from game_engine.snapshots import from_dict, to_dict
from game_engine.views import view_for
from game_engine.words import WordBank, WordBankExhausted, load_words

__all__ = [
    "MAX_NAME_LENGTH",
    "MAX_PLAYERS",
    "MAX_TEXT_LENGTH",
    "MIN_PLAYERS",
    "Book",
    "Game",
    "GameError",
    "InvalidSubmission",
    "NotAllowed",
    "Page",
    "PageKind",
    "Phase",
    "Player",
    "Reveal",
    "WordBank",
    "WordBankExhausted",
    "WrongPhase",
    "add_player",
    "advance_round",
    "all_submitted",
    "book_index",
    "deal_words",
    "enter_reveal",
    "finish_reveal",
    "from_dict",
    "has_submitted",
    "is_last_step",
    "kick",
    "load_words",
    "new_game",
    "page_kind",
    "pick_word",
    "previous_page",
    "reveal_next",
    "reveal_prev",
    "reveal_step_count",
    "seat_holding",
    "shuffle_seats",
    "shuffle_words",
    "skip_player",
    "start",
    "submit",
    "to_dict",
    "view_for",
]
