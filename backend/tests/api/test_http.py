"""`POST /api/rooms` and `POST /api/rooms/{code}/join`."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_create_room_returns_a_code_token_and_player_id() -> None:
    with TestClient(app) as client:
        response = client.post("/api/rooms", json={"name": "Jo"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["code"]) == 4
    assert body["player_id"] == 0
    assert body["token"]


def test_join_room_adds_a_second_player() -> None:
    with TestClient(app) as client:
        code = client.post("/api/rooms", json={"name": "Jo"}).json()["code"]

        response = client.post(f"/api/rooms/{code}/join", json={"name": "Sam"})

    assert response.status_code == 200
    assert response.json()["player_id"] == 1


def test_join_room_rejects_an_unknown_code() -> None:
    with TestClient(app) as client:
        response = client.post("/api/rooms/ZZZZ/join", json={"name": "Sam"})

    assert response.status_code == 404


def test_join_room_rejects_an_empty_name() -> None:
    with TestClient(app) as client:
        code = client.post("/api/rooms", json={"name": "Jo"}).json()["code"]

        response = client.post(f"/api/rooms/{code}/join", json={"name": "   "})

    assert response.status_code == 400


def test_create_room_rejects_an_empty_name() -> None:
    with TestClient(app) as client:
        response = client.post("/api/rooms", json={"name": ""})

    assert response.status_code == 400
