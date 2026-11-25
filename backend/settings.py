"""Environment-based configuration.

One place for the handful of values that differ between dev and production.
`pydantic-settings` reads everything from the environment; there is no default
list of origins, because a wrong guess there would either lock out the real
frontend or open the API to every site on the internet.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode

__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    """`ALLOWED_ORIGINS` and nothing else, for now.

    `None` means "unset" -- permissive, for local dev where the frontend talks
    to the API through Vite's proxy and there is no real cross-origin request
    to check. Production always sets it, so a dev-only default never ships.
    """

    allowed_origins: Annotated[frozenset[str] | None, NoDecode] = None

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: str | frozenset[str] | None) -> frozenset[str] | None:
        """`ALLOWED_ORIGINS` is a comma-separated string, not JSON, so the
        default env decoding (which expects JSON for non-primitive types) is
        skipped via `NoDecode` and the splitting done here instead."""
        if value is None or isinstance(value, frozenset):
            return value
        origins = frozenset(origin.strip() for origin in value.split(",") if origin.strip())
        return origins or None

    @property
    def cors_origins(self) -> list[str]:
        """What to hand `CORSMiddleware`: the list, or `"*"` when unset."""
        return ["*"] if self.allowed_origins is None else list(self.allowed_origins)


@lru_cache
def get_settings() -> Settings:
    """The app's one `Settings` instance (FastAPI's standard settings pattern:
    https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru_cache).

    `pydantic-settings` builds it straight from the environment, so `lru_cache`
    is the only reason this is a function and not just `Settings()` at every
    call site -- one instance, built once, reused by `Depends(get_settings)`.
    """
    return Settings()
