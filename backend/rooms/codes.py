"""Room codes: four letters, none of them ambiguous.

`O`/`0` and `I`/`1` are excluded so a code read aloud or copied by hand never
has to be second-guessed (BUILD_PLAN.md, Step 4). Uniqueness among games still
being played is enforced by Postgres's partial unique index
(`storage.ACTIVE_CODE_INDEX`); this module only produces candidates.
"""

from __future__ import annotations

import secrets

__all__ = ["ALPHABET", "CODE_LENGTH", "generate_code"]

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LENGTH = 4


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
