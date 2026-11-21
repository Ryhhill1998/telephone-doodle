"""Errors raised when a message is not valid for the current game state.

The API layer turns these into rejections. They are deliberately specific, so a
rejection says *why* rather than just "no" (BUILD_PLAN.md, section 3: "reject
messages not valid for the current phase or sender").
"""

__all__ = ["GameError", "InvalidSubmission", "NotAllowed", "WrongPhase"]


class GameError(Exception):
    """Base class for every rule violation."""


class WrongPhase(GameError):
    """The message is fine, but not in this phase (`start` during the reveal)."""


class NotAllowed(GameError):
    """The sender may not do this (a non-host moving the reveal pointer)."""


class InvalidSubmission(GameError):
    """The content is wrong for this round (a guess where a drawing is due)."""
