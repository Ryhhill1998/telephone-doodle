> Suggested reading (in docs/plan/): 01-product-spec.md; 03-architecture.md

### Step 12. End-to-end tests

Branch `feat/e2e`.

Playwright tests in `frontend/e2e/` that drive the real UI against the real backend and a real Postgres, with **three browser contexts as three players** (the only way to test what no unit test can: the canvas, the sockets and the multi-player sync together).

- `make e2e` starts Postgres (`make db`), the backend and the frontend (production build served locally), then runs Playwright. Use the latest stable Playwright and Chromium; add a WebKit project too if it is cheap, because iOS Safari is the riskiest browser for drawing.
- **Scenarios:** (1) full 3-player game: create room, join with code, shuffle seat order and check all three lobbies show the same order, start, pick a word (and check the three players' dealt options are all different), draw with pointer events (brush and fill), submit, guess, run through every round, reveal where the host's Next moves all three screens together and a non-host has no buttons, finish; (2) refresh a non-host mid-round (seat, word and draft drawing come back) and mid-reveal (lands on the current page); (3) host removes a player in the lobby (that player sees the removal message and the others' lists update); (4) restart the backend process mid-game and check the clients reconnect and the game continues; (5) a 429 from the rate limiter shows the friendly message.
- Keep the suite fast (aim for under about 3 minutes) and stable: no fixed sleeps, use Playwright's auto-waiting, retries only in CI and capture traces on failure.
- Add the `e2e` job to `ci.yml` (runs when backend or frontend changed; uploads the Playwright report on failure) and the `make e2e` target.

**Review checklist:** `make e2e` passes locally on a clean checkout and in CI; each scenario above exists; no flaky retries needed locally.

---
