> Suggested reading (in docs/plan/): 02-locked-decisions.md (repo layout, dependency direction); 03-architecture.md

### Step 4. Rooms and realtime API

Branch `feat/api`.

- `rooms/`: `RoomManager` (in-memory) with unique 4-letter room codes (no ambiguous letters like `O/0`, `I/1`), join, token to player mapping, connection registry, broadcast of per-player `state` after every change, cleanup of rooms inactive for 6 h (background task). Creating a room calls `storage.create_game`.
- `api/`: the HTTP and WebSocket API and limits from section 3, validated with Pydantic models. CORS and the WebSocket `Origin` check both use `ALLOWED_ORIGINS` from env (permissive in dev). Keep routes thin: they call `rooms`.
- Reconnect: connecting with a valid token resumes the seat and sends the current `state`. Mark players `connected` / `disconnected` in the snapshot.
- Reveal sync exactly as described in section 3: only the host can move the pointer, every move is broadcast to all players.
- On `finish_reveal`: call `storage.finish_game`, put the phase at `DONE`.
- Lobby host actions: `shuffle_seats` and `kick_player` (host only, lobby only; a kicked player's socket is closed with 4403 and their token stops working).
- Validate the stroke payload's structure and size caps from section 3 on `submit_page`, not just its byte size.
- **Structured logging from day one:** JSON log lines to stdout (Cloud Run ships them to Cloud Logging for free), each with an event name and a few fields: `room_created`, `player_joined`, `game_started`, `game_finished`, `ws_connected`, `ws_closed` (with close code), `snapshot_conflict`, `rate_limited`. No player names or drawing content in logs. This makes the later observability work (see the v1 backlog) a configuration job, not a rewrite.
- Tests using FastAPI's test client WebSocket support: a scripted 3-player game from lobby through reveal and finish, reconnect mid-round, reconnect during the reveal lands on the current page, a non-host `reveal_next` is rejected, invalid message rejected, oversize payload rejected, skip-player, disallowed origin rejected.

**Review checklist:** a full game can be played with only a test script (no UI); `game_engine` untouched except for bug fixes (call these out); the dependency direction in section 2 holds, with `api` and `rooms` added to import-linter's `root_packages` and their layers un-parenthesised.

---
