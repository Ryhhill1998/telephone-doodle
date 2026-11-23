> Suggested reading (in docs/plan/): 03-architecture.md

### Step 5. Durable games (deploys, restarts and scale-to-zero do not end games)

Branch `feat/durable-games`.

- **Snapshot on every change:** after each state-changing event (join, start, pick word, submit, round advance, reveal pointer move) write `game_engine.to_dict(game)` to `games.snapshot` through the version-guarded `save_snapshot`. Only on events, never per stroke.
- **Load on demand:** when a WebSocket or join request arrives for a room code that is not in memory, `RoomManager.get_or_load(code)` loads it from the database (only `lobby` or `in_progress` games updated within the last 24 hours), under a per-code lock so concurrent reconnects load it once. Every player starts as disconnected until they reconnect with their token. There is **no restore-everything-at-startup**.
- **Version conflicts:** if `save_snapshot` reports a conflict (another instance wrote first, e.g. during a deploy overlap), drop the in-memory room and close its sockets with code `1012`; clients reconnect and the room is reloaded from the database.
- **Graceful shutdown:** Cloud Run sends SIGTERM and stops the instance about 10 seconds later. On SIGTERM, flush any pending snapshot writes, then close every WebSocket with close code `1012` (service restart). Configure uvicorn's graceful shutdown timeout to about 8 seconds.
- **Cleanup:** delete `lobby` and `in_progress` games not updated for 24 hours (finished games are kept). Run it at startup and then hourly while the instance is up.
- Document in the README that a deploy or a cold start causes only a few seconds of reconnecting, and that tokens in snapshots are removed when a game finishes.
- Tests: play a game halfway, throw away the `RoomManager`, create a new one, reconnect with the old tokens (the room loads on demand) and finish the game; the same during the reveal (pointer preserved); two managers writing the same game (the second gets a conflict and drops its room); stale rows are not loaded; shutdown closes sockets with 1012; snapshot size for a worst-case 10-player game is reported.

**Review checklist:** the restart and conflict tests pass; no per-stroke database writes.

---
