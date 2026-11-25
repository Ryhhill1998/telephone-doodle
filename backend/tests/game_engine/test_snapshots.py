"""Whole-game snapshots: a game must survive a restart at any point.

Everything round-trips through real json.dumps/loads, because the snapshot ends
up in a JSONB column; passing the dict straight back would not prove that.
"""

import json
import random

import pytest

from game_engine.game import (
    advance_round,
    finish_reveal,
    is_last_step,
    pick_word,
    reveal_next,
    skip_player,
    submit,
)
from game_engine.models import Phase
from game_engine.snapshots import from_dict, to_dict
from game_engine.views import view_for
from tests.game_engine.conftest import lobby, play_round, play_to_reveal, started

PLAYER_COUNTS = range(3, 11)


def reload(game):
    """Round-trip a game the way Postgres will."""
    return from_dict(json.loads(json.dumps(to_dict(game))), random.Random(0))


def at_every_phase(player_count: int = 4):
    """One game captured at each phase it passes through."""
    yield "lobby", lobby(player_count)

    fresh = started(player_count)
    yield "round-0-before-picking", fresh

    picking = started(player_count)
    pick_word(picking, 0, "castle")
    yield "round-0-after-picking", picking

    mid = started(player_count)
    play_round(mid)
    yield "round-1", mid

    late = started(player_count)
    for _ in range(player_count - 1):
        play_round(late)
    yield "last-round", late

    revealing = play_to_reveal(player_count)
    reveal_next(revealing, revealing.host_idx)
    reveal_next(revealing, revealing.host_idx)
    yield "reveal", revealing

    done = play_to_reveal(player_count)
    while not is_last_step(done):
        reveal_next(done, done.host_idx)
    finish_reveal(done, done.host_idx)
    yield "done", done


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_a_snapshot_round_trips_at_every_phase(player_count: int) -> None:
    for label, game in at_every_phase(player_count):
        assert to_dict(reload(game)) == to_dict(game), f"lost data at {label}"


@pytest.mark.parametrize("player_count", PLAYER_COUNTS)
def test_every_players_view_is_unchanged_by_a_reload(player_count: int) -> None:
    """What matters is not the bytes but that nobody's screen changes."""
    for label, game in at_every_phase(player_count):
        restored = reload(game)
        for seat in range(player_count):
            assert view_for(restored, seat) == view_for(game, seat), f"{label}, seat {seat}"


def test_tokens_survive_so_players_can_reconnect() -> None:
    game = started(5)
    tokens = [p.token for p in game.players]

    restored = reload(game)

    assert [p.token for p in restored.players] == tokens
    assert restored.player_by_token(tokens[3]) is restored.players[3]


def test_the_host_survives_a_reload() -> None:
    game = started(5)
    host_token = game.players[game.host_idx].token

    restored = reload(game)

    assert restored.players[restored.host_idx].token == host_token


def test_snapshot_size_for_a_full_ten_player_game() -> None:
    """How big `games.snapshot` gets for the biggest lobby v0 allows.

    Uses realistic drawings (the same small fixture every other test does),
    not the 200 KB-per-message cap a single stroke payload is separately held
    to (BUILD_PLAN.md, section 3) -- that bounds one player's one submission,
    not what a whole game's worth of them adds up to, which is what this
    reports (Step 5's review checklist).
    """
    game = play_to_reveal(10)

    size = len(json.dumps(to_dict(game)).encode())

    assert size < 50_000, f"a full 10-player game's snapshot was {size} bytes"


def test_the_reveal_pointer_survives_a_reload() -> None:
    """A player refreshing mid-reveal must land on the page everyone else is on."""
    game = play_to_reveal(4)
    for _ in range(6):
        reveal_next(game, game.host_idx)

    restored = reload(game)

    assert restored.reveal is not None
    assert (restored.reveal.book, restored.reveal.step) == (game.reveal.book, game.reveal.step)


def test_a_reloaded_game_can_be_played_on() -> None:
    """The real test of a snapshot: carry on and finish."""
    game = started(4)
    play_round(game)

    restored = reload(game)
    for _ in range(3):
        play_round(restored)

    assert restored.phase is Phase.REVEAL
    assert all(len(book.pages) == 4 for book in restored.books)


def test_a_reloaded_round_zero_keeps_everyone_their_own_words() -> None:
    game = started(6)
    before = {seat: game.bank.options_for(seat) for seat in range(6)}

    restored = reload(game)

    assert {seat: restored.bank.options_for(seat) for seat in range(6)} == before


def test_a_reloaded_game_still_refuses_to_repeat_a_word() -> None:
    game = started(5)
    pick_word(game, 0, game.bank.options_for(0)[0])
    chosen = game.books[0].word

    restored = reload(game)
    submit(restored, 0, strokes={"v": 1, "w": 800, "h": 600, "ops": []})
    for seat in range(1, 5):
        assert chosen not in restored.bank.options_for(seat)


def test_submitted_pages_survive_with_their_content() -> None:
    game = started(3)
    pick_word(game, 0, "lighthouse")
    submit(game, 0, strokes={"v": 1, "w": 800, "h": 600, "ops": [{"t": "f", "x": 0.5}]})

    restored = reload(game)

    page = restored.books[0].pages[0]
    assert page.strokes == {"v": 1, "w": 800, "h": 600, "ops": [{"t": "f", "x": 0.5}]}
    assert page.author_idx == 0
    assert page.skipped is False


def test_a_skipped_page_stays_marked_as_skipped() -> None:
    game = started(3)
    skip_player(game, 1)

    restored = reload(game)

    assert restored.books[1].pages[0].skipped is True


def test_an_unstarted_game_has_no_books_or_bank() -> None:
    snapshot = to_dict(lobby(3))

    assert snapshot["books"] == []
    assert snapshot["bank"] is None
    assert snapshot["reveal"] is None


def test_round_tripping_twice_is_stable() -> None:
    game = play_to_reveal(3)

    once = reload(game)

    assert to_dict(reload(once)) == to_dict(once)


def test_advancing_a_reloaded_round_still_works() -> None:
    game = started(3)
    play_round(game)
    play_round(game)

    restored = reload(game)
    play_round(restored)

    assert restored.round == 3 or restored.phase is Phase.REVEAL


def test_a_finished_game_round_trips() -> None:
    game = play_to_reveal(3)
    while not is_last_step(game):
        reveal_next(game, game.host_idx)
    finish_reveal(game, game.host_idx)

    restored = reload(game)

    assert restored.phase is Phase.DONE
    assert all(book.word for book in restored.books)


def test_all_submitted_is_recomputed_not_stored() -> None:
    game = started(3)
    for seat in range(3):
        pick_word(game, seat, f"w{seat}")
        submit(game, seat, strokes={"v": 1, "w": 800, "h": 600, "ops": []})

    restored = reload(game)

    assert restored.phase is Phase.ROUND
    advance_round(restored)
    assert restored.round == 1
