"""The stroke payload: the structure and size limits BUILD_PLAN.md (section 3)
asks `api` to enforce, since `game_engine.submit` stores whatever dict it is
given and checks none of this itself.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from api.schemas import MAX_OPERATIONS, MAX_POINTS, Strokes


def _strokes(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "v": 1,
        "w": 800,
        "h": 600,
        "ops": [{"t": "brush", "c": "#C8381F", "s": 12, "p": [[0.1, 0.2], [0.3, 0.4]]}],
    }
    base.update(overrides)
    return base


def test_a_well_formed_drawing_is_accepted() -> None:
    Strokes.model_validate(_strokes())


def test_a_fill_operation_needs_no_brush_size() -> None:
    Strokes.model_validate(_strokes(ops=[{"t": "fill", "c": "#000000", "p": [[0.5, 0.5]]}]))


@pytest.mark.parametrize("colour", ["red", "#ABC", "#GGGGGG", "#12345"])
def test_an_invalid_colour_is_rejected(colour: str) -> None:
    with pytest.raises(ValidationError):
        Strokes.model_validate(_strokes(ops=[{"t": "brush", "c": colour, "s": 10, "p": [[0, 0]]}]))


@pytest.mark.parametrize("size", [0, 61, -1])
def test_brush_size_outside_1_to_60_is_rejected(size: int) -> None:
    with pytest.raises(ValidationError):
        Strokes.model_validate(
            _strokes(ops=[{"t": "brush", "c": "#000000", "s": size, "p": [[0, 0]]}])
        )


def test_a_brush_stroke_needs_a_size() -> None:
    with pytest.raises(ValidationError):
        Strokes.model_validate(_strokes(ops=[{"t": "brush", "c": "#000000", "p": [[0, 0]]}]))


@pytest.mark.parametrize("point", [(-0.1, 0.5), (0.5, 1.1), (1.5, 0.5)])
def test_a_coordinate_outside_0_to_1_is_rejected(point: tuple[float, float]) -> None:
    with pytest.raises(ValidationError):
        Strokes.model_validate(
            _strokes(ops=[{"t": "brush", "c": "#000000", "s": 10, "p": [list(point)]}])
        )


def test_more_than_max_operations_is_rejected() -> None:
    op = {"t": "brush", "c": "#000000", "s": 10, "p": [[0.0, 0.0]]}
    with pytest.raises(ValidationError):
        Strokes.model_validate(_strokes(ops=[op] * (MAX_OPERATIONS + 1)))


def test_more_than_max_points_total_is_rejected() -> None:
    big_op = {"t": "brush", "c": "#000000", "s": 10, "p": [[0.0, 0.0]] * (MAX_POINTS + 1)}
    with pytest.raises(ValidationError):
        Strokes.model_validate(_strokes(ops=[big_op]))


def test_an_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Strokes.model_validate(_strokes(extra_field=True))
