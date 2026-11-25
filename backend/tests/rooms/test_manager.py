"""RoomManager: lobby actions, connections keyed by token, and cleanup.

`create_room` and `finish_reveal` are the only two places `RoomManager` talks
to Postgres (snapshotting every change is Step 5), so these tests run against
the real database like the storage tests do.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import psycopg
import pytest

import game_engine
from game_engine import NotAllowed, PageKind, Phase, Player, page_kind
from rooms import Room, RoomGone, RoomManager, RoomNotFound
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


# -- durability (Step 5) ---------------------------------------------------


async def _play_round(manager: RoomManager, room: Room, players: list[Player]) -> None:
    """Every seat picks a word (round 0 only) and submits a page."""
    kind = page_kind(room.game.round)
    for player in players:
        if room.game.round == 0:
            assert room.game.bank is not None
            option = room.game.bank.options_for(player.idx)[0]
            await manager.pick_word(room, player, text=option)
        if kind is PageKind.TEXT:
            await manager.submit_page(room, player, text=f"guess-{player.idx}", strokes=None)
        else:
            strokes = {"v": 1, "w": 800, "h": 600, "ops": []}
            await manager.submit_page(room, player, text=None, strokes=strokes)


async def _finish_the_reveal(manager: RoomManager, room: Room, host: Player) -> None:
    while not game_engine.is_last_step(room.game):
        await manager.reveal_next(room, host)
    await manager.finish_reveal(room, host)


async def test_room_survives_discarding_the_manager_and_reloads_on_reconnect(
    db: Database,
) -> None:
    """A process restart mid-round costs a reconnect, not the game."""
    manager = RoomManager(db)
    room, host, host_token = await manager.create_room("Jo")
    code = room.game.code
    _, p1, p1_token = await manager.join_room(code, "Sam")
    _, p2, p2_token = await manager.join_room(code, "Ali")

    await manager.start_game(room, host)
    await _play_round(manager, room, [host, p1, p2])
    assert room.game.round == 1

    reloaded_manager = RoomManager(db)  # stands in for a brand-new process

    reloaded_room, reloaded_host = await reloaded_manager.authenticate(code, host_token)
    assert reloaded_room.game.round == 1
    assert all(not seated.connected for seated in reloaded_room.game.players)

    _, reloaded_p1 = await reloaded_manager.authenticate(code, p1_token)
    _, reloaded_p2 = await reloaded_manager.authenticate(code, p2_token)
    players = [reloaded_host, reloaded_p1, reloaded_p2]

    await _play_round(reloaded_manager, reloaded_room, players)
    await _play_round(reloaded_manager, reloaded_room, players)
    assert reloaded_room.game.phase is Phase.REVEAL

    await _finish_the_reveal(reloaded_manager, reloaded_room, reloaded_host)

    assert reloaded_room.game.phase is Phase.DONE
    finished = await db.get_finished_game(reloaded_room.game.id)
    assert finished is not None


async def test_room_survives_discarding_the_manager_during_the_reveal(db: Database) -> None:
    """The shared reveal pointer is part of the snapshot, so it picks up where
    it was left, not back at the first book.
    """
    manager = RoomManager(db)
    room, host, host_token = await manager.create_room("Jo")
    code = room.game.code
    _, p1, _ = await manager.join_room(code, "Sam")
    _, p2, _ = await manager.join_room(code, "Ali")

    await manager.start_game(room, host)
    for _ in range(3):
        await _play_round(manager, room, [host, p1, p2])
    assert room.game.phase is Phase.REVEAL

    await manager.reveal_next(room, host)
    await manager.reveal_next(room, host)
    moved_to = room.game.reveal

    reloaded_manager = RoomManager(db)
    reloaded_room, reloaded_host = await reloaded_manager.authenticate(code, host_token)

    assert reloaded_room.game.reveal == moved_to

    await _finish_the_reveal(reloaded_manager, reloaded_room, reloaded_host)
    assert reloaded_room.game.phase is Phase.DONE


async def test_get_or_load_refuses_a_stale_room(
    db: Database, conn: psycopg.AsyncConnection
) -> None:
    """A code nobody has touched in 24h is gone, not reloadable."""
    manager = RoomManager(db, inactivity_timeout=timedelta(seconds=-1))
    room, _host, _ = await manager.create_room("Jo")
    await manager.join_room(room.game.code, "Sam")  # a snapshot to (not) load
    code = room.game.code
    await manager.evict_stale_rooms()  # drop it from memory, as a restart would

    await conn.execute(
        "UPDATE games SET updated_at = now() - interval '25 hours' WHERE code = %s", (code,)
    )

    with pytest.raises(RoomNotFound):
        await manager.get_or_load(code)


async def test_losing_a_version_race_drops_the_room_and_closes_its_sockets(
    db: Database,
) -> None:
    """Two instances briefly holding the same room during a deploy: the one
    with the stale version loses, drops the room, and closes its sockets.
    """
    manager_a = RoomManager(db)
    room_a, host, host_token = await manager_a.create_room("Jo")
    code = room_a.game.code
    await manager_a.join_room(code, "Sam")  # version 0 -> 1: a snapshot exists

    manager_b = RoomManager(db)
    room_b, host_b = await manager_b.authenticate(code, host_token)
    guest_ws = FakeWebSocket()
    await manager_b.connect(room_b, host_b, guest_ws)

    await manager_a.shuffle_seats(room_a, host)  # version 1 -> 2, from elsewhere

    with pytest.raises(RoomGone):
        await manager_b.kick_player(room_b, host_b, seat=1)

    assert guest_ws.closed == 1012
    with pytest.raises(RoomNotFound):
        manager_b.get_room(code)


async def test_close_all_rooms_closes_every_socket_with_1012(db: Database) -> None:
    """The SIGTERM path (`main.py`'s lifespan shutdown)."""
    manager = RoomManager(db)
    room, host, _ = await manager.create_room("Jo")
    host_ws = FakeWebSocket()
    await manager.connect(room, host, host_ws)

    await manager.close_all_rooms()

    assert host_ws.closed == 1012
    with pytest.raises(RoomNotFound):
        manager.get_room(room.game.code)
