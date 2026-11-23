"""Request, response and WebSocket message shapes, and the stroke validation
`game_engine` deliberately leaves to this layer.

`game_engine.submit` stores whatever `strokes` dict it is given -- it has no
idea what a valid drawing looks like, because that is an API-shaped concern,
not a rule of the game (BUILD_PLAN.md, section 3's stroke limits). Everything
else here (names, guesses, player counts) is already checked by `game_engine`,
so it is not re-checked here: a limit written down twice is a limit that can
disagree with itself.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

__all__ = [
    "MAX_OPERATIONS",
    "MAX_POINTS",
    "MESSAGE_ADAPTER",
    "CreateRoomRequest",
    "CreateRoomResponse",
    "FinishRevealMessage",
    "IncomingMessage",
    "JoinRoomRequest",
    "JoinRoomResponse",
    "KickPlayerMessage",
    "PickWordMessage",
    "RevealNextMessage",
    "RevealPrevMessage",
    "ShuffleSeatsMessage",
    "ShuffleWordsMessage",
    "SkipPlayerMessage",
    "StartMessage",
    "Strokes",
    "SubmitPageMessage",
]

# -- the stroke payload (BUILD_PLAN.md, section 3) -------------------------

MAX_OPERATIONS = 500
MAX_POINTS = 20_000
MIN_BRUSH_SIZE = 1
MAX_BRUSH_SIZE = 60
_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class StrokeOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    t: Literal["brush", "fill"]
    c: str
    s: int | None = None
    p: list[tuple[float, float]]

    @field_validator("c")
    @classmethod
    def _colour_is_hex(cls, value: str) -> str:
        if not _COLOUR.fullmatch(value):
            raise ValueError("colour must be #RRGGBB")
        return value

    @field_validator("p")
    @classmethod
    def _points_are_normalised(cls, value: list[tuple[float, float]]) -> list[tuple[float, float]]:
        for x, y in value:
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise ValueError("coordinates must be within 0..1")
        return value

    @model_validator(mode="after")
    def _brush_has_a_size(self) -> StrokeOp:
        if self.t == "brush" and not (
            self.s is not None and MIN_BRUSH_SIZE <= self.s <= MAX_BRUSH_SIZE
        ):
            raise ValueError(f"a brush stroke needs size {MIN_BRUSH_SIZE}..{MAX_BRUSH_SIZE}")
        return self


class Strokes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v: Literal[1]
    w: int
    h: int
    ops: list[StrokeOp] = Field(max_length=MAX_OPERATIONS)

    @model_validator(mode="after")
    def _not_too_many_points(self) -> Strokes:
        if sum(len(op.p) for op in self.ops) > MAX_POINTS:
            raise ValueError(f"at most {MAX_POINTS} points per drawing")
        return self


# -- HTTP ---------------------------------------------------------------


class CreateRoomRequest(BaseModel):
    name: str


class CreateRoomResponse(BaseModel):
    code: str
    token: str
    player_id: int


class JoinRoomRequest(BaseModel):
    name: str


class JoinRoomResponse(BaseModel):
    token: str
    player_id: int


# -- WebSocket: client to server ------------------------------------------


class _Message(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartMessage(_Message):
    type: Literal["start"]


class ShuffleWordsMessage(_Message):
    type: Literal["shuffle_words"]


class PickWordMessage(_Message):
    type: Literal["pick_word"]
    text: str


class SubmitPageMessage(_Message):
    type: Literal["submit_page"]
    kind: Literal["text", "strokes"]
    text: str | None = None
    strokes: Strokes | None = None

    @model_validator(mode="after")
    def _payload_matches_kind(self) -> SubmitPageMessage:
        if self.kind == "text" and self.text is None:
            raise ValueError("a text page needs text")
        if self.kind == "strokes" and self.strokes is None:
            raise ValueError("a strokes page needs strokes")
        return self


class RevealNextMessage(_Message):
    type: Literal["reveal_next"]


class RevealPrevMessage(_Message):
    type: Literal["reveal_prev"]


class FinishRevealMessage(_Message):
    type: Literal["finish_reveal"]


class SkipPlayerMessage(_Message):
    type: Literal["skip_player"]
    player_id: int


class ShuffleSeatsMessage(_Message):
    type: Literal["shuffle_seats"]


class KickPlayerMessage(_Message):
    type: Literal["kick_player"]
    player_id: int


IncomingMessage = Annotated[
    StartMessage
    | ShuffleWordsMessage
    | PickWordMessage
    | SubmitPageMessage
    | RevealNextMessage
    | RevealPrevMessage
    | FinishRevealMessage
    | SkipPlayerMessage
    | ShuffleSeatsMessage
    | KickPlayerMessage,
    Field(discriminator="type"),
]

MESSAGE_ADAPTER: TypeAdapter[IncomingMessage] = TypeAdapter(IncomingMessage)
