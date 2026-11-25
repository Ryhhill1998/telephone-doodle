"""The word bank: dealing round-0 word options without ever repeating one.

All players' options are drawn from **one** shuffled bank without replacement,
so no two players are ever dealt the same word. A shuffle returns the player's
current options and draws fresh ones from the words nobody holds and nobody
has picked.

Purity: `WordBank` takes its vocabulary as an argument and its randomness as an
injected `random.Random`, so it is deterministic under test. `load_words()` is
the one function that touches the filesystem, reading the bundled `words.json`
once at import time.
"""

from __future__ import annotations

import json
import random
from collections import deque
from importlib.resources import files

__all__ = ["DEFAULT_OPTION_COUNT", "WordBank", "WordBankExhausted", "load_words"]

# Keys used in the snapshot written to games.snapshot.
_POOL, _HELD, _DISCARDED, _RETIRED = "pool", "held", "discarded", "retired"

DEFAULT_OPTION_COUNT = 3


class WordBankExhausted(RuntimeError):
    """Raised when the bank cannot produce enough distinct words.

    Unreachable in a real game: 10 players at 3 options each need 30 of 210
    words, and shuffled-away words are recycled. It exists so that a bank built
    from a short word list in a test fails loudly rather than silently repeating.
    """


def load_words() -> tuple[str, ...]:
    """Read the bundled word list. The only filesystem access in this package."""
    raw = files(__package__).joinpath("words.json").read_text(encoding="utf-8")
    return tuple(json.loads(raw))


class WordBank:
    """Hands out word options to seats, guaranteeing uniqueness across players.

    Every word is in exactly one of four places:

    - `_pool`      waiting to be dealt, in shuffled draw order
    - `_held`      currently on some player's screen
    - `_discarded` dealt once, shuffled away, reusable if the pool runs dry
    - `_retired`   picked by a player; never dealt again, so the reveal cannot
                   show two books that started from the same word
    """

    def __init__(self, words: list[str] | tuple[str, ...], rng: random.Random) -> None:
        unique = list(dict.fromkeys(words))
        if not unique:
            raise ValueError("a word bank needs at least one word")
        rng.shuffle(unique)

        self._rng = rng
        self._pool: deque[str] = deque(unique)
        self._held: dict[int, tuple[str, ...]] = {}
        self._discarded: list[str] = []
        self._retired: set[str] = set()

    # -- dealing ----------------------------------------------------------

    def deal(self, seat: int, count: int = DEFAULT_OPTION_COUNT) -> tuple[str, ...]:
        """Deal `count` words to `seat`, replacing whatever it currently holds.

        This is also what a shuffle does: the old options go back into
        circulation for *other* players and fresh ones are drawn, so a shuffle
        can never hand back a word another player is looking at.
        """
        if count <= 0:
            raise ValueError("count must be positive")

        self._release(seat)
        drawn = self._draw(count)
        self._held[seat] = drawn
        return drawn

    def options_for(self, seat: int) -> tuple[str, ...]:
        """The options currently on this seat's screen, or empty if none."""
        return self._held.get(seat, ())

    def pick(self, seat: int, word: str) -> None:
        """Record the word a seat chose, releasing its other options.

        A *dealt* word is retired so nobody else can be given it. A word the
        player typed themselves is deliberately not retired and not compared
        with anyone else's: any such check would leak what another player
        chose. Typed words may therefore collide, which the plan accepts.
        """
        held = self._held.pop(seat, ())
        if word in held:
            self._retired.add(word)
            self._discarded.extend(other for other in held if other != word)
        else:
            self._discarded.extend(held)

    # -- snapshots --------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        """A JSON-safe snapshot of the whole bank.

        The held options are included so that a player who reconnects mid
        round 0 is shown the *same* three words, rather than a fresh deal
        that might collide with another player's.

        `held` is a list of pairs, not a mapping: JSON object keys must be
        strings, and round-tripping seat numbers through strings is a bug
        waiting to happen.
        """
        return {
            _POOL: list(self._pool),
            _HELD: [[seat, list(options)] for seat, options in sorted(self._held.items())],
            _DISCARDED: list(self._discarded),
            _RETIRED: sorted(self._retired),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object], rng: random.Random) -> WordBank:
        """Rebuild a bank from `to_dict`, with fresh randomness.

        The rng is not part of the snapshot: which words come next only has to
        be unpredictable, never reproducible across a reload.

        Built without `__init__` on purpose, because the state is restored
        verbatim and must not be reshuffled.
        """
        bank = object.__new__(cls)
        bank._rng = rng
        bank._pool = deque(data[_POOL])  # type: ignore[arg-type]
        bank._held = {int(seat): tuple(options) for seat, options in data[_HELD]}  # type: ignore[misc,union-attr]
        bank._discarded = list(data[_DISCARDED])  # type: ignore[arg-type]
        bank._retired = set(data[_RETIRED])  # type: ignore[arg-type]
        return bank

    # -- internals --------------------------------------------------------

    def _release(self, seat: int) -> None:
        self._discarded.extend(self._held.pop(seat, ()))

    def _draw(self, count: int) -> tuple[str, ...]:
        if len(self._pool) < count:
            self._recycle()
        if len(self._pool) < count:
            raise WordBankExhausted(f"need {count} words, only {len(self._pool)} left undealt")
        return tuple(self._pool.popleft() for _ in range(count))

    def _recycle(self) -> None:
        """Return shuffled-away words to the back of the pool.

        Only `_discarded` is recycled, so a word someone is holding or has
        picked can never come back round.
        """
        if not self._discarded:
            return
        recycled = self._discarded
        self._discarded = []
        self._rng.shuffle(recycled)
        self._pool.extend(recycled)
