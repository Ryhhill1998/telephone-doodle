"""The thin FastAPI layer: HTTP routes, the WebSocket handler, and the request,
response and message schemas, validated with Pydantic (BUILD_PLAN.md, section
2). Everything here calls into `rooms`; nothing here touches `game_engine` or
`storage` directly.
"""

from fastapi import APIRouter

from api.http import router as _http_router
from api.ws import router as _ws_router

router = APIRouter()
router.include_router(_http_router)
router.include_router(_ws_router)

__all__ = ["router"]
