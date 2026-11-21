# BUILD_PLAN.md: Telephone Doodle (v0), revision 5

A web app for playing "telephone pictionary" with family. Each player starts a "book" by picking a word and drawing it. Books are then passed around and players alternate between writing a guess for the previous drawing and drawing the previous guess. At the end, every book is revealed page by page.

> **Instructions for Claude Code:** read this whole file before doing anything. Work through the steps **one at a time, in order**. Follow the Working Agreement below exactly. Do not skip ahead.

---

## 0. Working agreement (applies to every step)

1. **One step = one branch.** A step may be **more than one PR** where that gives a cleaner split (see rule 3). Branch names are `<type>/<short-name>` with no step numbers (types: `feat`, `chore`, `infra`, `ci`, `docs`, `fix`), for example `feat/game-engine`, `chore/scaffold`, `infra/terraform`. Always branch from an up-to-date `main`. Open the PR with `gh pr create`; the description contains: what changed, how to review it, how to run it, and anything deferred.
   **Commit in small, logically ordered steps.** A PR is read commit by commit, so commit at each natural checkpoint as the work happens rather than squashing a step into one large commit. Plan the commit sequence before starting (for example: models, then rotation, then dealing, then serialisation, then tests) and say what it is in the PR description.
2. **Stop after each PR.** Summarise the PR in a few lines and wait for me to say "merged" or "go" before starting the next step. Never merge PRs yourself and never start the next step on an unmerged branch.
3. **Split PRs by logical unit, not by line count.** There is no fixed line budget. Divide a step where the *meaning* divides: data separately from the logic that consumes it (the word bank is its own PR, separate from the game engine), a standalone component separately from the screens that use it, a pure module separately from its wiring. Propose the split up front, say which PR each piece lands in, and keep every PR independently reviewable and green.
4. **Tests are part of the step.** Each step lists acceptance checks. Run them and report the results honestly, including failures.
5. **Never commit secrets** (tokens, keys, connection strings, `.tfvars` with real values, `.env`). Add them to `.gitignore` before they exist. Never print secret values in chat.
6. **Ask before anything that costs money or is hard to reverse.** For Terraform, always run `terraform plan`, show me the summary, and wait for explicit approval before `terraform apply`. Don't create cloud resources outside Terraform, except the three manual items in Step 15 (the Terraform state bucket, the Neon project, and the database secret's value).
7. **Don't enter passwords or tokens on my behalf.** If a login or credential is needed (`gh auth login`, `gcloud auth login`, the Neon connection string), tell me the exact command or page and wait for me to do it.
8. **Don't run `gcloud` or any cloud CLI until Step 14 (Terraform)**, and then only as that step says.
9. **Always use the latest stable versions** of languages, runtimes, libraries, GitHub Actions and base images (see section 2). Never pin versions from memory: let the package manager resolve the latest, look up the current stable release of anything you install or reference by hand, and tell me the versions you ended up with in each PR. If a dependency does not yet support the newest language version, use the newest version it does support and tell me why.
10. **Prefer boring and simple.** No extra frameworks, queues, caches, ORMs or auth systems. If something in this plan seems wrong or over-complicated, say so rather than silently deviating.
11. **One command per check.** Every lint, test, build and check is a `make` target (see Step 1), and CI calls those same targets. Never duplicate a command's flags between the Makefile and a workflow file.
12. **Tests ship with the code they cover**, on both sides: backend with `pytest`, frontend with `vitest` and Testing Library, and a Playwright end-to-end suite (Step 12). A frontend PR without tests is incomplete.
13. **Log every deviation in this file.** If a step is built differently from how this plan describes it, or a sub-step is deferred, reordered or dropped, append an entry to [section 9, Build log](#9-build-log-decisions-and-deviations) in the same PR as the change: what the plan said, what was actually done, and why. Record the decisions this plan asks me to make there too. Mentioning a deviation only in chat or in a PR description is not enough — this file has to stay true.

---

## 1. Product spec (v0)

**Players:** 3 to 10, all online at the same time on phones, tablets or laptops. Phone and tablet first.

**Flow**

1. One player creates a room and gets a 4-letter code. Others join with the code and a display name. The creator is the host.
2. Before starting, the lobby shows the players in **seat order** (join order by default), numbered 1 to N. The host can **shuffle the order** with a button (as often as they like) and can **remove a player** (for example a stranger who joined by mistake, or someone who has to leave). Removed players are disconnected and see a "You were removed" message. The host starts the game (min 3 players; no joining after start). Starting freezes the seat order.
3. With `N` players there are `N` books and `N` rounds (`r = 0 .. N-1`). The seats form a **circle**: seat 1 follows seat N. Each round every book moves on to the next seat in the circle, so player in seat `p` works on book `(p - r) mod N` (their own book in round 0; the book of the seat before them in round 1; and so on). The direction and order never change during a game, so the passing is always predictable from the lobby list.
   - **Round 0 (pick and draw):** the player gets 3 random words from the word bank and picks one, **or** types their own (they can shuffle to get 3 new words). **Dealt words never repeat across players:** all players' options are drawn from one shuffled bank without replacement, and a shuffle draws from the words not yet dealt or picked. Typed words are deliberately **not** compared with other players' words, because any such check would reveal what someone else picked; only dealt words are guaranteed unique. They then **draw that word** on the next screen. The chosen word is stored privately on the book and is only shown at the reveal. The drawing is page 1 of their own book.
   - **Odd rounds (guess):** the player sees only the previous page (a drawing) and writes what they think it is.
   - **Even rounds >= 2 (draw):** the player sees only the previous page (a guess) and draws it.
   - With an odd number of players the last page of every book is a drawing that nobody guesses. That is fine for v0.
4. A round ends when **every player has submitted** ("ready-based"). There is no timer in v0. The UI shows who has finished.
5. After the last round, the **reveal** begins. For each book, the host steps through it: first a **word card** (who chose the word and what it was), then each page in order, with its author's name. Drawings are rendered statically from stroke data (replay animation is v1). After the last page of a book the host taps "Next book"; after the last book they finish the game.
6. **Everyone sees the same reveal screen at the same time:** the host's taps move a shared pointer on the server and every player's screen follows (see "Reveal sync" in section 3). Other players do not get Back or Next buttons.
7. When the host finishes, the game is marked finished and everyone sees a "That's a wrap" screen with a "Play again" button. There is **no shareable link or archive page** in v0.

**What we store:** only display names and the game's content (each book's starting word, the pages, who made each). There are **no accounts, passwords, emails or per-player stats**. Player tokens exist only while a game is in progress and are removed when it finishes. Finished games are kept quietly in the database so that v1 features (a highlights reel, voting on funniest books, scoring) have data to work with, but v0 has no screen that reads them back.

**Out of scope for v0 (do not build):** scoring, fuzzy matching, timers, votes or reactions, highlights, awards, accounts or auth, async play, stroke replay animation, themed word packs, permalinks or an archive page, browsing past games, running more than one API instance.

**Robustness requirements (in scope):**
- Players get a random token on join, stored in `localStorage`. Refreshing the page, locking the phone or closing the tab must **rejoin the same seat**: the home page shows a "Rejoin room KQFM" button while a saved seat exists, and the app reconnects automatically when the tab becomes visible or the network returns.
- **Drafts survive interruptions.** A drawing in progress (and a half-typed guess) is saved to `localStorage` after every stroke, keyed by room code and round, and restored when the same player returns to the same round on the same device (after a refresh, a locked phone, an accidental exit, or a server deploy that drops the socket). It is cleared when the page is submitted. Drafts are not synced between devices.
- If a player is disconnected during a round, the game waits. The host gets a "Skip" button which submits a blank page for that player.
- A player must never receive other players' pages or words before the reveal. The server only sends each player what they're allowed to see.
- **Games survive server restarts, deploys and scale-to-zero** (see Step 5): in-progress games are saved to Postgres on every change and loaded back on demand, and clients reconnect automatically.
- Games abandoned for 24 hours are deleted from the database; empty rooms are dropped from memory after about 6 hours of inactivity.
- **Abuse protection** (see Step 6): per-IP rate limits and connection caps, so a public URL can't be used to run up costs.

---

## 2. Locked decisions

| Area | Decision |
|---|---|
| Languages and versions | **Latest stable of everything.** At the time of writing Python 3.15 is the latest stable release (released 9 Oct 2026); verify at python.org. Node: the latest LTS. Latest stable Vite, React, TypeScript, FastAPI, Terraform and GitHub Actions majors. Fall back to Python 3.14 only if a key dependency has no 3.15 support, and tell me. |
| Backend | Python, FastAPI, WebSockets, `uv` for deps and the Python version (`.python-version`), `ruff`, `pytest` |
| Live state | In memory (dict of rooms), snapshotted to Postgres on every change, loaded on demand |
| Database | **Neon Postgres** (free plan), `psycopg` 3 with an async pool, plain SQL, schema created on startup. Neon project in AWS `eu-west-2` (London). |
| Frontend | Vite + React + TypeScript (strict), plain CSS. **Static files hosted on Firebase Hosting**, deployed separately from the API. |
| Tests | Backend: `pytest` (+ Postgres). Frontend: `vitest` + React Testing Library (jsdom) with a fake WebSocket. End-to-end: Playwright with three simulated players (Step 12). |
| Drawings | Operation-list JSON (brush strokes and flood fills, normalised coordinates, see Step 9), canvas with Pointer Events |
| API hosting | **Google Cloud Run**, region `europe-west2` (London), `max-instances=1`, `min-instances=0`, HTTPS from the built-in `*.run.app` URL |
| Image registry | **Artifact Registry** (GCP) with a cleanup policy that keeps only the last few images |
| CI/CD | GitHub Actions. CI runs only the jobs for the parts of the repo a PR changed (backend, frontend, infrastructure; e2e when backend or frontend change), always through `make` targets. Two deploy workflows with path filters: `backend/**` deploys the API, `frontend/**` deploys the UI. Authentication to GCP via **Workload Identity Federation** (no stored keys). |
| IaC | Terraform (remote state in a GCS bucket). Neon project is created by hand (see Step 15). |
| Cost guard | Budget alerts at $1 and $5 per month, `max-instances=1`, rate limits |
| Repo | New GitHub repo in **my personal account**, created with `gh` |

### Repo layout

Three top-level directories plus the usual root files. The backend has **no `src/` folder**: the packages sit directly inside `backend/`. The backend does not serve the UI.

```
backend/
  pyproject.toml, uv.lock, .python-version
  Dockerfile         API image only
  main.py            FastAPI app, lifespan (graceful shutdown, cleanup), CORS
  settings.py        env-based config
  api/               thin FastAPI layer: HTTP routes, WebSocket handler, Pydantic schemas, rate limiting
  rooms/             live in-memory rooms, connections, broadcast, snapshot and load-on-demand, cleanup
  storage/           Postgres access (schema, snapshots, finishing a game)
  game_engine/       PURE game rules: dataclasses and functions, no I/O, no FastAPI
    words.json       word bank
  tests/             mirrors the packages above
frontend/
  src/
    pages/           Home, Lobby, Room (phase router)
    screens/         Word, Draw, Waiting, Guess, Reveal, Finished
    components/      DrawingCanvas, StrokeView, PlayerList, Button, ...
    game/            socket hook, state types, reconnect logic
    lib/             strokes.ts and other pure helpers
  design/            approved UI prototype exports (see Step 7)
  e2e/               Playwright end-to-end tests (three simulated players, Step 12)
  firebase.json      hosting config (SPA rewrite, cache headers)
infrastructure/
  versions.tf, variables.tf, outputs.tf
  apis.tf            enable the GCP APIs we need
  registry.tf        Artifact Registry repository and cleanup policy
  iam.tf             runtime service account, deploy service account, Workload Identity Federation for GitHub
  secrets.tf         Secret Manager secret for the Neon connection string (value added by hand)
  cloud_run.tf       the API service
  hosting.tf         Firebase project and Hosting site
  budget.tf          budget and alerts
docker-compose.dev.yml   local Postgres for development and tests
.github/workflows/   ci.yml, deploy-api.yml, deploy-frontend.yml
Makefile             dev, test, lint targets
BUILD_PLAN.md, README.md
```

Run the backend from `backend/` with `uv run uvicorn main:app`. Imports are plain top-level package names (`from game_engine import ...`, `from storage import ...`).

**Dependency direction (enforce it):** `api` calls `rooms`; `rooms` calls `game_engine` and `storage`; `game_engine` imports nothing from the other packages. `game_engine` must stay free of I/O so it is trivially unit-testable.

---

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

## 4. UI design brief (the visual source of truth until `frontend/design/` exists)

An interactive prototype of these screens has been built for my review: **https://claude.ai/artifact/M7Wh9dZHav7oH6aMPWqgHY** (private to me; it may not open for you). **Do not start any frontend step until I have approved it and given you the exported files** (see Step 7); if you cannot open the link, ask me for the export. Implement the frontend to match it once approved. Tokens:

- **Colours:** paper `#FAF6EE`, ink `#1E2330`, card `#FFFFFF`, line `#E4DCCB`, input border `#8C8676`, muted text `#5E6472`, primary action red `#C8381F` (white text), highlight yellow `#FFD95A`, soft yellow `#FFF1B8`, success green `#1F7A4D`, focus ring blue `#2B59C3`. Avatar fills: `#FFD95A #BFD7FF #FFC9BC #CDEBC8 #E3D4FF`. Brush palette (14 presets plus eraser and a custom-colour swatch): ink `#1E2330`, grey `#8C8676`, brown `#7A4B2A`, red `#C8381F`, pink `#F26B9B`, orange `#F08A24`, yellow `#FFD95A`, lime `#9BD13B`, green `#2E9B5B`, teal `#1FA8A0`, sky blue `#4FB3F0`, blue `#2B59C3`, purple `#7A4FC9`, skin `#F2C9A0`, eraser (white). The custom swatch (a rainbow ring) opens a colour picker.
- **Type:** Space Grotesk 500/700 for headings and the room code, Inter 400/500/600 for body.
- **Shape:** buttons radius 14, cards 20, inputs 12, pills 999. All tap targets at least 44px. Visible `:focus-visible` outline. Respect `prefers-reduced-motion`.
- **Layout:** phone-first at 390px wide; on wider screens centre a column (max about 480px). The reveal screen should also scale up nicely on a tablet or TV.
- **Screens (8):**
  1. Home (name, create room, join with code).
  2. Lobby (big room code with copy, numbered player list in seat order, host-only Shuffle order and remove-player crosses, host Start).
  3. Pick a word (3 options, shuffle, type your own; the button says "Draw it").
  4. Draw (round 1: "Your word, now draw it", with the word on a note; in later rounds the note shows the previous guess; 4:3 canvas, a two-row palette of 14 colours plus eraser and a custom-colour swatch, a **brush-size slider** (2 to 40 on the 800-wide canvas, with a live dot preview), a **fill (bucket) tool**, icon-only undo and clear, done).
  5. Waiting (player list with done, working, disconnected; host Skip; progress bar).
  6. Guess (the previous drawing and a text input).
  7. Reveal (author, verb, page, dots; first step of each book is the word card; the host has Back and Next page / Next book; every other player sees a "Jo is turning the pages" message instead of buttons).
  8. Finished ("That's a wrap!", a row of book tiles, Play again). No link.
- A **"Reconnecting..."** banner is needed on every in-game screen (not in the prototype). Also show a friendly "Waking things up..." message if the first connection takes more than a couple of seconds (Cloud Run and Neon cold starts).

---

## 5. Steps

### Step 0. Preflight and repo creation  → `main`

**0a. Tooling (no cloud yet).** Check tooling is installed and report versions: `git`, `gh`, `python` (latest stable), `uv`, `node` (latest LTS), `npm`, `docker`, `terraform`. Tell me what's missing and how to install it; don't install system software without asking. Check `gh auth status`. **Do not run any cloud CLI yet.**

**0b. Hosting (decided).** On 19 Nov 2026 we chose: API on Cloud Run + Neon free Postgres + UI on Firebase Hosting. Expected cost is about $0 a month for family use. Before creating anything, re-verify these figures on the providers' pricing pages and tell me if any have changed:
- Cloud Run request-based billing free tier (about 180,000 vCPU-seconds and 360,000 GiB-seconds a month; about 50 hours of play on 1 vCPU). WebSocket connections count as active requests.
- Neon Free: 1 GB storage per project, 100 CU-hours a month per project, scale to zero after 5 minutes idle, 6-hour restore window, 5 GB network transfer. Exceeding CU-hours or transfer **suspends compute until the next month; there are no overage charges** and no data is deleted. Exceeding storage makes writes fail.
- Artifact Registry: first 0.5 GB free.
- Firebase Hosting: free quota is far above our needs.

**0c. Repo.** Ask me these questions in one message and wait for answers:
- Repo name (suggest `telephone-doodle`) and visibility (suggest **public**).
- Whether I want the GCP project id to be something specific (suggest `telephone-doodle-<random suffix>`).

Create the repo in my personal account: `gh repo create <name> --<visibility> --clone`. Put this `BUILD_PLAN.md` in it, add a minimal `README.md` and `.gitignore` (Python, Node, Terraform, `.env`, `*.tfvars`, `*.tfstate*`), commit and push to `main`. Protect `main` lightly: enable "require PR before merging" if possible with `gh api`; otherwise tell me to.

**Done when:** the repo exists on GitHub with the initial commit, and I've confirmed the answers above.

---

### Step 1. Project scaffolding and CI

Branch `chore/scaffold`.

- `backend/`: `uv init` with the latest stable Python (`.python-version`), the flat package layout from section 2 (**no `src/`**), FastAPI + uvicorn + pytest + ruff + httpx + psycopg (with pool); `main.py` with `GET /healthz`; one trivial passing test. Create the package folders (`api/`, `rooms/`, `storage/`, `game_engine/`) when they first have content.
- `frontend/`: Vite React TS template (strict TS), vitest with React Testing Library and jsdom (plus `@testing-library/user-event`), ESLint, a placeholder page and one trivial passing test that renders it.
- `docker-compose.dev.yml` at the root: just a Postgres container (latest stable major) with a named volume, and `make db` to start it. Tests and local dev use it via `DATABASE_URL`.
- **The Makefile is the single source of every command.** Targets: `db`, `dev-backend`, `dev-frontend`, `backend-lint`, `backend-test`, `frontend-lint`, `frontend-typecheck`, `frontend-test`, `frontend-build`, `infra-fmt`, `infra-validate` (added with Terraform in Step 14), `e2e` (added in Step 12), and umbrellas `test`, `lint` and `ci-backend`, `ci-frontend`, `ci-infra` that run the relevant targets together. Vite dev server proxies `/api` and `/ws` to the backend.
- `.github/workflows/ci.yml`: one workflow on PR and push to `main`. A first `changes` job (path filter, for example `dorny/paths-filter`, latest version) decides what changed, and then **only the matching jobs run**: `backend` (when `backend/**` or `docker-compose.dev.yml` changed; Postgres service container), `frontend` (when `frontend/**` changed), `infra` (when `infrastructure/**` changed: `terraform fmt -check` and `validate`, no cloud credentials), and later `e2e` (when backend or frontend changed). Each job only sets up its toolchain and then calls the `make` target (for example `make ci-backend`); no job repeats a command that lives in the Makefile. A final `ci-ok` job (`if: always()`) fails if any job that ran failed and passes when jobs were skipped; **`ci-ok` is the only required status check**, so a PR that touches one area is never blocked by skipped jobs. Use the latest stable versions of actions and runtimes and dependency caching.

**Review checklist:** `make test` and `make lint` pass locally and in CI; no unused template cruft; versions used are listed in the PR.

---

### Step 2. Game engine (pure Python, no I/O)

Branch `feat/game-engine`.

Implement in `backend/game_engine/` as plain dataclasses and pure functions with **no FastAPI, no sockets, no clocks, no database**.

- Models: `Player`, `Page(kind, author_idx, text|strokes)`, `Book(owner_idx, word, pages)`, `Game`, `Phase`.
- Seats: players are seated in join order; `shuffle_seats(rng)` (lobby only) randomises the order; `kick(player)` (lobby only) removes a player and invalidates their token; `start` freezes the seat order. Seat index is the player index everywhere after start.
- Rotation: `book_index(seat, round, n) = (seat - round) % n` (each book moves to the next seat each round; seat 0 follows seat n-1). Page kind by round: round 0 = strokes (the word is picked, then drawn), odd rounds = text (a guess), even rounds >= 2 = strokes.
- Round 0 needs two inputs per player: `pick_word(player, text)` (stored on the book, hidden until reveal) and then `submit` of the drawing. The round-0 submission is rejected until a word has been picked.
- Transitions: `add_player`, `start`, `deal_words`, `pick_word`, `submit(player, page)` (idempotent per player per round, rejects wrong kind or phase), `all_submitted`, `advance_round`, `enter_reveal`, `reveal_next/prev` (moves a pointer `{book, step}` across the word card and pages of each book, and across books), `skip_player` (blank page; if no word was picked, a default word from the bank), `finish`.
- `view_for(game, player_idx) -> dict`: the personalised snapshot. Before the reveal: lobby info, who has submitted, the dealt words and own picked word in round 0, and **only** the previous page of the player's current book. During the reveal: all books and the reveal pointer.
- `to_dict(game)` and `from_dict(data)`: lossless JSON-safe serialisation of the entire game (used for snapshots in Step 5).
- Word bank: `backend/game_engine/words.json` with ~200 family-friendly words, plus `deal_words(rng, k=3)` taking an injectable `random.Random`. Dealing keeps a pool of undealt words so **no two players are ever dealt the same word**, and a shuffle draws replacements from the remaining pool (if the pool runs low, recycle words that have been dealt but not picked). `pick_word` does not compare typed words with other players' words (that would leak them).

**Tests (must include):** rotation correctness for N = 3..10 (including that it follows the seat order after `shuffle_seats`, and that each round every book moves exactly one seat the same way), no two players are dealt the same word across N = 3..10 and repeated shuffles, a shuffle never returns a word currently dealt to another player, kick and shuffle are rejected after start, each book is touched by every player exactly once, page-kind alternation for odd and even N (round 0 is a drawing; with odd N the last page is a drawing), a player never sees pages or words from other books pre-reveal, round-0 submit is rejected before a word is picked, phase and permission violations are rejected, skip-player works, the reveal pointer walks every step of every book in order, `view_for` snapshot contents per phase, `to_dict`/`from_dict` round-trips at every phase.

**Review checklist:** `game_engine` has zero I/O imports; coverage of it >= 90%.

---

### Step 3. Storage layer (Postgres)

Branch `feat/storage`.

- `backend/storage/`: an async `psycopg` pool created from `DATABASE_URL` (see the Neon connection notes in section 3: `prepare_threshold=None`, `sslmode=require`, connect timeout, retry on first connect). Create the schema from section 3 idempotently on startup.
- Functions: `create_game(code, host_name) -> id`, `save_snapshot(id, status, snapshot, expected_version) -> new_version | conflict` (the version-guarded write from section 3), `load_game(code) -> (id, version, snapshot) | None` (active games only), `finish_game(id, players, books, pages)` (one transaction: writes `players`, `books` and `pages`, sets status `finished` and `finished_at`, clears `snapshot`), `get_finished_game(id)` (used by tests and kept for v1; no endpoint uses it in v0), `delete_stale_games(older_than)`.
- Tests against the local Postgres from `docker-compose.dev.yml` (and the service container in CI): create then finish round trip (names, words and pages all stored), partial unique index on `code` (a finished code can be reused, an active one cannot), snapshot overwrite, a stale `expected_version` is rejected, missing code returns `None`, stale deletion leaves finished games alone.

**Review checklist:** no ORM and no migration tool; schema creation is idempotent; the connection string comes only from `DATABASE_URL`.

---

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

**Review checklist:** a full game can be played with only a test script (no UI); `game_engine` untouched except for bug fixes (call these out); the dependency direction in section 2 holds.

---

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

### Step 6. Rate limits and abuse protection

Branch `feat/rate-limits`.

Because the API has a public URL and Cloud Run bills per use, protect it in the app. State can be in memory because there is only ever one instance.

- Run uvicorn with `--proxy-headers` and trust Cloud Run's `X-Forwarded-For` to find the client IP (the Dockerfile passes `--forwarded-allow-ips='*'`; document why that is acceptable behind Cloud Run).
- Limits per client IP (one method for everything: a **sliding-window limiter**, a `SlidingWindowLimiter` class that keeps a deque of recent timestamps per key and allows at most N events in the last W seconds, with idle keys cleaned up periodically; do not also implement token buckets; values configurable in `settings.py`; suggested defaults): create room 5 per minute; join attempts 20 per minute; **failed joins (unknown code) 10 per minute** (the code space is small, so this stops guessing); at most 20 concurrent WebSocket connections per IP; at most 20 inbound WebSocket messages per second per connection (close with 1008 when exceeded).
- Global caps: at most 200 rooms and 1,000 concurrent WebSocket connections in memory; beyond that, creating rooms returns 503 with a friendly message.
- Return `429` with a `Retry-After` header; the frontend shows a friendly message (handled in the lobby step).
- Tests: each limit triggers and recovers, the limits are per IP, and limits don't affect a normal 10-player game.

**Review checklist:** limits are configurable by env; a normal game never hits them; the proxy-header handling is explained in the PR.

---

### Step 7. Design review gate (me, then Claude Code)

No PR until I approve.

1. I will review the interactive prototype of the screens in section 4 (**https://claude.ai/artifact/M7Wh9dZHav7oH6aMPWqgHY**, private to me) and send change requests. **Do not start any frontend step until I say "design approved".** Backend steps do not wait for this.
2. When I approve, I will export the prototype from the design tool and give you the files (or tell you where they are). Commit them to `frontend/design/` on branch `docs/design-reference` (screenshots and the exported HTML, plus a short `README.md` listing which export is which), and open a PR.
3. From then on, `frontend/design/` plus section 4 is the visual source of truth. If a screen needed in the build is missing from the prototype (for example the Reconnecting banner, the Draw screen in later rounds, or a wide-screen reveal), propose the design in the PR description before building it.

---

### Step 8. Frontend foundation and lobby

Branch `feat/lobby`. Requires Step 7 approved.

- Routing (`react-router`): `/` (create or join) and `/room/:code`. The room page shows the right screen for the current phase. Firebase Hosting rewrites every path to `index.html`, so deep links work.
- Config: `src/config.ts` reads `import.meta.env.VITE_API_URL` (empty in dev, so requests go through Vite's proxy) and derives the HTTP and `ws(s)://` base URLs from it.
- `game/useGameSocket(code)` hook: connects with the token from `localStorage`, auto-reconnects (immediately on close code 1012, then exponential backoff), exposes the latest `state`, a `connection` status and `send()`. Typed message and state types in `frontend/src/game/types.ts` mirroring the backend schemas (one file, with a comment where it mirrors Pydantic).
- Home page and Lobby matching the design: create room or join with code and name; lobby shows the code (big, with copy button), the player list with connected status, numbered seat order with a host-only Shuffle order button and remove (cross) buttons, host-only Start button (disabled under 3 players). Friendly handling of `429` and `503`.
- Design tokens from section 4 as CSS custom properties in one stylesheet. Mobile-first, 44px minimum tap targets, visible focus.
- The "Reconnecting..." banner and the "Waking things up..." message for slow first connections.
- **Rejoin:** keep `{code, token}` in `localStorage`; the home page shows "Rejoin room KQFM" while a saved seat exists (and clears it if the server says the room is gone or the player was removed). The socket hook also reconnects immediately on `visibilitychange` (tab visible again) and the `online` event, which covers locked phones.
- **Frontend tests (vitest + Testing Library):** the socket hook against a fake `WebSocket` (connect, reconnect after 1012, backoff, reconnect on visibility change, state updates), the Home and Lobby screens (create, join, error and `429` messages, host-only controls visible only to the host, shuffle and remove send the right messages, Start disabled under 3 players), and the rejoin flow.

**Review checklist:** two browser tabs can create, join and see each other live; refreshing a tab rejoins the same seat; restarting the dev backend shows the banner and recovers.

---

### Step 9. Drawing canvas component

Branch `feat/canvas`. Requires Step 7 approved.

A standalone, well-tested component, not yet wired into the game.

- **Stroke format** (shared with the backend as an opaque JSON blob):
  ```json
  { "v": 1, "w": 800, "h": 600,
    "ops": [
      { "t": "s", "color": "#222222", "size": 4, "pts": [[0.127, 0.147], [0.131, 0.150]] },
      { "t": "f", "color": "#F08A24", "x": 0.40, "y": 0.55 } ] }
  ```
  Logical canvas is fixed 4:3 (800×600). Points are stored as 0..1 fractions of width and height so drawings render correctly at any display size. A drawing is an ordered list of **operations**: `s` is a brush stroke (the eraser is a white stroke), `f` is a **flood fill** at a point. Rendering replays the operations in order; a fill is computed on an offscreen 800×600 canvas (scanline flood fill with a small colour tolerance so anti-aliased edges don't leak) and then scaled to the display size, so every device shows the same result. Cache the rendered bitmap so a `StrokeView` does not redo fills on every paint. Undo removes the last operation.
- `DrawingCanvas` (editable): Pointer Events (`pointerdown/move/up/cancel`), `touch-action: none`, correct handling of `devicePixelRatio` and CSS resizing, smoothing via quadratic curves between points, the 14-colour palette and eraser from section 4, a **custom colour picker** (the custom swatch opens a popover with a hue slider and a saturation/brightness square, or the browser's native colour input if that proves more reliable on iOS; tell me which you chose, and keep the last few custom colours as extra swatches), a **brush-size slider** (an `<input type="range">`, 2 to 40, with a live preview dot; stroke `size` is stored in logical canvas pixels), a **Fill tool** (tap inside a region to fill it with the selected colour; eraser colour makes it fill with white), icon-only **Undo** (removes the last operation) and **Clear**, all with accessible labels and 44px targets. Throttle or simplify points to keep payloads small.
- `StrokeView` (read-only renderer) reusing the same drawing function, used later in guessing and the reveal.
- Pure helper functions in `frontend/src/lib/strokes.ts` (normalise, simplify, serialise, size estimate) and a **pure flood-fill function over a pixel buffer** (`Uint8ClampedArray`, width, height, seed, colour, tolerance) in `frontend/src/lib/floodfill.ts`, with vitest unit tests (fill a closed shape, fill does not leak through a closed outline, tolerance handling, filling an already-filled area is a no-op, edge and corner seeds). jsdom has no real canvas, so canvas behaviour itself is covered by component tests with a mocked 2D context (the right operations are produced for pointer sequences; undo and clear) and by the Playwright suite in Step 12.
- A dev-only `/sandbox` route to try the canvas.

**Review checklist:** works with mouse, touch and stylus (test on a phone via the dev server on the LAN if possible); a typical drawing serialises to well under 50 KB; no scroll or zoom gestures hijack drawing on iOS.

---

### Step 10. Gameplay screens

Branch `feat/gameplay`. Requires Steps 8 and 9.

Wire the UI to the `state` snapshots for rounds, matching the design:

- **Pick a word, then draw it (round 0):** 3 word buttons, a "Shuffle words" button, an "or type your own" input; "Draw it" sends `pick_word` and moves to the Draw screen with the picked word on the note. Both screens are Round 1.
- **Draw (all drawing rounds):** the note shows the word (round 0) or the previous guess (later rounds), the canvas, a "Done" button that sends `submit_page` with strokes.
- **Guess:** shows the previous drawing via `StrokeView`, a text input and a "Done" button.
- **Waiting:** a list of players with done, working or disconnected, a progress bar, and for the host a "Skip" button beside any disconnected, unfinished player.
- Round indicator ("Round 2 of 5") and progress segments, and a clear "you've already submitted" state. After a refresh, a locked phone, an accidental exit or a deploy-triggered reconnect mid-round, the screen restores correctly: the picked word and submitted state come from the server, and the **draft drawing and half-typed guess come back from `localStorage`** (saved after every stroke or keystroke, keyed by room code, round and player, cleared on submit, and expired after 24 hours).
- **Frontend tests:** the word screen (pick, shuffle, type your own, "Draw it" sends `pick_word`), the draw screen (Done sends the operations, draft saved and restored from a pre-filled `localStorage`, cleared after submit), the guess screen (shows only the previous page, submit sends text, draft restore), the waiting screen (statuses, Skip visible only to the host and only for disconnected players), and a "game state to screen" mapping test for every phase.

**Review checklist:** 3 browser tabs can play a full game to the end of the final round; the guess screen never shows anything but the immediately previous page.

---

### Step 11. Reveal and finished screen

Branch `feat/reveal`.

- **Reveal:** shows "<owner>'s book" and "Book b of N", the page's author with a verb ("Chose the word", "Drew it", "Guessed"), the content (the word card, a guess note or `StrokeView`), page dots and "Page p of N+1". The host has Back / Next page buttons (and keyboard arrows), and "Next book" on the last page of a book (it becomes "Finish game" on the last book). Every other player sees a short "<host> is turning the pages" message instead of buttons and follows the pointer automatically. Make it scale well on tablet and large screens.
- **Finished screen:** "That's a wrap!", the row of book tiles and "Play again" (new room). No link and no archive page.
- **Frontend tests:** the reveal for the host (Back disabled on the first step, Next page, "Next book", "Finish game" on the last book, arrow keys send the right messages) and for a non-host (no buttons, follows the pointer in the state), the word card and page rendering for each step kind, and the finished screen ("Play again" creates a new room).

**Review checklist:** with 3 tabs, the host's Next moves every tab together; refreshing a non-host tab mid-reveal returns to the current page; the finished game is in the database with names, words and pages.

---

### Step 12. End-to-end tests

Branch `feat/e2e`.

Playwright tests in `frontend/e2e/` that drive the real UI against the real backend and a real Postgres, with **three browser contexts as three players** (the only way to test what no unit test can: the canvas, the sockets and the multi-player sync together).

- `make e2e` starts Postgres (`make db`), the backend and the frontend (production build served locally), then runs Playwright. Use the latest stable Playwright and Chromium; add a WebKit project too if it is cheap, because iOS Safari is the riskiest browser for drawing.
- **Scenarios:** (1) full 3-player game: create room, join with code, shuffle seat order and check all three lobbies show the same order, start, pick a word (and check the three players' dealt options are all different), draw with pointer events (brush and fill), submit, guess, run through every round, reveal where the host's Next moves all three screens together and a non-host has no buttons, finish; (2) refresh a non-host mid-round (seat, word and draft drawing come back) and mid-reveal (lands on the current page); (3) host removes a player in the lobby (that player sees the removal message and the others' lists update); (4) restart the backend process mid-game and check the clients reconnect and the game continues; (5) a 429 from the rate limiter shows the friendly message.
- Keep the suite fast (aim for under about 3 minutes) and stable: no fixed sleeps, use Playwright's auto-waiting, retries only in CI and capture traces on failure.
- Add the `e2e` job to `ci.yml` (runs when backend or frontend changed; uploads the Playwright report on failure) and the `make e2e` target.

**Review checklist:** `make e2e` passes locally on a clean checkout and in CI; each scenario above exists; no flaky retries needed locally.

---

### Step 13. Packaging

Branch `chore/packaging`.

- `backend/Dockerfile` (API only): multi-stage if useful; the official `python` slim image at the same Python version as `.python-version` (verify the tag exists), install deps with `uv` from the lockfile, run as non-root. Command: `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*' --timeout-graceful-shutdown 8`. Add the `org.opencontainers.image.source` label pointing at the repo. Keep the image small.
- `frontend/firebase.json`: hosting `public` is `dist`; rewrite `**` to `/index.html`; long-lived immutable cache headers for `/assets/**` (hashed filenames) and `no-cache` for `index.html`.
- `frontend/.env.production.example` documenting `VITE_API_URL`.
- Local full-stack check: `make db`, the API container pointed at that Postgres, and the Vite dev server (or a production build served locally) pointed at the container.

**Review checklist:** `docker build` works from a clean checkout and the container passes a full multi-tab game against local Postgres; the container stops cleanly on SIGTERM within 10 seconds; image size reported in the PR.

---

### Step 14. Terraform for GCP

Branch `infra/terraform`.

First, **ask me for**: the billing account id and its currency, and my Google account email (for budget alert emails). This is the first step where `gcloud` is used, and only for Terraform authentication (`gcloud auth application-default login`, which I run myself).

- All Terraform files sit directly in `infrastructure/`, split as in section 2. Remote state in a GCS bucket (created in Step 15). Latest provider versions (`google` and `google-beta`).
- `apis.tf`: enable Cloud Run, Artifact Registry, Secret Manager, IAM credentials, Security Token Service, Firebase, Firebase Hosting and Billing Budgets APIs.
- `registry.tf`: Artifact Registry Docker repository in `europe-west2`, with a **cleanup policy that keeps only the 3 most recent images** and deletes older ones.
- `iam.tf`: a runtime service account for Cloud Run (only `secretmanager.secretAccessor` on the one secret); a deploy service account for GitHub Actions with the minimum roles (push to the registry, deploy to Cloud Run, act as the runtime service account, deploy Firebase Hosting); **Workload Identity Federation** pool and provider for GitHub with a condition restricting it to my repo, and nothing else, so no service account keys are created anywhere.
- `secrets.tf`: the Secret Manager secret for the Neon connection string, **without a version**. I add the value by hand in Step 15. Use `prevent_destroy` on it.
- `cloud_run.tf`: the API service in `europe-west2`: 1 vCPU, 512 MiB, **`max-instances=1`, `min-instances=0`, concurrency 250, request timeout 3600 s**, request-based billing, startup probe on `/healthz`, public invoker (`allUsers`), env vars `ALLOWED_ORIGINS`, `DATABASE_URL` from the secret, and the rate-limit settings. The container image is set to a placeholder (for example Google's hello image) with `lifecycle { ignore_changes = [template[0].containers[0].image] }`, because GitHub Actions deploys the real image.
- `hosting.tf`: the Firebase project (on the existing GCP project) and the Hosting site.
- `budget.tf`: a monthly budget of $5 (in the billing account's currency) with email alerts at 20% ($1) and 100% ($5), plus a forecasted-100% alert.
- `outputs.tf`: the Cloud Run URL, the Hosting URL, the Artifact Registry path, the deploy service account email and the Workload Identity provider name.

**Review checklist:** `terraform fmt -check` and `terraform validate` pass; `terraform plan` output summarised in the PR, including the expected monthly cost (about $0). **Do not apply yet.**

---

### Step 15. Bootstrap: apply infrastructure and create the Neon database

Branch `docs/infra-bootstrap` (docs and small fixes only; the steps below are actions, not code). There are exactly three manual items; everything else is Terraform.

1. **State bucket (manual, ask first).** Create the Terraform state bucket in the GCP project (versioning on, private, uniform access). Add the backend config to Terraform.
2. **Terraform apply.** Run `terraform plan`, show me the summary, wait for approval, then `terraform apply`.
3. **Neon project (manual, by me).** I create the Neon project myself in the Neon console: region AWS `eu-west-2` (London), the latest available Postgres version, a database `doodle` and a role for the app. Neon is created by hand (not Terraform) on purpose: the community provider is unofficial, and a Terraform mistake must never be able to delete the database. Claude Code gives me the exact steps, including how to copy the **pooled** connection string. Neon's auto-suspend after 5 minutes is fixed on the free plan.
4. **Secret value (manual, by me).** I add the connection string to Secret Manager without it appearing in chat or shell history: `gcloud secrets versions add <secret-name> --data-file=-` and paste when prompted (Claude Code gives me the exact command). Then Claude Code verifies that the secret has a version, without reading it.
5. **GitHub configuration.** Claude Code sets, with `gh variable set` (not secret, none of these are sensitive): the GCP project id, region, Artifact Registry path, Cloud Run service name, deploy service account email, Workload Identity provider name, and `VITE_API_URL` (the Cloud Run URL). Then redeploy the Cloud Run service once so `ALLOWED_ORIGINS` matches the Hosting URL.
6. Document the whole bootstrap in `infrastructure/README.md` (including how to tear down with `terraform destroy`, which leaves the Neon project alone).

**Review checklist:** `terraform plan` shows no changes after apply; the secret has a version; the placeholder Cloud Run service answers on its URL.

---

### Step 16. CD pipelines

Branch `ci/deploy`.

- **`deploy-api.yml`**: triggers on pushes to `main` that change `backend/**` or the workflow itself (and manually). Steps: authenticate with Workload Identity Federation (`google-github-actions/auth`, latest), build the image with Buildx and push it to Artifact Registry tagged with the commit SHA, deploy a new revision with `--no-traffic --tag candidate`, then call `https://candidate---<service>-<hash>.europe-west2.run.app/healthz` until it passes (fail the job and leave traffic untouched if it doesn't), then shift 100% of traffic to the new revision. **Rollback:** record the previous revision before the switch; if a final health check on the live URL fails, move traffic back to it. Use `concurrency: deploy-api` so deploys never overlap.
- **`deploy-frontend.yml`**: triggers on pushes to `main` that change `frontend/**` (and manually). Install, build with `VITE_API_URL` from the repo variable, and run `firebase deploy --only hosting` authenticated through the same Workload Identity Federation (latest `firebase-tools`). Firebase keeps previous releases, so rollback is one command; document it.
- **Deploys during a game:** Cloud Run sends SIGTERM to the old revision after traffic shifts; the old instance closes sockets with 1012, players reconnect to the new revision, and the room loads from the database. Document this and test it by deploying during a game.
- Terraform changes are applied by me from my machine with plan and approval, not by CI. Say so in the README.

**Review checklist:** merging an API change deploys only the API and a UI change deploys only the UI; the live site works from the Hosting URL; a deploy during a game resumes after a few seconds of reconnecting.

---

### Step 17. Live verification and docs

Branch `docs/wrapup`.

- Play a full game against the live Hosting URL using at least 3 devices or tabs, including a phone, and report what happened (including any rough edges: cold start time, Neon wake-up time).
- Check the Cloud Run and Neon usage pages and the budget page after the test game, and report the numbers so I can see how far a game moves them.
- Write a real `README.md`: what the game is, how to play, local dev setup, architecture overview (including the two-origin setup, the package dependency direction, reveal sync and load-on-demand rooms), deploy and rollback for both pipelines, cost and limits, known limitations, and the v1 roadmap below.
- Add a short `docs/PLAYTEST.md` checklist (rejoin after refresh, skip player, odd and even player counts, long text, big drawings, slow network, scale-to-zero while phones are locked, deploy during a game, reveal on several devices).

**Review checklist:** I can play a family game on my phone from the live URL.

---

## 6. Hosting notes (for explaining things to me)

- **Cloud Run** runs the API container only when needed and scales to zero when nobody is connected. It gives the service an HTTPS `*.run.app` URL, so there are no certificates or domain names to manage. We cap it at one instance, so cost is bounded. It supports WebSockets, and a connection counts as an active request while it is open.
- **Neon** is serverless Postgres. On the free plan the database compute sleeps after 5 minutes idle and wakes in about a second. If a monthly limit is hit, compute is suspended until the next month rather than billed.
- **Firebase Hosting** serves the built React files from a global CDN. It is free at our scale and deploys in seconds.
- **Artifact Registry** is GCP's container image store (like ECR). A cleanup policy keeps it at about zero cost.
- **Workload Identity Federation** lets GitHub Actions prove who it is to GCP using a short-lived token, so there are no downloaded keys to leak or rotate.
- **Budget alerts** email me at $1 and $5 a month. They do not stop spending by themselves; `max-instances=1`, rate limits and Neon's no-overage behaviour are what keep the worst case small.

---

## 7. v1 backlog (do not build now, just list in README)

- Round timers (host toggle: off / 60 s / 90 s) with auto-submit
- Fuzzy-match scoring for guesses (the starting word is already stored, so round 1 can be scored against it; drawer and guesser both score), scoreboard
- Votes with limited votes per player, highlights reel, "drift" detection, awards (finished games are already saved for this)
- A way to look back at past games (a link or a history page)
- Stroke replay animation in the reveal
- Themed and custom family word packs
- Export a book as a shareable image or GIF
- Async play mode
- Hall of fame across game nights
- Remove a player **mid-game** (they would be auto-skipped for the remaining rounds, shown as skipped in the reveal; in v0 the host's Skip button covers this one round at a time), plus lock-room and ban for kicked players
- Drag to reorder seats in the lobby (v0 only has Shuffle order)
- **Observability dashboard** (Cloud Monitoring, free): Cloud Run's built-in metrics (requests, latency, 5xx rate, instance count and how often it sits at the max of 1, memory, billable time, cold-start time); app metrics from the structured logs (rooms and connections active, games started and finished, reconnects, WebSocket close codes, snapshot write time and conflicts, rate-limit hits); Neon's console for compute hours, storage and wake-ups; error tracking for both sides (for example Sentry's free tier); an uptime check; and alerts on 5xx rate, sustained max instances and budget. Managed in Terraform.
- Multiple API instances (shared room state through Postgres LISTEN/NOTIFY or Redis) if usage ever outgrows one instance
- Scheduled database export if the Neon 6-hour restore window is not enough

---

## 8. Definition of done for v0

- [ ] Repo in my personal GitHub account, with all steps merged via reviewed PRs
- [ ] CI green on `main`; latest stable versions in use throughout (versions listed in the README)
- [ ] I approved the UI design before the frontend was built, and the exports live in `frontend/design/`
- [ ] UI live on Firebase Hosting and API live on Cloud Run, each deployed automatically from `main` by its own pipeline, with rollback documented
- [ ] A 3 to 10 player game plays from word pick and drawing to reveal on phones, with reconnect and skip-player working
- [ ] Seat order is a consistent circle, the host can shuffle it and remove players in the lobby, and no two players are dealt the same word
- [ ] Drawings include a working fill tool; an in-progress drawing survives a refresh, a locked phone and a deploy
- [ ] Backend, frontend and Playwright end-to-end tests all exist and pass; CI runs only the jobs for the changed areas, with `ci-ok` as the one required check
- [ ] In the reveal, the host's taps move every player's screen together
- [ ] A deploy, a restart or a scale-to-zero during a game does not end it
- [ ] Rate limits and connection caps in place; budget alerts at $1 and $5 confirmed working
- [ ] Finished games are saved with player names, words and pages
- [ ] Infrastructure managed by Terraform (except the state bucket, the Neon project and the secret value), with a documented teardown
- [ ] README explains how to run, deploy and recover

---

## 9. Build log: decisions and deviations

Append-only. Newest step last. See working agreement rule 13.

### Step 0 — preflight and repo creation (21 Nov 2026)

**Decisions (the answers to 0c):**

| Question | Answer |
|---|---|
| Repo name | `telephone-doodle` |
| Visibility | **Public** |
| GCP project id | **`telephone-doodle-9e7a70a4`** (recorded only; nothing created) |

**Tooling found (0a).** git 2.43.0, gh 2.100.0 (authed as `Ryhhill1998`, SSH),
uv 0.13.6, node 26.13.1 (confirmed Latest LTS, "Lithium"), npm 11.20.0,
docker 29.8.0 with Compose v5.2.0, terraform 1.14.7. System python is 3.14.4, but
that is irrelevant: `uv` pins the project's own interpreter and `cpython-3.15.2`
is available, confirming the plan's claim that **Python 3.15 is the current
stable release**.

**Deviations:**

1. **Repo created with `--source=.`, not `--clone`.** 0c says
   `gh repo create <name> --<visibility> --clone`. `BUILD_PLAN.md` already lived in
   `~/Documents/personal/telephone-doodle`, so cloning would have nested a second
   working copy inside it. Used
   `gh repo create telephone-doodle --public --source=. --remote=origin --push`
   instead. Identical end state.
2. **Branch protection is lighter than "require PR before merging" implies.**
   Set `required_approving_review_count: 0` and `enforce_admins: false`.
   GitHub forbids approving your own pull request, so requiring even one approval
   would lock the sole owner out of his own repo. Force-pushes, branch deletion and
   unresolved conversations are blocked. **No required status check yet** —
   `ci-ok` does not exist until Step 1, and naming a non-existent check blocks every
   PR; it is added as the single required check in the Step 1 PR.
3. **Commit identity is the GitHub handle, not the global git identity.** The
   initial commit was authored with a work email address, which would have been
   permanently visible in a public repo's history. It was amended and force-pushed
   (Ryan removed branch protection for the push and it was immediately re-applied),
   so the work address never remained in the published history. Personal projects now
   resolve to `Ryhhill1998 <95857127+Ryhhill1998@users.noreply.github.com>`
   automatically, via `[includeIf "gitdir:~/Documents/personal/"]` in `~/.gitconfig`
   pointing at `~/.gitconfig-personal`; repos under `~/Documents/repos/` keep the
   work identity. **No personal/public repo should ever be committed to with the work
   address.**
4. **0b (free-tier re-verification) deferred to the start of Step 14.** Nothing is
   created in Step 0, and working agreement rule 8 forbids touching cloud providers
   before Step 14. The Cloud Run, Neon, Artifact Registry and Firebase Hosting figures
   in 0b will be re-checked against the live pricing pages before a line of Terraform
   is written, and reported then.
5. **Terraform upgrade deferred to the start of Step 14.** Installed 1.14.7, latest
   stable 1.17.2. `tenv` manages it, so the bump is user-local and takes one command.
   No Terraform is written before Step 14, so upgrading earlier gains nothing.

**Open proposals — flagged to Ryan, agreed in principle, not yet applied.**
Each is applied (and logged again) in the step it belongs to:

- **Step 15 will fail its first `terraform apply` as written.** `cloud_run.tf`
  (Step 14) wires `DATABASE_URL` from a Secret Manager secret, but 15.2 applies
  Terraform *before* the secret value is added by hand in 15.4. A Cloud Run v2
  revision referencing a secret with no versions cannot deploy. Fix at Step 14/15:
  a **two-pass bootstrap** — apply everything except the Cloud Run service, add the
  secret version by hand, then apply again.
- **The ~600-line PR rule (agreement rule 3) does not fit several steps.** Step 2
  alone is a ~200-word `words.json` plus a large test matrix; Steps 4, 8 and 10 are
  comparable. Generated and data files are counted separately from reviewable code,
  and steps are split at clean seams with a note in the PR when that happens.
- **Step 14: `ALLOWED_ORIGINS` needs both Firebase domains**,
  `https://<project>.web.app` *and* `https://<project>.firebaseapp.com`, or the UI
  breaks on whichever is omitted.
- **Step 6: raise the per-IP concurrent WebSocket cap from 20 to 40.** A family of
  up to 10 players behind one home NAT shares a single public IP, and reconnect
  storms leave half-closed sockets lingering, so 20 is uncomfortably tight.

### Step 1 — project scaffolding and CI (21 Nov 2026)

**Versions resolved** (nothing pinned from memory; package managers resolved these):

| | |
|---|---|
| Python | **3.15.2** (`.python-version` pins `3.15`, uv fetches the interpreter) |
| FastAPI 0.165.0 | uvicorn 0.54.0 (`[standard]`), starlette 1.10.0, pydantic 2.14.4 |
| psycopg | 3.3.9 (`[binary,pool]`), psycopg-pool 3.3.3 |
| Backend dev | pytest 9.2.0, pytest-asyncio 1.5.0, pytest-cov 7.1.0, ruff 0.17.6, httpx2 2.16.2 |
| Node | **26.13.1** (Latest LTS "Lithium"), npm 11.20.0 |
| Frontend | Vite 8.3.6, React 19.3.1, TypeScript 7.0.2, @vitejs/plugin-react 6.1.2 |
| Frontend dev | vitest 5.1.1, @vitest/coverage-v8 5.1.1, jsdom 31.0.1, Testing Library (react 16.3.3, dom 10.4.2, jest-dom 8.0.0, user-event 14.6.13), oxlint 1.90.0 |
| Postgres | **19.0** (`postgres:19`), local and in CI |
| Actions | checkout v7.0.1, setup-node v7.1.0, setup-uv v10.4.0, paths-filter v4.0.3, setup-terraform v4.0.1 |

**Deviations:**

1. **oxlint, not ESLint.** Step 1 says ESLint. The current Vite `react-ts` template
   ships **oxlint** instead, and no longer generates any ESLint config. Kept the
   template's choice rather than tearing it out and hand-building an ESLint +
   typescript-eslint + react-plugins stack: it is the upstream default, needs no
   extra config, and agreement rule 10 prefers fewer moving parts. The script is
   `oxlint --deny-warnings`, because oxlint reports violations as *warnings* and
   would otherwise exit 0 and pass CI silently (verified both ways with a probe
   file). **Say so and this gets swapped for ESLint.**
2. **`httpx2`, not `httpx`.** Step 1 lists httpx. Starlette 1.10's `TestClient`
   now emits `StarletteDeprecationWarning: Using httpx with starlette.testclient
   is deprecated; install httpx2 instead`. Used httpx2 2.16.2.
3. **Two dev dependencies added beyond the step's list:** `pytest-asyncio` (Step 3's
   storage layer and Step 4's WebSocket tests are async) and `pytest-cov`
   (Step 2's review checklist requires `game_engine` coverage >= 90%). Adding them
   now avoids churning the lockfile in the next two steps.
4. **TypeScript `strict` had to be set by hand.** The template's `tsconfig.app.json`
   and `tsconfig.node.json` no longer include it, and the plan requires strict TS.
   Set explicitly in both, and confirmed enforced with a throwaway file containing
   an implicitly-typed parameter (`error TS7006`).
5. **Postgres volume mounts at `/var/lib/postgresql`, not `.../data`.** Postgres 18+
   Docker images store data in a major-version-specific subdirectory and refuse to
   start against the old layout. The first `make db` failed on exactly this; the
   compose file carries a comment and a link to the upstream change.
6. **`pytest` runs with `-W error`.** Deprecation warnings from FastAPI, Starlette
   or psycopg fail the backend suite while they are still cheap to fix, rather than
   accumulating unnoticed. This is what surfaced deviation 2.
7. **Path filters are wider than the step describes.** `Makefile` and
   `.github/workflows/ci.yml` changes trigger **both** the backend and frontend jobs,
   and `.nvmrc` triggers the frontend, because a change to any of them can break
   those jobs. The `infra` filter is `infrastructure/**` only, for the reason below.
8. **`infra-fmt`, `infra-validate` and `ci-infra` are not in the Makefile yet.** The
   plan already defers them to Step 14. The `infra` CI job exists in `ci.yml` with
   its path filter, but can only ever fire once `infrastructure/**` exists, which
   first happens in the Step 14 PR that also adds the targets. **Step 14 must add
   `Makefile` and `ci.yml` to the infra filter** to close the gap left by deviation 7.
9. **Makefile has targets beyond the step's list:** `install`, `backend-install`,
   `frontend-install` (so CI's dependency-installation step is a make target too, not
   a duplicated command — agreement rule 11), plus `db-stop`, `backend-format` and
   `help`.
10. **`.nvmrc` added at the repo root**, so the Node version has one home and
    `actions/setup-node` reads it via `node-version-file` instead of a hardcoded
    version in the workflow.
11. **No `backend/settings.py` yet**, and none of `api/`, `rooms/`, `storage/` or
    `game_engine/` exist. Step 1 says to create package folders when they first have
    content; there is no configuration to hold until Step 3.
12. **The template's `frontend/.gitignore` was deleted** in favour of the root one,
    with its two unique entries (`logs/`, `*.tsbuildinfo`) folded in, so there is a
    single ignore file to reason about.

**Verified locally:** `make lint` and `make test` both pass; `make frontend-build`
produces a 219.66 kB bundle (68.65 kB gzipped); `make db` starts Postgres 19.0 and
data survives `make db-stop` + `make db`; the Vite dev proxy forwards `/api/...` to
the backend with the path intact (confirmed in uvicorn's own request log) and
upgrades `/ws/...` through to it. The first proxy check was run against the wrong
port — 5173 was already held by an unrelated container, so Vite had silently fallen
back to 5174 — and was redone on a pinned free port with `--strictPort`.

### Housekeeping before Step 2 (21 Nov 2026)

Two corrections, neither of them new build work.

1. **Working agreement rules 1 and 3 rewritten** at Ryan's request, after Step 1
   arrived as a single large commit:
   - Rule 1 now requires **small, logically ordered commits** within a PR, planned
     before the work starts, and allows a step to span more than one PR.
   - Rule 3's ~600-line budget is replaced by **splitting on logical units**. A
     diff staying under an arbitrary number is not the goal; dividing where the
     meaning divides is. His example, applied immediately below.
2. **`.nvmrc` moved from the repo root to `frontend/`.** Step 1 put it at the root
   on the mistaken reasoning that the Makefile needed it there; the Makefile drives
   npm with `--prefix frontend` and never consults nvm. The root placement also
   broke symmetry with `backend/.python-version`. Each stack now pins its own
   runtime version beside the code that needs it. `actions/setup-node` reads the
   new path, and the frontend path filter drops its now-redundant `.nvmrc` entry.

**Consequence for Step 2:** it ships as **two PRs** rather than one —
`feat/word-bank` (`words.json` plus dealing, shuffling and the uniqueness tests)
and `feat/game-engine` (models, rotation, transitions, `view_for`, serialisation).
Data is reviewed separately from the logic that consumes it.

### Step 2a — word bank (21 Nov 2026)

First of Step 2's two PRs, per the new rule 3: the data and its dealing rules,
reviewed apart from the engine that consumes them.

**Deviations:**

1. **`game_engine` does touch the filesystem, once.** The Step 2 checklist says
   "zero I/O imports", but the plan also puts `words.json` inside
   `game_engine/`, so something must read it. `load_words()` reads the bundled
   file through `importlib.resources` and is the only such call in the package.
   Purity is preserved where it matters: `WordBank` takes its vocabulary as an
   argument, so every test builds one from a literal list and never touches
   disk. The guard test allows `json` and `importlib.resources` by name and
   bans everything else.
2. **The dependency direction is enforced by a test, not by ruff.** Ruff's
   banned-api rule is global and cannot be scoped to one directory without a
   second config file. `tests/game_engine/test_dependency_direction.py` walks
   each module's AST instead and fails with a sentence explaining the rule. It
   also bans calls to the global `random` generator, which would quietly make
   games unreplayable. All three rules were probed by introducing the violation
   they catch, so they are known to fail and not merely to pass.
3. **`WordBank.to_dict`/`from_dict` ship here rather than with the engine.**
   The plan lists serialisation under the engine's `to_dict(game)`. The bank
   owns state the engine cannot reconstruct — which options each player is
   holding — and Step 5 needs that to survive a reload so a reconnecting player
   is shown the same three words rather than a fresh deal that might collide
   with someone else's. Keeping it with the bank makes the engine PR a
   composition job.
4. **210 words, not "~200".** Comfortably above the worst case (10 players x 3
   options = 30 before any shuffling) with recycling on top.

**Decided while building:** a *shuffle* is the same operation as a deal — the
old options are released before new ones are drawn, which is what prevents a
shuffle returning a word another player is looking at. Typed words are not
retired, matching section 1's reasoning that comparing them with other players'
words would leak what someone else chose.

**Verified:** 44 tests pass; `game_engine` coverage 100% (the checklist asks for
>= 90%); `make lint` and `make test` green.
