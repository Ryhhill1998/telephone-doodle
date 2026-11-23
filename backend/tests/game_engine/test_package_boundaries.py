"""Guards what `game_engine` is allowed to depend on.

The *layering* between packages (`api` -> `rooms` -> `game_engine`, BUILD_PLAN.md
section 2) is enforced by import-linter, configured in `pyproject.toml` and run
by `make backend-lint`. It reads the real import graph, so it also catches
indirect chains, which a per-file check cannot.

What is left here is the part no import linter can express:

- `game_engine` must import from a short **allowlist** and nothing else. Every
  contract import-linter offers is a denylist, which only ever catches the
  modules somebody thought to name: banning `time` but forgetting `datetime`
  reads as a passing purity check while a clock sits in the rules. Inverting it
  means a new dependency has to be argued for in this file instead of slipping
  in unnoticed.
- Randomness must be injected rather than taken from the global generator. That
  is a rule about a *call*, not an import, so it is out of scope for any tool
  that works on the import graph.
"""

import ast
import tomllib
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
PACKAGE = BACKEND / "game_engine"

# Everything `game_engine` may import. Pure stdlib and itself: no clock, no
# filesystem beyond the one concession below, no third-party anything, and none
# of the sibling packages, which sit above it in the dependency order.
#
# `json` and `importlib` are the concession: the package ships words.json and
# load_words() reads it through importlib.resources. Purity is preserved where
# it counts, because WordBank takes its vocabulary as an argument and the tests
# build one from a literal list.
ALLOWED_IMPORTS = {
    "__future__",
    "collections",
    "dataclasses",
    "enum",
    "game_engine",
    "importlib",
    "json",
    "random",
    "typing",
}


def source_files() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def parsed(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_roots(path: Path) -> set[str]:
    """Top-level module name of every import in the file."""
    roots: set[str] = set()
    for node in ast.walk(parsed(path)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_there_is_something_to_check() -> None:
    """Stops this file quietly passing if the package is ever moved."""
    assert source_files(), f"no modules found under {PACKAGE}"


@pytest.mark.parametrize("path", source_files(), ids=lambda p: p.name)
def test_game_engine_imports_only_the_allowlist(path: Path) -> None:
    offenders = imported_roots(path) - ALLOWED_IMPORTS

    assert not offenders, (
        f"{path.name} imports {sorted(offenders)}, which is not on game_engine's "
        "allowlist. The package holds the rules and nothing else: no I/O, no clock, "
        "no framework, and nothing from the packages above it. If the import really "
        "belongs here, add it to ALLOWED_IMPORTS and say why."
    )


def test_randomness_is_injected_never_global() -> None:
    """`random.shuffle` and friends share one global generator.

    A module reaching for those could not be replayed from a seed, so they are
    banned. `random.Random` is the exception and the point: constructing a
    dedicated generator is what injected randomness means. Allowlisting exactly
    one name means any other function added to `random` is caught by default.
    """
    for path in source_files():
        for node in ast.walk(parsed(path)):
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


def test_import_linter_covers_every_package() -> None:
    """import-linter can only check packages named as roots.

    A package left out of `root_packages` is simply absent from the graph, so
    its contracts pass by having nothing to say. This fails the moment a step
    adds `rooms/` or `storage/` without listing it, which is the only way the
    layering contract can quietly stop meaning anything.
    """
    config = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    configured = set(config["tool"]["importlinter"]["root_packages"])
    on_disk = {d.name for d in BACKEND.iterdir() if (d / "__init__.py").exists()}

    assert on_disk == configured, (
        f"pyproject.toml lists {sorted(configured)} as import-linter root packages but "
        f"the backend has {sorted(on_disk)}. Add the missing ones and place them in the "
        "layers contract, or the layering stops being checked for them."
    )
