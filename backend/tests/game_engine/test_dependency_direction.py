"""Guards the dependency direction and purity of `game_engine`.

BUILD_PLAN.md section 2 says `api` calls `rooms`; `rooms` calls `game_engine`
and `storage`; and `game_engine` imports nothing from the other packages. The
review checklist for Step 2 adds that it must stay free of I/O so it is
trivially unit-testable.

A lint rule cannot express "only in this directory", so the rule lives here as
a test instead, where it is visible and fails with an explanation.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "game_engine"

SIBLING_PACKAGES = {"api", "rooms", "storage", "main", "settings"}

# Anything that reaches the network, a database, a socket, a clock or a
# subprocess. `json` and `importlib.resources` are absent on purpose: the
# package reads its own bundled words.json once, which is the single
# concession, confined to load_words().
IO_MODULES = {
    "asyncio",
    "fastapi",
    "httpx",
    "logging",
    "os",
    "psycopg",
    "pydantic",
    "requests",
    "socket",
    "starlette",
    "subprocess",
    "threading",
    "time",
    "urllib",
    "uvicorn",
}


def source_files() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def imported_roots(path: Path) -> set[str]:
    """Top-level module name of every import in the file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_there_is_something_to_check() -> None:
    """Stops this file quietly passing if the package is ever moved."""
    assert source_files(), f"no modules found under {PACKAGE}"


@pytest.mark.parametrize("path", source_files(), ids=lambda p: p.name)
def test_game_engine_does_not_import_sibling_packages(path: Path) -> None:
    offenders = imported_roots(path) & SIBLING_PACKAGES

    assert not offenders, (
        f"{path.name} imports {sorted(offenders)}. game_engine sits at the bottom "
        "of the dependency order: rooms calls it, it calls nobody."
    )


@pytest.mark.parametrize("path", source_files(), ids=lambda p: p.name)
def test_game_engine_does_not_import_io(path: Path) -> None:
    offenders = imported_roots(path) & IO_MODULES

    assert not offenders, (
        f"{path.name} imports {sorted(offenders)}. game_engine must stay pure so the "
        "rules can be tested without a database, a socket or a clock."
    )


def test_randomness_is_injected_never_global() -> None:
    """`random.shuffle` and friends share one global generator.

    A module reaching for those could not be replayed from a seed, so they are
    banned. `random.Random` is the exception and the point: constructing a
    dedicated generator is what injected randomness means. Allowlisting exactly
    one name means any other function added to `random` is caught by default.
    """
    for path in source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "random"
                and node.func.attr != "Random"
            ):
                pytest.fail(
                    f"{path.name} calls random.{node.func.attr}() on the global generator; "
                    "take a random.Random argument instead"
                )
