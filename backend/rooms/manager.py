"""Live rooms: the in-memory half of a game, and the only thing `api` talks to.

One `Room` per game in progress, keyed by its code. `rooms` owns the engine
state, the open WebSocket per player (keyed by token, because seat `idx`
reshuffles in the lobby -- BUILD_PLAN.md, Step 4), and broadcasting a fresh
personalised `state` to everyone after every change.

Nothing here persists mid-game: a snapshot is written once at creation
(`storage.create_game`) and once at the end (`storage.finish_game`). Writing
one on every change and reloading a room that fell out of memory is Step 5
("durable games"); until then a process restart ends any game in flight, which
the plan accepts for this step.

No lock guards a room's mutations. Each engine call is synchronous and a
handler only awaits (to broadcast or to write to Postgres) once it is done
mutating, and asyncio only switches tasks at an `await` -- so two messages for
the same room can never interleave mid-mutation.
"""

from __future__ import annotations

import asyncio
import contextlib
import random
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from starlette.websockets import WebSocket

import game_engine
from game_engine import Game, NotAllowed, Phase, Player, view_for
from rooms.codes import generate_code
from rooms.errors import InvalidToken, RoomNotFound
from rooms.events import log_event
from rooms.translate import finished_game_rows
from storage import Database, RoomCodeTaken

__all__ = ["Room", "RoomManager"]

#: A fresh code is tried this many times before giving up. Four letters from a
#: 24-letter alphabet is 331,776 codes; collisions this many times running
#: would mean the active-game table is nearly full, which v0 has no limit for
#: yet (Step 6 adds a cap on rooms in memory).
CODE_ATTEMPTS = 10
TOKEN_BYTES = 16

INACTIVITY_TIMEOUT = timedelta(hours=6)
CLEANUP_INTERVAL = timedelta(minutes=30)


@dataclass
class Room:
    """One game, live in memory."""

    game: Game
    connections: dict[str, WebSocket] = field(default_factory=dict)
    last_active: datetime = field(default_factory=lambda: datetime.now(UTC))


class RoomManager:
    """Every room currently in memory, and the actions players can take."""

    def __init__(
        self,
        db: Database,
        *,
        inactivity_timeout: timedelta = INACTIVITY_TIMEOUT,
        cleanup_interval: timedelta = CLEANUP_INTERVAL,
    ) -> None:
        self._db = db
        self._rooms: dict[str, Room] = {}
        self._inactivity_timeout = inactivity_timeout
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: asyncio.Task[None] | None = None

    # -- lifecycle ----------------------------------------------------

    async def start(self) -> None:
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        if self._cleanup_task is None:
            return
        self._cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._cleanup_task

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(self._cleanup_interval.total_seconds())
            await self.evict_stale_rooms()

    async def evict_stale_rooms(self) -> list[str]:
        """Drop rooms nobody has touched in `inactivity_timeout`.

        In-memory only: there is no snapshot to fall back to before Step 5, so
        this is for abandoned lobbies, not games anyone can resume. Any socket
        still open (there should not be one, after six hours) is closed first.
        """
        now = datetime.now(UTC)
        stale = [
            code
            for code, room in self._rooms.items()
            if now - room.last_active > self._inactivity_timeout
        ]
        for code in stale:
            room = self._rooms.pop(code)
            for websocket in room.connections.values():
                with contextlib.suppress(Exception):
                    await websocket.close(code=1001)
        return stale

    # -- lobby ----------------------------------------------------------

    async def create_room(self, name: str) -> tuple[Room, Player, str]:
        game_id: str | None = None
        code = ""
        for _ in range(CODE_ATTEMPTS):
            code = generate_code()
            try:
                game_id = await self._db.create_game(code)
            except RoomCodeTaken:
                continue
            break
        if game_id is None:
            raise RuntimeError("could not find a free room code")

        game = game_engine.new_game(game_id, code)
        token = secrets.token_urlsafe(TOKEN_BYTES)
        player = game_engine.add_player(game, name, token)
        room = Room(game=game)
        self._rooms[code] = room

        log_event("room_created", code=code)
        log_event("player_joined", code=code, seat=player.idx)
        return room, player, token

    def get_room(self, code: str) -> Room:
        room = self._rooms.get(code)
        if room is None:
            raise RoomNotFound(code)
        return room

    def authenticate(self, code: str, token: str) -> tuple[Room, Player]:
        room = self.get_room(code)
        player = room.game.player_by_token(token)
        if player is None:
            raise InvalidToken(token)
        return room, player

    async def join_room(self, code: str, name: str) -> tuple[Room, Player, str]:
        room = self.get_room(code)
        token = secrets.token_urlsafe(TOKEN_BYTES)
        player = game_engine.add_player(room.game, name, token)
        log_event("player_joined", code=code, seat=player.idx)
        await self._broadcast_and_touch(room)
        return room, player, token

    async def connect(self, room: Room, player: Player, websocket: WebSocket) -> None:
        room.connections[player.token] = websocket
        player.connected = True
        await self._broadcast_and_touch(room)

    async def disconnect(self, room: Room, player: Player) -> None:
        if room.connections.pop(player.token, None) is None:
            return
        if room.game.player_by_token(player.token) is None:
            return  # already removed (kicked); nothing left to mark
        player.connected = False
        await self._broadcast_and_touch(room)

    # -- lobby host actions ----------------------------------------------

    async def shuffle_seats(self, room: Room, player: Player) -> None:
        self._require_host(room.game, player, "shuffle the seats")
        game_engine.shuffle_seats(room.game, random.Random())
        await self._broadcast_and_touch(room)

    async def kick_player(self, room: Room, player: Player, *, seat: int) -> None:
        self._require_host(room.game, player, "remove a player")
        removed = game_engine.kick(room.game, seat)
        websocket = room.connections.pop(removed.token, None)
        if websocket is not None:
            with contextlib.suppress(Exception):
                await websocket.close(code=4403)
        await self._broadcast_and_touch(room)

    # -- rounds -----------------------------------------------------------

    async def start_game(self, room: Room, player: Player) -> None:
        self._require_host(room.game, player, "start the game")
        game_engine.start(room.game, random.Random())
        log_event("game_started", code=room.game.code)
        await self._broadcast_and_touch(room)

    async def shuffle_words(self, room: Room, player: Player) -> None:
        game_engine.shuffle_words(room.game, player.idx)
        await self._broadcast_and_touch(room)

    async def pick_word(self, room: Room, player: Player, *, text: str) -> None:
        game_engine.pick_word(room.game, player.idx, text)
        await self._broadcast_and_touch(room)

    async def submit_page(
        self, room: Room, player: Player, *, text: str | None, strokes: dict | None
    ) -> None:
        game_engine.submit(room.game, player.idx, text=text, strokes=strokes)
        self._advance_if_ready(room.game)
        await self._broadcast_and_touch(room)

    async def skip_player(self, room: Room, player: Player, *, seat: int) -> None:
        self._require_host(room.game, player, "skip a player")
        game_engine.skip_player(room.game, seat)
        self._advance_if_ready(room.game)
        await self._broadcast_and_touch(room)

    @staticmethod
    def _advance_if_ready(game: Game) -> None:
        if game.phase is Phase.ROUND and game_engine.all_submitted(game):
            game_engine.advance_round(game)

    # -- the reveal ---------------------------------------------------------

    async def reveal_next(self, room: Room, player: Player) -> None:
        game_engine.reveal_next(room.game, player.idx)
        await self._broadcast_and_touch(room)

    async def reveal_prev(self, room: Room, player: Player) -> None:
        game_engine.reveal_prev(room.game, player.idx)
        await self._broadcast_and_touch(room)

    async def finish_reveal(self, room: Room, player: Player) -> None:
        game_engine.finish_reveal(room.game, player.idx)
        players, books, pages = finished_game_rows(room.game)
        await self._db.finish_game(room.game.id, players=players, books=books, pages=pages)
        log_event("game_finished", code=room.game.code)
        await self._broadcast_and_touch(room)

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _require_host(game: Game, player: Player, action: str) -> None:
        if player.idx != game.host_idx:
            raise NotAllowed(f"only the host can {action}")

    async def broadcast(self, room: Room) -> None:
        for seated in room.game.players:
            websocket = room.connections.get(seated.token)
            if websocket is None:
                continue
            # A failed send means a dead socket; its own receive loop will see
            # the disconnect and clean up, so this is not this method's job.
            with contextlib.suppress(Exception):
                await websocket.send_json({"type": "state", **view_for(room.game, seated.idx)})

    async def _broadcast_and_touch(self, room: Room) -> None:
        room.last_active = datetime.now(UTC)
        await self.broadcast(room)
