"""HTTP routes: create and join a room.

Thin on purpose: every rule lives in `game_engine`, every room lives in
`rooms`. This module only translates between HTTP and
`RoomManager`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.schemas import (
    CreateRoomRequest,
    CreateRoomResponse,
    JoinRoomRequest,
    JoinRoomResponse,
)
from rooms import NotAllowed, RoomGone, RoomManager, RoomNotFound, WrongPhase

router = APIRouter()


def _rooms(request: Request) -> RoomManager:
    return request.app.state.rooms


@router.post("/api/rooms", response_model=CreateRoomResponse)
async def create_room(body: CreateRoomRequest, request: Request) -> CreateRoomResponse:
    try:
        room, player, token = await _rooms(request).create_room(body.name)
    except NotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateRoomResponse(code=room.game.code, token=token, player_id=player.idx)


@router.post("/api/rooms/{code}/join", response_model=JoinRoomResponse)
async def join_room(code: str, body: JoinRoomRequest, request: Request) -> JoinRoomResponse:
    try:
        _, player, token = await _rooms(request).join_room(code.upper(), body.name)
    except (RoomNotFound, RoomGone) as exc:
        raise HTTPException(status_code=404, detail="no such room") from exc
    except WrongPhase as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JoinRoomResponse(token=token, player_id=player.idx)
