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

*How it is enforced* (added in Step 2b's review): the layering is an import-linter contract in `backend/pyproject.toml`, run by `make backend-lint`. The layers that do not exist yet are written in parentheses, so each one starts being checked in the step that creates it. **Every step that adds a package must also add it to `root_packages` and un-parenthesise its layer** — a package missing from `root_packages` is absent from the import graph, so its contract passes by having nothing to check. `tests/game_engine/test_package_boundaries.py` fails when the config and the packages on disk disagree, so this cannot be forgotten silently; it also holds `game_engine`'s import allowlist and the ban on the global `random` generator.

---
