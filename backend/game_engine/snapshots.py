"""Lossless JSON serialisation of a whole game.

Step 5 writes this to `games.snapshot` after every state-changing event and
loads it back when a room is needed again, so a deploy, a restart or Cloud Run
scaling to zero does not end a game (BUILD_PLAN.md, section 3).

Lossless means *everything*, tokens included: a reconnecting player proves who
they are with a token that must survive the round trip. The snapshot is cleared
when a game finishes, which is what removes the tokens.
"""

from __future__ import annotations

import random
from typing import Any

from game_engine.models import Book, Game, Page, PageKind, Phase, Player, Reveal
from game_engine.words import WordBank

__all__ = ["from_dict", "to_dict"]


def to_dict(game: Game) -> dict[str, Any]:
    """A JSON-safe snapshot of the entire game."""
    return {
        "id": game.id,
        "code": game.code,
        "phase": str(game.phase),
        "round": game.round,
        "players": [
            {
                "idx": player.idx,
                "name": player.name,
                "token": player.token,
                "connected": player.connected,
                "is_host": player.is_host,
            }
            for player in game.players
        ],
        "books": [
            {
                "owner_idx": book.owner_idx,
                "word": book.word,
                "pages": [
                    {
                        "kind": str(page.kind),
                        "author_idx": page.author_idx,
                        "text": page.text,
                        "strokes": page.strokes,
                        "skipped": page.skipped,
                    }
                    for page in book.pages
                ],
            }
            for book in game.books
        ],
        "reveal": None
        if game.reveal is None
        else {"book": game.reveal.book, "step": game.reveal.step},
        "bank": None if game.bank is None else game.bank.to_dict(),
    }


def from_dict(data: dict[str, Any], rng: random.Random | None = None) -> Game:
    """Rebuild a game from `to_dict`.

    The rng is only needed to carry on dealing words; a game past round 0 never
    touches it again. It defaults to a fresh generator because which word comes
    next must be unpredictable, not reproducible across a reload.
    """
    rng = rng or random.Random()

    return Game(
        id=data["id"],
        code=data["code"],
        phase=Phase(data["phase"]),
        round=data["round"],
        players=[
            Player(
                idx=raw["idx"],
                name=raw["name"],
                token=raw["token"],
                connected=raw["connected"],
                is_host=raw["is_host"],
            )
            for raw in data["players"]
        ],
        books=[
            Book(
                owner_idx=raw["owner_idx"],
                word=raw["word"],
                pages=[
                    Page(
                        kind=PageKind(page["kind"]),
                        author_idx=page["author_idx"],
                        text=page["text"],
                        strokes=page["strokes"],
                        skipped=page["skipped"],
                    )
                    for page in raw["pages"]
                ],
            )
            for raw in data["books"]
        ],
        reveal=None if data["reveal"] is None else Reveal(**data["reveal"]),
        bank=None if data["bank"] is None else WordBank.from_dict(data["bank"], rng),
    )
