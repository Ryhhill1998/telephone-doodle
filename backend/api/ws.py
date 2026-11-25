"""The WebSocket API: one connection per player, one route per room.

Parsing, auth and the per-frame size cap live here; every action is a call
into `rooms.RoomManager` (BUILD_PLAN.md, Step 4). A rejected message (wrong
phase, wrong sender, bad payload) gets an `error` reply and the connection
stays open -- only a bad `Origin`, an unknown room or an invalid token close
the socket, because those mean there is no legitimate conversation to have.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from api.schemas import (
    MESSAGE_ADAPTER,
    FinishRevealMessage,
    IncomingMessage,
    KickPlayerMessage,
    PickWordMessage,
    RevealNextMessage,
    RevealPrevMessage,
    ShuffleSeatsMessage,
    ShuffleWordsMessage,
    SkipPlayerMessage,
    StartMessage,
    SubmitPageMessage,
)
from rooms import GameError, InvalidToken, Player, Room, RoomGone, RoomManager, RoomNotFound
from rooms.events import log_event
from settings import Settings, get_settings

router = APIRouter()

#: Section 3's 200 KB cap on a stroke payload, enforced on the whole frame: the
#: envelope around it is tiny, and rejecting early avoids parsing an
#: adversarial payload at all.
MAX_MESSAGE_BYTES = 200_000

CLOSE_FORBIDDEN_ORIGIN = 4403
CLOSE_ROOM_NOT_FOUND = 4404
CLOSE_INVALID_TOKEN = 4401


def _origin_allowed(settings: Settings, origin: str | None) -> bool:
    """Whether a WebSocket's `Origin` header may connect.

    CORS protects browsers reading HTTP responses and is handled by
    `CORSMiddleware`; WebSocket upgrades are not covered by CORS at all, so
    the server has to check this itself (BUILD_PLAN.md, section 3).
    """
    if settings.allowed_origins is None:
        return True
    return origin is not None and origin in settings.allowed_origins


@router.websocket("/ws/{code}")
async def room_socket(
    websocket: WebSocket,
    code: str,
    token: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if not _origin_allowed(settings, websocket.headers.get("origin")):
        await websocket.close(code=CLOSE_FORBIDDEN_ORIGIN)
        return

    rooms: RoomManager = websocket.app.state.rooms
    try:
        room, player = await rooms.authenticate(code.upper(), token)
    except RoomNotFound:
        await websocket.close(code=CLOSE_ROOM_NOT_FOUND)
        return
    except InvalidToken:
        await websocket.close(code=CLOSE_INVALID_TOKEN)
        return

    await websocket.accept()
    await rooms.connect(room, player, websocket)
    log_event("ws_connected", code=room.game.code, seat=player.idx)

    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
                await _send_error(websocket, "message too large")
                continue

            try:
                message = MESSAGE_ADAPTER.validate_json(raw)
            except ValidationError:
                await _send_error(websocket, "invalid message")
                continue

            try:
                await _dispatch(rooms, room, player, message)
            except GameError as exc:
                await _send_error(websocket, str(exc))
            except RoomGone:
                # Another instance won the version race; this instance has
                # already dropped the room and closed every socket in it,
                # this one included, so there is nothing left to receive.
                break
    except WebSocketDisconnect as exc:
        await rooms.disconnect(room, player)
        log_event("ws_closed", code=room.game.code, seat=player.idx, close_code=exc.code)


async def _send_error(websocket: WebSocket, message: str) -> None:
    await websocket.send_json({"type": "error", "message": message})


async def _dispatch(
    rooms: RoomManager, room: Room, player: Player, message: IncomingMessage
) -> None:
    match message:
        case StartMessage():
            await rooms.start_game(room, player)
        case ShuffleWordsMessage():
            await rooms.shuffle_words(room, player)
        case PickWordMessage(text=text):
            await rooms.pick_word(room, player, text=text)
        case SubmitPageMessage(text=text, strokes=strokes):
            await rooms.submit_page(
                room,
                player,
                text=text,
                strokes=strokes.model_dump() if strokes is not None else None,
            )
        case RevealNextMessage():
            await rooms.reveal_next(room, player)
        case RevealPrevMessage():
            await rooms.reveal_prev(room, player)
        case FinishRevealMessage():
            await rooms.finish_reveal(room, player)
        case SkipPlayerMessage(player_id=seat):
            await rooms.skip_player(room, player, seat=seat)
        case ShuffleSeatsMessage():
            await rooms.shuffle_seats(room, player)
        case KickPlayerMessage(player_id=seat):
            await rooms.kick_player(room, player, seat=seat)
