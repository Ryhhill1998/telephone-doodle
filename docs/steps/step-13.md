> Suggested reading (in docs/plan/): 02-locked-decisions.md

### Step 13. Packaging

Branch `chore/packaging`.

- `backend/Dockerfile` (API only): multi-stage if useful; the official `python` slim image at the same Python version as `.python-version` (verify the tag exists), install deps with `uv` from the lockfile, run as non-root. Command: `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*' --timeout-graceful-shutdown 8`. Add the `org.opencontainers.image.source` label pointing at the repo. Keep the image small.
- `frontend/firebase.json`: hosting `public` is `dist`; rewrite `**` to `/index.html`; long-lived immutable cache headers for `/assets/**` (hashed filenames) and `no-cache` for `index.html`.
- `frontend/.env.production.example` documenting `VITE_API_URL`.
- Local full-stack check: `make db`, the API container pointed at that Postgres, and the Vite dev server (or a production build served locally) pointed at the container.

**Review checklist:** `docker build` works from a clean checkout and the container passes a full multi-tab game against local Postgres; the container stops cleanly on SIGTERM within 10 seconds; image size reported in the PR.

---
