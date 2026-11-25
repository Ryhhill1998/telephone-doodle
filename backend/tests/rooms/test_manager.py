"""RoomManager: lobby actions, connections keyed by token, and cleanup.

`create_room` and `finish_reveal` are the only two places `RoomManager` talks
to Postgres (BUILD_PLAN.md, Step 4 -- snapshotting every change is Step 5), so
these tests run against the real database like the storage tests do.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import pytest

from game_engine import NotAllowed
from rooms import RoomManager, RoomNotFound
from storage import Database


@dataclass
class FakeWebSocket:
    """A socket double with just enough of the real interface to broadcast to."""

    sent: list[dict[str, Any]] = field(default_factory=list)
    closed: int | None = None

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)

    async def close(self, code: int = 1000) -> None:
        self.closed = code


async def test_create_room_seats_the_creator_as_host(db: Database) -> None:
    manager = RoomManager(db)

    room, player, token = await manager.create_room("Jo")

    assert player.is_host
    assert player.token == token
    assert manager.get_room(room.game.code) is room


async def test_join_room_adds_a_second_player_and_broadcasts(db: Database) -> None:
    manager = RoomManager(db)
    room, host, _ = await manager.create_room("Jo")
    host_ws = FakeWebSocket()
    await manager.connect(room, host, host_ws)
    host_ws.sent.clear()

    _, guest, _ = await manager.join_room(room.game.code, "Sam")

    assert guest.idx == 1
    assert not guest.is_host
    # The host hears about the new player without having to reconnect.
    assert host_ws.sent[-1]["players"][1]["name"] == "Sam"


async def test_connections_follow_the_token_through_a_seat_reindex(db: Database) -> None:
    """A kick reindexes every later seat; the socket must follow its player by
    token, not by the seat number that just changed under it -- `idx` is only
    stable once the game starts (game_engine.models.Player).
    """
    manager = RoomManager(db)
    room, host, _ = await manager.create_room("Jo")
    _, middle, _ = await manager.join_room(room.game.code, "Sam")
    _, last, _ = await manager.join_room(room.game.code, "Ali")
    last_ws = FakeWebSocket()
    await manager.connect(room, last, last_ws)
    assert last.idx == 2

    await manager.kick_player(room, host, seat=middle.idx)

    assert last.idx == 1
    assert room.connections[last.token] is last_ws


async def test_kick_player_closes_their_socket_and_invalidates_their_token(
    db: Database,
) -> None:
    manager = RoomManager(db)
    room, host, _ = await manager.create_room("Jo")
    _, guest, guest_token = await manager.join_room(room.game.code, "Sam")
    guest_ws = FakeWebSocket()
    await manager.connect(room, guest, guest_ws)

    await manager.kick_player(room, host, seat=guest.idx)

    assert guest_ws.closed == 4403
    assert room.game.player_by_token(guest_token) is None
    assert guest_token not in room.connections


async def test_host_can_shuffle_seats(db: Database) -> None:
    manager = RoomManager(db)
    room, host, _ = await manager.create_room("Jo")
    await manager.join_room(room.game.code, "Sam")

    await manager.shuffle_seats(room, host)  # does not raise

    assert len(room.game.players) == 2


async def test_only_the_host_can_shuffle_seats_or_kick(db: Database) -> None:
    manager = RoomManager(db)
    room, _host, _ = await manager.create_room("Jo")
    _, guest, _ = await manager.join_room(room.game.code, "Sam")

    with pytest.raises(NotAllowed):
        await manager.shuffle_seats(room, guest)
    with pytest.raises(NotAllowed):
        await manager.kick_player(room, guest, seat=0)


async def test_evict_stale_rooms_drops_rooms_inactive_too_long(db: Database) -> None:
    manager = RoomManager(db, inactivity_timeout=timedelta(seconds=-1))
    room, _host, _ = await manager.create_room("Jo")

    evicted = await manager.evict_stale_rooms()

    assert evicted == [room.game.code]
    with pytest.raises(RoomNotFound):
        manager.get_room(room.game.code)


async def test_evict_stale_rooms_closes_any_open_sockets(db: Database) -> None:
    manager = RoomManager(db, inactivity_timeout=timedelta(seconds=-1))
    room, host, _ = await manager.create_room("Jo")
    host_ws = FakeWebSocket()
    await manager.connect(room, host, host_ws)

    await manager.evict_stale_rooms()

    assert host_ws.closed == 1001


async def test_evict_stale_rooms_leaves_active_rooms_alone(db: Database) -> None:
    manager = RoomManager(db)
    room, _host, _ = await manager.create_room("Jo")

    evicted = await manager.evict_stale_rooms()

    assert evicted == []
    assert manager.get_room(room.game.code) is room
