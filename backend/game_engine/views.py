"""The personalised snapshot each player receives.

The server sends a full `state` after every change rather than diffs, tailored
to the player it is going to (BUILD_PLAN.md, section 3). The tailoring is the
security boundary: before the reveal a player must never receive another
player's word or pages, so the rule is enforced by only ever *putting in* what
they may see, rather than by filtering a complete state afterwards.

Nothing here ever emits a token.
"""

from __future__ import annotations

from typing import Any

from game_engine.game import has_submitted, previous_page
from game_engine.models import Game, Page, Phase

__all__ = ["view_for"]


def _page(page: Page) -> dict[str, Any]:
    return {
        "kind": str(page.kind),
        "author": page.author_idx,
        "text": page.text,
        "strokes": page.strokes,
        "skipped": page.skipped,
    }


def _players(game: Game) -> list[dict[str, Any]]:
    """Names and status only. Tokens never leave the server."""
    playing = game.phase is Phase.ROUND
    return [
        {
            "idx": player.idx,
            "name": player.name,
            "connected": player.connected,
            "host": player.is_host,
            "submitted": has_submitted(game, player.idx) if playing else False,
        }
        for player in game.players
    ]


def view_for(game: Game, seat: int) -> dict[str, Any]:
    """Everything this seat is allowed to know, and nothing else."""
    view: dict[str, Any] = {
        "phase": str(game.phase),
        "code": game.code,
        "you": seat,
        "host": game.host_idx,
        "players": _players(game),
    }

    if game.phase is Phase.ROUND:
        view.update(_round_view(game, seat))
    elif game.phase is Phase.REVEAL:
        view["reveal"] = _reveal_view(game)

    return view


def _round_view(game: Game, seat: int) -> dict[str, Any]:
    """What a player sees mid-game: their own book's word, and one page.

    `previous` is the single page they are working from. The earlier pages of
    the book in their hands are deliberately absent -- a player must not be
    able to read the story so far, only the page handed to them.
    """
    assert game.bank is not None
    earlier = previous_page(game, seat)

    view: dict[str, Any] = {
        "round": game.round,
        "round_count": game.round_count,
        "submitted": has_submitted(game, seat),
        "previous": _page(earlier) if earlier else None,
    }

    if game.round == 0:
        # Only ever this player's own options and own word.
        view["options"] = list(game.bank.options_for(seat))
        view["word"] = game.books[seat].word

    return view


def _reveal_view(game: Game) -> dict[str, Any]:
    """Every book, in full. The secrecy rule ends when the reveal begins."""
    assert game.reveal is not None
    return {
        "book": game.reveal.book,
        "step": game.reveal.step,
        "books": [
            {
                "owner": book.owner_idx,
                "word": book.word,
                "pages": [_page(page) for page in book.pages],
            }
            for book in game.books
        ],
    }
