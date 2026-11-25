# Telephone Doodle

A web app for playing "telephone pictionary" with family.

Each player starts a **book** by picking a word and drawing it. The books are then
passed around the circle, and players alternate between writing a guess for the
drawing they're handed and drawing the guess they're handed. At the end, every book
is revealed page by page — usually to considerable confusion.

3 to 10 players, all online at the same time, on phones, tablets or laptops.

## Status

**In development — nothing is deployed yet.**

The full specification, the locked technical decisions and the step-by-step build
plan all live in [`docs/plan/`](./docs/plan/) and [`docs/steps/`](./docs/steps/).
Those are the source of truth; this README will be rewritten properly in the
final step.

## Planned stack

| Part | Choice |
|---|---|
| Backend | Python + FastAPI + WebSockets, `uv`, `ruff`, `pytest` |
| Database | Neon Postgres (free plan), `psycopg` 3, plain SQL |
| Frontend | Vite + React + TypeScript (strict), plain CSS |
| API hosting | Google Cloud Run, `europe-west2` (London) |
| UI hosting | Firebase Hosting |
| Infrastructure | Terraform (GCS remote state) |
| CI/CD | GitHub Actions, Workload Identity Federation (no stored keys) |
| Tests | `pytest`, `vitest` + Testing Library, Playwright end-to-end |

## Repo layout

```
backend/         FastAPI app: api/, rooms/, storage/, game_engine/
frontend/        Vite + React UI, design/ references, e2e/ Playwright suite
infrastructure/  Terraform for GCP
.github/         CI and deploy workflows
Makefile         every lint, test and build command lives here
```

Not all of these exist yet — they are created step by step.

## Development

Every command is a `make` target, and CI calls those same targets. `make help`
lists them.

```sh
make db        # local Postgres in Docker (the backend tests need it)
make install   # backend and frontend dependencies
make test      # backend and frontend suites
make lint
```

The backend tests run against a real Postgres rather than a fake, because what
they check — a partial unique index, a version-guarded write, a transaction that
has to be all or nothing — is decided by the database. `DATABASE_URL` points at
the container above by default; in production it comes from Secret Manager, and
there is no fallback if it is unset.

A game's state is written to Postgres after every change, so a deploy, a
restart or Cloud Run scaling to zero costs players a few seconds of
reconnecting, not the game in progress. A finished game's snapshot — and the
player tokens in it — is deleted as soon as the game ends.

## Contributing

One step, one branch, one pull request. `main` requires a reviewed PR.

## Licence

Not yet decided.
