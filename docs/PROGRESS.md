# Progress

Update at the end of every step: tick it and add at most 5 lines under "What exists".

## Steps
- [x] 0 Preflight and repo creation
- [x] 1 Project scaffolding and CI
- [x] 2 Game engine (2a word bank, 2b engine)
- [x] 3 Storage layer
- [x] 4 Rooms and realtime API
- [ ] 5 Durable games  <- NEXT
- [ ] 6 Rate limits and abuse protection
- [ ] 7 Design review gate
- [ ] 8 Frontend foundation and lobby
- [ ] 9 Drawing canvas component
- [ ] 10 Gameplay screens
- [ ] 11 Reveal and finished screen
- [ ] 12 End-to-end tests
- [ ] 13 Packaging
- [ ] 14 Terraform for GCP
- [ ] 15 Bootstrap
- [ ] 16 CD pipelines
- [ ] 17 Live verification and docs

## What exists
- Repo `Ryhhill1998/telephone-doodle` (public). Personal-repo commits use the GitHub noreply identity, never the work email.
- Python 3.15 (uv), Node 26 LTS (`frontend/.nvmrc`), Postgres 19 (`make db`). Frontend lint is oxlint. Test client is `httpx2`. pytest runs with `-W error`. Backend tests need `make db` running.
- `game_engine/` is pure and complete: models and limits (`MIN_PLAYERS`, `MAX_PLAYERS`, `MAX_NAME_LENGTH`, `MAX_TEXT_LENGTH` in `models.py`), `WordBank`, rules, `view_for`, `to_dict`/`from_dict`. Host index and "has submitted" are derived. The host cannot be kicked. Only the host can move the reveal pointer.
- `storage/` (Step 3 PR): `Database` object wrapping the async pool; `create_game(code)`, `save_snapshot(id, status, snapshot, expected_version, host_idx, player_count)`, `load_game(code)`, `finish_game(id, players, books, pages)`, `RoomCodeTaken` (code generator must catch and retry). `main.py` has a lifespan that opens the pool and creates the schema; pool is on `app.state`.
- Import-linter config is in `backend/pyproject.toml`; a new package must be added to `root_packages`.
- `rooms/` (Step 4 PR): `RoomManager` with 4-letter room codes, join/token mapping, connection registry, per-player `state` broadcast after every change, 6h inactive-room cleanup; structured JSON event logging in `rooms/events.py`.
- `api/` (Step 4 PR): HTTP routes (`api/http.py`) and the WebSocket route (`api/ws.py`), Pydantic message schemas in `api/schemas.py`. Routes are thin and call into `rooms`.
- `settings.py`: `Settings` (pydantic-settings, `ALLOWED_ORIGINS`) with a cached `get_settings()` function injected via FastAPI's `Depends`; CORS and the WebSocket `Origin` check both read `allowed_origins`.

## Open proposals (agreed in principle, not yet applied to the step files)
- Step 6: raise the per-IP concurrent WebSocket cap from 20 to 40.
- Step 14: `ALLOWED_ORIGINS` needs both `https://<project>.web.app` and `https://<project>.firebaseapp.com`. Also at the start of Step 14: re-verify the free-tier figures from Step 0b, upgrade Terraform, and add `Makefile` and `ci.yml` to the infra path filter.
- Step 14/15: Step 15 will fail its first `terraform apply` as written (Cloud Run needs a secret version that is only added in 15.4). Use a two-pass bootstrap: apply everything except the Cloud Run service, add the secret version by hand, then apply again.
