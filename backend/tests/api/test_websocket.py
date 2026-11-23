"""The WebSocket API: a scripted game, reconnects, and rejections.

`WebSocketTestSession.send_json` only enqueues a message for the app to
process; it does not wait for a reply. `receive_json` is the synchronisation
point -- it blocks until the server has actually produced one -- so every
assertion here is reached through a `receive_json`, never by assuming a send
has already been handled.

Because every successful action broadcasts a fresh `state` to *every*
currently connected socket, the sockets are opened one at a time and each
socket's own backlog is drained before the next one opens (`_connect_all`);
after that, every send in the happy path is followed by exactly one
`receive_json` per open socket (`_drain`).
"""

from __future__ import annotations

from contextlib import ExitStack

import psycopg
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from main import app

STROKES = {"v": 1, "w": 100, "h": 100, "ops": []}


def _setup_three_players(client: TestClient) -> tuple[str, list[str]]:
    created = client.post("/api/rooms", json={"name": "Host"}).json()
    code = created["code"]
    tokens = [created["token"]]
    for name in ("P2", "P3"):
        tokens.append(client.post(f"/api/rooms/{code}/join", json={"name": name}).json()["token"])
    return code, tokens


def _connect_all(stack: ExitStack, client: TestClient, code: str, tokens: list[str]) -> list:
    """Open one socket per token, draining each connect's broadcast as it lands.

    Opening socket *n* broadcasts to every socket already open plus itself, so
    sockets already in `connected` each gain exactly one more backlog message;
    draining immediately, before the next socket opens, keeps every socket's
    queue at zero between sockets instead of growing unevenly.
    """
    connected: list = []
    for token in tokens:
        websocket = stack.enter_context(client.websocket_connect(f"/ws/{code}?token={token}"))
        for existing in connected:
            existing.receive_json()
        websocket.receive_json()
        connected.append(websocket)
    return connected


def _drain(sockets: list) -> list[dict]:
    """Read the one broadcast each socket just received, in socket order."""
    return [websocket.receive_json() for websocket in sockets]


def _play_round(sockets: list, states: list[dict], kind: str) -> list[dict]:
    for i, websocket in enumerate(sockets):
        message = (
            {"type": "submit_page", "kind": "strokes", "strokes": STROKES}
            if kind == "strokes"
            else {"type": "submit_page", "kind": "text", "text": f"guess-{i}"}
        )
        websocket.send_json(message)
        states = _drain(sockets)
    return states


def _play_to_reveal(sockets: list) -> list[dict]:
    sockets[0].send_json({"type": "start"})
    states = _drain(sockets)

    for i, websocket in enumerate(sockets):
        websocket.send_json({"type": "pick_word", "text": states[i]["options"][0]})
        states = _drain(sockets)

    states = _play_round(sockets, states, "strokes")  # round 0: draw the word
    states = _play_round(sockets, states, "text")  # round 1: guess
    states = _play_round(sockets, states, "strokes")  # round 2: draw the guess

    assert states[0]["phase"] == "reveal"
    return states


async def test_full_game_from_lobby_through_reveal_to_finish(
    conn: psycopg.AsyncConnection,
) -> None:
    with TestClient(app) as client:
        code, tokens = _setup_three_players(client)

        with ExitStack() as stack:
            sockets = _connect_all(stack, client, code, tokens)
            states = _play_to_reveal(sockets)
            assert (states[0]["reveal"]["book"], states[0]["reveal"]["step"]) == (0, 0)

            # Only the host may move the reveal pointer; the sender alone
            # hears about the rejection, and the pointer does not move.
            sockets[1].send_json({"type": "reveal_next"})
            error = sockets[1].receive_json()
            assert error["type"] == "error"

            last_book = len(sockets) - 1
            while (states[0]["reveal"]["book"], states[0]["reveal"]["step"]) != (last_book, 3):
                sockets[0].send_json({"type": "reveal_next"})
                states = _drain(sockets)

            sockets[0].send_json({"type": "finish_reveal"})
            states = _drain(sockets)

        assert states[0]["phase"] == "done"

    cursor = await conn.execute("SELECT status FROM games WHERE code = %s", (code,))
    row = await cursor.fetchone()
    assert row is not None
    assert row["status"] == "finished"


def test_host_can_skip_a_stalled_player() -> None:
    with TestClient(app) as client:
        code, tokens = _setup_three_players(client)

        with ExitStack() as stack:
            sockets = _connect_all(stack, client, code, tokens)

            sockets[0].send_json({"type": "start"})
            states = _drain(sockets)
            for i, websocket in enumerate(sockets):
                websocket.send_json({"type": "pick_word", "text": states[i]["options"][0]})
                states = _drain(sockets)

            # Seats 0 and 2 submit; seat 1 never does.
            sockets[0].send_json({"type": "submit_page", "kind": "strokes", "strokes": STROKES})
            states = _drain(sockets)
            sockets[2].send_json({"type": "submit_page", "kind": "strokes", "strokes": STROKES})
            states = _drain(sockets)
            assert states[0]["round"] == 0

            sockets[0].send_json({"type": "skip_player", "player_id": 1})
            states = _drain(sockets)

    assert states[0]["round"] == 1


def test_reconnect_mid_round_resumes_the_seat() -> None:
    with TestClient(app) as client:
        code, tokens = _setup_three_players(client)

        with ExitStack() as stack:
            sockets = _connect_all(stack, client, code, tokens)
            sockets[0].send_json({"type": "start"})
            _drain(sockets)

            sockets[1].close()
            states = _drain([sockets[0], sockets[2]])
            assert states[0]["players"][1]["connected"] is False

            rejoined = stack.enter_context(
                client.websocket_connect(f"/ws/{code}?token={tokens[1]}")
            )
            states = [rejoined.receive_json(), sockets[0].receive_json(), sockets[2].receive_json()]

    assert states[0]["you"] == 1
    assert states[0]["phase"] == "round"
    assert all(state["players"][1]["connected"] for state in states)


def test_reconnect_during_the_reveal_lands_on_the_current_page() -> None:
    with TestClient(app) as client:
        code, tokens = _setup_three_players(client)

        with ExitStack() as stack:
            sockets = _connect_all(stack, client, code, tokens)
            states = _play_to_reveal(sockets)

            sockets[0].send_json({"type": "reveal_next"})
            states = _drain(sockets)
            moved_to = states[0]["reveal"]

            sockets[1].close()
            _drain([sockets[0], sockets[2]])

            rejoined = stack.enter_context(
                client.websocket_connect(f"/ws/{code}?token={tokens[1]}")
            )
            reconnected_state = rejoined.receive_json()
            sockets[0].receive_json()
            sockets[2].receive_json()

    assert reconnected_state["phase"] == "reveal"
    assert reconnected_state["reveal"] == moved_to


def test_invalid_message_is_rejected() -> None:
    with TestClient(app) as client:
        code, tokens = _setup_three_players(client)

        with client.websocket_connect(f"/ws/{code}?token={tokens[0]}") as websocket:
            websocket.receive_json()  # its own connect() broadcast

            websocket.send_text("not json at all")
            error = websocket.receive_json()
            assert error["type"] == "error"

            websocket.send_json({"type": "not_a_real_message_type"})
            error = websocket.receive_json()
            assert error["type"] == "error"


def test_oversize_payload_is_rejected() -> None:
    with TestClient(app) as client:
        code, tokens = _setup_three_players(client)

        with client.websocket_connect(f"/ws/{code}?token={tokens[0]}") as websocket:
            websocket.receive_json()

            huge_points = [[0.1, 0.2]] * 20_000
            websocket.send_json(
                {
                    "type": "submit_page",
                    "kind": "strokes",
                    "strokes": {
                        "v": 1,
                        "w": 100,
                        "h": 100,
                        "ops": [{"t": "brush", "c": "#000000", "s": 1, "p": huge_points}],
                    },
                }
            )
            error = websocket.receive_json()
            assert error["type"] == "error"


def test_disallowed_origin_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://good.example")

    with TestClient(app) as client:
        code, tokens = _setup_three_players(client)

        with (
            pytest.raises(WebSocketDisconnect) as exc_info,
            client.websocket_connect(
                f"/ws/{code}?token={tokens[0]}",
                headers={"origin": "https://evil.example"},
            ),
        ):
            pass

    assert exc_info.value.code == 4403
