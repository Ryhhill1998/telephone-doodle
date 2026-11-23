## 3. Architecture reference

**Phases:** `LOBBY → ROUND(r) → REVEAL → DONE`

**Two origins.** The UI is at `https://<project>.web.app` (Firebase Hosting). The API and WebSockets are at `https://<service>-<hash>.europe-west2.run.app` (Cloud Run). The UI is built with `VITE_API_URL` pointing at the API (empty in local dev, where Vite's dev server proxies `/api` and `/ws`). The API allows the UI origin through CORS and checks the `Origin` header on WebSocket upgrades, both from the env var `ALLOWED_ORIGINS`.

*How CORS works (so nobody is surprised):* the **browser** makes the requests to the API, from JavaScript running on the UI's page. By default browsers refuse to let a page read responses from a different origin (scheme + host + port; nothing to do with IP addresses). The API opts in by answering with `Access-Control-Allow-Origin: <the UI's origin>`; for JSON `POST` requests the browser first sends an `OPTIONS` "preflight" asking whether that is allowed. CORS protects *users' browsers* from other websites, it does not protect the API: `curl` ignores it, which is why rate limits exist. **WebSockets are not covered by CORS**: the browser sends an `Origin` header and the server must check it itself, which is why the API does.

**Server-to-client:** the server sends a full personalised `state` snapshot after every change (not diffs). The snapshot is tailored per player, so it only contains what they may see. This keeps the client simple and makes cheating impossible.

**HTTP API**
- `POST /api/rooms` → `{code, token, player_id}` (body: `{name}`)
- `POST /api/rooms/{code}/join` → `{token, player_id}` (body: `{name}`)
- `GET /healthz` (does **not** touch the database, so a sleeping Neon never fails a deploy)

**WebSocket:** `/ws/{code}?token=...`

Client to server messages: `start`, `shuffle_words`, `pick_word {text}`, `submit_page {kind, text | strokes}`, `reveal_next`, `reveal_prev`, `finish_reveal`, `skip_player {player_id}`, `shuffle_seats` (host, lobby only), `kick_player {player_id}` (host, lobby only; the kicked socket is closed with code 4403)

Limits (enforce server-side): name <= 20 chars; text <= 100 chars; stroke payload <= 200 KB **and structurally valid** (version, at most 500 operations, at most 20,000 points in total, coordinates within 0..1, colours as `#RRGGBB`, brush size 1 to 60); max 10 players per room; reject messages not valid for the current phase or sender.

**Reveal sync (how everyone sees what the host does):**
- When the last round ends, the server enters the `REVEAL` phase and starts sending every player the full content of all books (the secrecy rule ends here), plus a shared pointer `reveal = {book, step}`. Step 0 of each book is the word card; steps 1..N are the pages.
- Only the host's `reveal_next` and `reveal_prev` messages are accepted. The server moves the pointer (forward from the last step of a book goes to the first step of the next book; `finish_reveal` is only valid at the last step of the last book) and then broadcasts a fresh `state` to **every** connected player.
- Each client renders whatever the pointer says. Clients never move the pointer themselves, so all screens always match, a player who refreshes or reconnects lands on the current page, and the pointer is saved in the in-progress snapshot like everything else.

**Why one API instance is enough, and what that implies.** Rooms live in the memory of the single Cloud Run instance, so the service is capped at `max-instances=1`. One instance comfortably holds hundreds of WebSocket connections (set concurrency to 250), and each room is only a few KB. Because Cloud Run scales to zero when nobody is connected (and phones that lock between rounds drop their sockets), **the database is the source of truth and rooms are loaded on demand** when a player reconnects. During a deploy the old and new instances briefly overlap, so every snapshot write is guarded by a version number (below) to prevent the two from overwriting each other.

**Postgres schema** (created idempotently on startup with `CREATE TABLE IF NOT EXISTS`)

A game row is created **when the room is created** (one room hosts exactly one game; "play again" creates a new room and a new game).

- `games(id TEXT PK, code TEXT, status TEXT CHECK(status IN ('lobby','in_progress','finished')), host_idx INT, player_count INT, version INT NOT NULL DEFAULT 0, created_at TIMESTAMPTZ, started_at TIMESTAMPTZ NULL, finished_at TIMESTAMPTZ NULL, updated_at TIMESTAMPTZ, snapshot JSONB NULL)`
  - `id` is a short random URL-safe id (8 chars), created with the room. It is internal; there is no public link to it in v0.
  - Partial unique index on `code` where `status != 'finished'`, so codes can be reused once a game is finished.
  - `snapshot` holds the full engine state (including player tokens) while the game is in progress and is set to NULL when it finishes.
  - `version` is incremented on every snapshot write. A write is `UPDATE ... SET version = version + 1 ... WHERE id = $1 AND version = $expected`. If it matches no row, another instance has written since, so this instance **drops its in-memory room and closes its sockets with 1012**; clients reconnect and the room is loaded fresh from the database.
- `players(game_id, idx INT, name TEXT)`: display names only, so that a finished game records who drew or wrote what.
- `books(game_id, idx INT, owner_idx INT, word TEXT)`: each book's starting word.
- `pages(game_id, book_idx INT, round INT, author_idx INT, kind TEXT CHECK(kind IN ('text','strokes')), text TEXT NULL, strokes JSONB NULL)`

`players`, `books` and `pages` are written when the game finishes (in one transaction).

**Connection notes for Neon.** Use Neon's *pooled* connection string (the hostname with `-pooler`), which runs PgBouncer in transaction mode: create connections with `prepare_threshold=None` so psycopg doesn't use server-side prepared statements. Use `sslmode=require`, a connect timeout of about 10 seconds, and retry the first connection a couple of times, because a compute that has auto-suspended needs about a second to wake.

---
