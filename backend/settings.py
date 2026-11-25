"""Environment-based configuration.

One place for the handful of values that differ between dev and production
(BUILD_PLAN.md, section 2's repo layout). `pydantic-settings` reads everything
from the environment; there is no default list of origins, because a wrong
guess there would either lock out the real frontend or open the API to every
site on the internet.
"""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode

__all__ = ["Settings"]


class Settings(BaseSettings):
    """`ALLOWED_ORIGINS` and nothing else, for now.

    `None` means "unset" -- permissive, for local dev where the frontend talks
    to the API through Vite's proxy and there is no real cross-origin request
    to check. Production always sets it, so a dev-only default never ships.
    """

    allowed_origins: Annotated[tuple[str, ...] | None, NoDecode] = None

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: str | tuple[str, ...] | None) -> tuple[str, ...] | None:
        """`ALLOWED_ORIGINS` is a comma-separated string, not JSON, so the
        default env decoding (which expects JSON for non-primitive types) is
        skipped via `NoDecode` and the splitting done here instead."""
        if value is None or isinstance(value, tuple):
            return value
        origins = tuple(origin.strip() for origin in value.split(",") if origin.strip())
        return origins or None

    @classmethod
    def from_env(cls) -> Self:
        return cls()

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
