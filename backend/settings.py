"""Environment-based configuration.

One place for the handful of values that differ between dev and production
(BUILD_PLAN.md, section 2's repo layout). Everything is read from the
environment and nothing is guessed: there is no default list of origins,
because a wrong guess there would either lock out the real frontend or open
the API to every site on the internet.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Self

__all__ = ["Settings"]


@dataclass(frozen=True)
class Settings:
    """`ALLOWED_ORIGINS` and nothing else, for now.

    `None` means "unset" -- permissive, for local dev where the frontend talks
    to the API through Vite's proxy and there is no real cross-origin request
    to check. Production always sets it, so a dev-only default never ships.
    """

    allowed_origins: tuple[str, ...] | None

    @classmethod
    def from_env(cls) -> Self:
        raw = os.environ.get("ALLOWED_ORIGINS")
        if raw is None:
            return cls(allowed_origins=None)
        origins = tuple(origin.strip() for origin in raw.split(",") if origin.strip())
        return cls(allowed_origins=origins)

    def allows_origin(self, origin: str | None) -> bool:
        """Whether a WebSocket's `Origin` header may connect.

        CORS protects browsers reading HTTP responses and is handled by
        `CORSMiddleware`; WebSocket upgrades are not covered by CORS at all, so
        the server has to check this itself (BUILD_PLAN.md, section 3).
        """
        if self.allowed_origins is None:
            return True
        return origin is not None and origin in self.allowed_origins

    @property
    def cors_origins(self) -> list[str]:
        """What to hand `CORSMiddleware`: the list, or `"*"` when unset."""
        return ["*"] if self.allowed_origins is None else list(self.allowed_origins)
