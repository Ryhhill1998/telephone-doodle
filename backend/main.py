"""Telephone Doodle API.

The FastAPI application. HTTP routes and the WebSocket handler move into `api/`
from Step 4 onward; for now this module only exposes the health check.
"""

from fastapi import FastAPI

app = FastAPI(title="Telephone Doodle API")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness and startup probe.

    Deliberately does not touch the database. Neon's free-plan compute suspends
    after five minutes idle, and a probe that woke it would make a sleeping
    database able to fail a deploy (BUILD_PLAN.md, section 3).
    """
    return {"status": "ok"}
