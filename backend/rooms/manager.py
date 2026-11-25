"""Live rooms: the in-memory half of a game, and the only thing `api` talks to.

One `Room` per game in progress, keyed by its code. `rooms` owns the engine
state, the open WebSocket per player (keyed by token, because seat `idx`
reshuffles in the lobby -- BUILD_PLAN.md, Step 4), and broadcasting a fresh
personalised `state` to everyone after every change.

A snapshot is written after every state-changing event, guarded by the row's
version, and a room missing from memory is loaded back from that snapshot on
demand (`get_or_load`) -- a deploy, a restart or Cloud Run scaling to zero
costs a few seconds of reconnecting, not the game (BUILD_PLAN.md, Step 5).
Losing the version guard means another instance holds this room now: this
instance drops its copy and closes its sockets with 1012, and the client
reconnects into a fresh load.

No lock guards a room's mutations. Each engine call is synchronous and a
handler only awaits (to persist, broadcast or write to Postgres) once it is
done mutating, and asyncio only switches tasks at an `await` -- so two
messages for the same room can never interleave mid-mutation.
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
from rooms.errors import InvalidToken, RoomGone, RoomNotFound
from rooms.events import log_event
from rooms.translate import finished_game_rows
from storage import Database, GameStatus, RoomCodeTaken

__all__ = ["Room", "RoomManager"]

#: A fresh code is tried this many times before giving up. Four letters from a
#: 24-letter alphabet is 331,776 codes; collisions this many times running
#: would mean the active-game table is nearly full, which v0 has no limit for
#: yet (Step 6 adds a cap on rooms in memory).
CODE_ATTEMPTS = 10
TOKEN_BYTES = 16

INACTIVITY_TIMEOUT = timedelta(hours=6)
CLEANUP_INTERVAL = timedelta(minutes=30)

#: How long a game may go untouched before `get_or_load` refuses to load it
#: and the hourly sweep deletes its row outright -- the same cutoff, so a code
#: is never "not quite stale enough to load but not stale enough to delete"
#: (BUILD_PLAN.md, Step 5).
GAME_STALE_AFTER = timedelta(hours=24)
DB_CLEANUP_INTERVAL = timedelta(hours=1)

#: A service restart (SIGTERM) or a lost version race: either way the client's
#: own reconnect logic is what resumes the game, not this instance.
CLOSE_SERVICE_RESTART = 1012


@dataclass
class Room:
    """One game, live in memory.

    `version` mirrors the `games.version` column at the point this copy was
    last written or loaded; every snapshot write is conditioned on it matching
    (BUILD_PLAN.md, Step 5).
    """

    game: Game
    connections: dict[str, WebSocket] = field(default_factory=dict)
    last_active: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 0


class RoomManager:
    """Every room currently in memory, and the actions players can take."""

    def __init__(
        self,
        db: Database,
        *,
        inactivity_timeout: timedelta = INACTIVITY_TIMEOUT,
        cleanup_interval: timedelta = CLEANUP_INTERVAL,
        stale_after: timedelta = GAME_STALE_AFTER,
        db_cleanup_interval: timedelta = DB_CLEANUP_INTERVAL,
    ) -> None:
        self._db = db
        self._rooms: dict[str, Room] = {}
        self._inactivity_timeout = inactivity_timeout
        self._cleanup_interval = cleanup_interval
        self._stale_after = stale_after
        self._db_cleanup_interval = db_cleanup_interval
        self._cleanup_task: asyncio.Task[None] | None = None
        self._db_cleanup_task: asyncio.Task[None] | None = None
        #: One lock per in-flight load, so two requests racing to reconnect a
        #: room that just fell out of memory load it exactly once instead of
        #: each building its own copy (BUILD_PLAN.md, Step 5). Never cleaned
        #: up afterwards -- a lock is a few bytes, and the number of distinct
        #: codes a single instance ever sees in its lifetime is small.
        self._load_locks: dict[str, asyncio.Lock] = {}

    # -- lifecycle ----------------------------------------------------

    async def start(self) -> None:
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._db_cleanup_task = asyncio.create_task(self._db_cleanup_loop())

    async def stop(self) -> None:
        for task in (self._cleanup_task, self._db_cleanup_task):
            if task is None:
                continue
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(self._cleanup_interval.total_seconds())
            await self.evict_stale_rooms()

    async def _db_cleanup_loop(self) -> None:
        """Delete abandoned games from Postgres, at startup and then hourly.

        Separate from `_cleanup_loop`: that one frees this instance's memory
        of rooms nobody is connected to any more; this one is the thing that
        stops an abandoned game's row -- and its four-letter code -- living
        forever (BUILD_PLAN.md, Step 5).
        """
        while True:
            deleted = await self._db.delete_stale_games(self._stale_after)
            if deleted:
                log_event("stale_games_deleted", count=deleted)
            await asyncio.sleep(self._db_cleanup_interval.total_seconds())

    async def evict_stale_rooms(self) -> list[str]:
        """Drop rooms nobody has touched in `inactivity_timeout`.

        This only frees memory on this instance -- the snapshot already on
        disk is what a later `get_or_load` would rebuild from, so this is safe
        even for a game still within its 24h window.
        """
        now = datetime.now(UTC)
        stale = [
            code
            for code, room in self._rooms.items()
            if now - room.last_active > self._inactivity_timeout
        ]
        for code in stale:
            room = self._rooms.pop(code)
            await self._close_all(room, code=1001)
        return stale

    async def close_all_rooms(self) -> None:
        """Close every open socket with 1012 and forget every room.

        Called on SIGTERM (`main.py`'s lifespan shutdown): every snapshot
        write already happens synchronously as part of handling the event
        that caused it, so there is nothing left to flush here -- only the
        sockets, so clients start reconnecting immediately instead of waiting
        out a dead connection (BUILD_PLAN.md, Step 5).
        """
        for code in list(self._rooms):
            room = self._rooms.pop(code)
            await self._close_all(room, code=CLOSE_SERVICE_RESTART)

    async def _close_all(self, room: Room, *, code: int) -> None:
        for websocket in room.connections.values():
            with contextlib.suppress(Exception):
                await websocket.close(code=code)

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
        """The room for this code if it is already in memory. Never loads."""
        room = self._rooms.get(code)
        if room is None:
            raise RoomNotFound(code)
        return room

    async def get_or_load(self, code: str) -> Room:
        """The room for this code: from memory if it's live, from Postgres if
        not (BUILD_PLAN.md, Step 5).

        Every player starts disconnected -- there is no socket to any of them
        yet in this instance -- and reconnects set their own flag back to true
        the way a brand-new room does. Raises `RoomNotFound` if there is no
        row for this code, or no snapshot to rebuild one from (a lobby that
        never outlived its creating instance, which never wrote one).
        """
        room = self._rooms.get(code)
        if room is not None:
            return room

        lock = self._load_locks.setdefault(code, asyncio.Lock())
        async with lock:
            room = self._rooms.get(code)
            if room is not None:
                return room

            active = await self._db.load_game(code)
            if active is None or active.snapshot is None:
                raise RoomNotFound(code)

            game = game_engine.from_dict(active.snapshot)
            for seated in game.players:
                seated.connected = False

            room = Room(game=game, version=active.version)
            self._rooms[code] = room
            log_event("room_loaded", code=code)
            return room

    async def authenticate(self, code: str, token: str) -> tuple[Room, Player]:
        room = await self.get_or_load(code)
        player = room.game.player_by_token(token)
        if player is None:
            raise InvalidToken(token)
        return room, player

    async def join_room(self, code: str, name: str) -> tuple[Room, Player, str]:
        room = await self.get_or_load(code)
        token = secrets.token_urlsafe(TOKEN_BYTES)
        player = game_engine.add_player(room.game, name, token)
        log_event("player_joined", code=code, seat=player.idx)
        await self._persist_and_broadcast(room)
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
        await self._persist_and_broadcast(room)

    async def kick_player(self, room: Room, player: Player, *, seat: int) -> None:
        self._require_host(room.game, player, "remove a player")
        removed = game_engine.kick(room.game, seat)
        websocket = room.connections.pop(removed.token, None)
        if websocket is not None:
            with contextlib.suppress(Exception):
                await websocket.close(code=4403)
        await self._persist_and_broadcast(room)

    # -- rounds -----------------------------------------------------------

    async def start_game(self, room: Room, player: Player) -> None:
        self._require_host(room.game, player, "start the game")
        game_engine.start(room.game, random.Random())
        log_event("game_started", code=room.game.code)
        await self._persist_and_broadcast(room)

    async def shuffle_words(self, room: Room, player: Player) -> None:
        game_engine.shuffle_words(room.game, player.idx)
        await self._persist_and_broadcast(room)

    async def pick_word(self, room: Room, player: Player, *, text: str) -> None:
        game_engine.pick_word(room.game, player.idx, text)
        await self._persist_and_broadcast(room)

    async def submit_page(
        self, room: Room, player: Player, *, text: str | None, strokes: dict | None
    ) -> None:
        game_engine.submit(room.game, player.idx, text=text, strokes=strokes)
        self._advance_if_ready(room.game)
        await self._persist_and_broadcast(room)

    async def skip_player(self, room: Room, player: Player, *, seat: int) -> None:
        self._require_host(room.game, player, "skip a player")
        game_engine.skip_player(room.game, seat)
        self._advance_if_ready(room.game)
        await self._persist_and_broadcast(room)

    @staticmethod
    def _advance_if_ready(game: Game) -> None:
        if game.phase is Phase.ROUND and game_engine.all_submitted(game):
            game_engine.advance_round(game)

    # -- the reveal ---------------------------------------------------------

    async def reveal_next(self, room: Room, player: Player) -> None:
        game_engine.reveal_next(room.game, player.idx)
        await self._persist_and_broadcast(room)

    async def reveal_prev(self, room: Room, player: Player) -> None:
        game_engine.reveal_prev(room.game, player.idx)
        await self._persist_and_broadcast(room)

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

    async def _persist_and_broadcast(self, room: Room) -> None:
        """Write the snapshot, then broadcast -- every mutation but a connect,
        a disconnect or the final `finish_reveal` goes through here
        (BUILD_PLAN.md, Step 5).

        A lost version race means another instance has already written this
        game, so this instance's copy is wrong the moment it loses: the room
        is dropped, its sockets are closed with 1012, and `RoomGone` unwinds
        back to whichever `api` call started the mutation.
        """
        new_version = await self._db.save_snapshot(
            room.game.id,
            status=_status_for(room.game.phase),
            host_idx=room.game.host_idx,
            player_count=room.game.player_count,
            snapshot=game_engine.to_dict(room.game),
            expected_version=room.version,
        )
        if new_version is None:
            log_event("snapshot_conflict", code=room.game.code)
            self._rooms.pop(room.game.code, None)
            await self._close_all(room, code=CLOSE_SERVICE_RESTART)
            raise RoomGone(room.game.code)

        room.version = new_version
        await self._broadcast_and_touch(room)


def _status_for(phase: Phase) -> GameStatus:
    """`games.status` has no `reveal` or `done` of its own (storage/schema.py):
    both are still a game in progress until `finish_game` marks it finished.
    """
    return GameStatus.LOBBY if phase is Phase.LOBBY else GameStatus.IN_PROGRESS
