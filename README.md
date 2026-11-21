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
plan all live in [`BUILD_PLAN.md`](./BUILD_PLAN.md). That file is the source of
truth; this README will be rewritten properly in the final step.

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

Every command is a `make` target, and CI calls those same targets. The Makefile
arrives in the first scaffolding step.

## Contributing

One step, one branch, one pull request. `main` requires a reviewed PR.

## Licence

Not yet decided.
