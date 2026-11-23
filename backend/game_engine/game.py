"""The transitions: every legal way a game can change.

Each function takes the `Game` and mutates it, or raises one of the errors in
`errors.py` if the move is not legal right now. Nothing here does I/O, and all
randomness arrives as an injected `random.Random`, so any game can be replayed
exactly from a seed.
"""

from __future__ import annotations

import random

from game_engine.errors import InvalidSubmission, NotAllowed, WrongPhase
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
from game_engine.rotation import book_index, page_kind
from game_engine.words import WordBank, load_words

__all__ = [
    "add_player",
    "advance_round",
    "all_submitted",
    "book_for",
    "deal_words",
    "enter_reveal",
    "finish_reveal",
    "has_submitted",
    "is_last_step",
    "kick",
    "new_game",
    "pick_word",
    "previous_page",
    "reveal_next",
    "reveal_prev",
    "reveal_step_count",
    "shuffle_seats",
    "shuffle_words",
    "skip_player",
    "start",
    "submit",
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


# -- rounds --------------------------------------------------------------


def book_for(game: Game, seat: int) -> Book:
    """The book this seat is working on this round."""
    return game.books[book_index(seat, game.round, game.player_count)]


def has_submitted(game: Game, seat: int) -> bool:
    """Whether this seat has already filed its page for this round.

    Derived from the book rather than tracked separately: the page either
    exists or it does not, so the two can never disagree.
    """
    return len(book_for(game, seat).pages) > game.round


def previous_page(game: Game, seat: int) -> Page | None:
    """The one page this seat is allowed to see: the last one in its book.

    Round 0 has no previous page -- the player draws the word they picked.
    """
    if game.round == 0:
        return None
    return book_for(game, seat).pages[game.round - 1]


def pick_word(game: Game, seat: int, text: str) -> None:
    """Choose the word for your own book. Round 0 only, before you submit.

    The word is stored on the book and stays hidden until the reveal. Words the
    player typed are not checked against anyone else's, because such a check
    would leak what another player chose (BUILD_PLAN.md, section 1).
    """
    _require_phase(game, Phase.ROUND, "pick a word")
    if game.round != 0:
        raise WrongPhase("words are only picked in the first round")
    if has_submitted(game, seat):
        raise NotAllowed("your drawing is already in")

    text = text.strip()
    if not text:
        raise InvalidSubmission("a word is required")
    if len(text) > MAX_TEXT_LENGTH:
        raise InvalidSubmission(f"words are at most {MAX_TEXT_LENGTH} characters")

    assert game.bank is not None
    game.books[seat].word = text
    game.bank.pick(seat, text)


def shuffle_words(game: Game, seat: int) -> tuple[str, ...]:
    """Swap this seat's three options for three nobody else is holding."""
    _require_phase(game, Phase.ROUND, "shuffle words")
    if game.round != 0:
        raise WrongPhase("words are only dealt in the first round")
    if game.books[seat].word is not None:
        raise NotAllowed("you have already chosen your word")

    assert game.bank is not None
    return game.bank.deal(seat)


def submit(
    game: Game,
    seat: int,
    *,
    text: str | None = None,
    strokes: dict | None = None,
) -> None:
    """File this seat's page for the current round.

    Idempotent per player per round: a repeat submission is ignored rather than
    rejected, because a flaky connection retrying should not look like an
    error.
    """
    _require_phase(game, Phase.ROUND, "submit a page")

    if has_submitted(game, seat):
        return

    expected = page_kind(game.round)
    if game.round == 0 and game.books[seat].word is None:
        raise InvalidSubmission("pick a word before drawing it")

    if expected is PageKind.TEXT:
        if text is None:
            raise InvalidSubmission("this round expects a guess")
        text = text.strip()
        if not text:
            raise InvalidSubmission("a guess is required")
        if len(text) > MAX_TEXT_LENGTH:
            raise InvalidSubmission(f"guesses are at most {MAX_TEXT_LENGTH} characters")
        page = Page(kind=expected, author_idx=seat, text=text)
    else:
        if strokes is None:
            raise InvalidSubmission("this round expects a drawing")
        page = Page(kind=expected, author_idx=seat, strokes=strokes)

    book_for(game, seat).pages.append(page)


def skip_player(game: Game, seat: int) -> None:
    """File a blank page for a player who has dropped out of this round.

    The host's escape hatch so one locked phone cannot stall everyone. If the
    player never picked a word, one is dealt for them, otherwise their book
    would have no word at the reveal.
    """
    _require_phase(game, Phase.ROUND, "skip a player")

    if has_submitted(game, seat):
        return

    assert game.bank is not None
    if game.round == 0 and game.books[seat].word is None:
        fallback = game.bank.options_for(seat) or game.bank.deal(seat)
        pick_word(game, seat, fallback[0])

    kind = page_kind(game.round)
    page = Page(
        kind=kind,
        author_idx=seat,
        text="" if kind is PageKind.TEXT else None,
        strokes={"v": 1, "w": 800, "h": 600, "ops": []} if kind is PageKind.STROKES else None,
        skipped=True,
    )
    book_for(game, seat).pages.append(page)


def all_submitted(game: Game) -> bool:
    """Rounds end when everyone has filed, not on a timer (section 1)."""
    return all(len(book.pages) > game.round for book in game.books)


def advance_round(game: Game) -> None:
    """Move every book on one seat, or begin the reveal after the last round."""
    _require_phase(game, Phase.ROUND, "advance the round")
    if not all_submitted(game):
        raise NotAllowed("not everyone has submitted")

    game.round += 1
    if game.round >= game.round_count:
        enter_reveal(game)


def enter_reveal(game: Game) -> None:
    """Open every book to everyone. The secrecy rule ends here."""
    game.phase = Phase.REVEAL
    game.reveal = Reveal(book=0, step=0)


# -- the reveal ----------------------------------------------------------


def reveal_step_count(game: Game, book: int) -> int:
    """Steps in a book: the word card, then one per page."""
    return 1 + len(game.books[book].pages)


def is_last_step(game: Game) -> bool:
    """Whether the pointer is on the final step of the final book."""
    assert game.reveal is not None
    last_book = len(game.books) - 1
    return (
        game.reveal.book == last_book and game.reveal.step == reveal_step_count(game, last_book) - 1
    )


def _require_host(game: Game, seat: int, action: str) -> None:
    if seat != game.host_idx:
        raise NotAllowed(f"only the host can {action}")


def reveal_next(game: Game, seat: int) -> None:
    """Move the shared pointer forward one step, for everyone.

    Running off the end of a book lands on the word card of the next one.
    Clamps at the very end rather than raising: the host is shown "Finish game"
    there, so a stray Next is a double-tap, not a bug worth failing a game for.
    """
    _require_phase(game, Phase.REVEAL, "move the reveal")
    _require_host(game, seat, "turn the pages")
    assert game.reveal is not None

    if is_last_step(game):
        return
    if game.reveal.step < reveal_step_count(game, game.reveal.book) - 1:
        game.reveal.step += 1
    else:
        game.reveal.book += 1
        game.reveal.step = 0


def reveal_prev(game: Game, seat: int) -> None:
    """Move the pointer back one step, over book boundaries. Clamps at the start."""
    _require_phase(game, Phase.REVEAL, "move the reveal")
    _require_host(game, seat, "turn the pages")
    assert game.reveal is not None

    if game.reveal.step > 0:
        game.reveal.step -= 1
    elif game.reveal.book > 0:
        game.reveal.book -= 1
        game.reveal.step = reveal_step_count(game, game.reveal.book) - 1


def finish_reveal(game: Game, seat: int) -> None:
    """End the game. Only legal on the last step of the last book."""
    _require_phase(game, Phase.REVEAL, "finish the game")
    _require_host(game, seat, "finish the game")

    if not is_last_step(game):
        raise NotAllowed("there are still pages to show")

    game.phase = Phase.DONE
