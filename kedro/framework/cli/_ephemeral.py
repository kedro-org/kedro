"""Helper for ephemeral re-execution when optional tools are missing."""

from __future__ import annotations

import functools
import importlib.util
import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def _have_all(modules: list[str]) -> bool:
    """Check if all required modules are importable."""
    return all(importlib.util.find_spec(m) for m in modules)


def ensure_or_ephemeral(required_modules: list[str], argv: list[str]) -> None:
    """If any required module is missing, re-exec the CLI via uvx ephemerally.

    Args:
        required_modules: List of module names to check (e.g., ["cookiecutter", "git"])
        argv: Command-line arguments (sys.argv)

    Raises:
        SystemExit: If deps are missing and fallback is not possible/allowed
    """
    if _have_all(required_modules):
        return  # All tools available, proceed normally

    # Missing tools - check if ephemeral fallback is allowed
    if os.environ.get("KEDRO_NO_UVX_FALLBACK"):
        miss = [m for m in required_modules if not importlib.util.find_spec(m)]
        raise SystemExit(
            "Missing tools: " + ", ".join(miss) + "\n"
            "Install locally, e.g.:\n"
            f"  pip install {' '.join(miss)}\n"
            "Or unset KEDRO_NO_UVX_FALLBACK to allow ephemeral fallback."
        )

    # Check if uvx is available
    if not shutil.which("uvx"):
        raise SystemExit(
            "Missing tools and no uvx found.\n"
            "Install tools locally OR install uv:\n"
            "  pip install uv"
        )

    # Prevent infinite loop if uvx re-exec fails
    if os.environ.get("KEDRO_UVX_REEXEC") == "1":
        raise SystemExit("uvx re-exec loop detected; aborting.")

    # Re-execute via uvx
    env = {**os.environ, "KEDRO_UVX_REEXEC": "1"}
    cmd = ["uvx", "--from", "kedro[create]", "kedro", *argv[1:]]
    print(
        "🔧 Missing tools — running ephemerally via uvx:\n  ",
        " ".join(cmd),
        file=sys.stderr,
    )
    raise SystemExit(subprocess.call(cmd, env=env))


def ephemeral_if_missing(modules: list[str]) -> Callable:
    """Decorator for Click commands that need extra tooling.

    Args:
        modules: List of module names required (e.g., ["cookiecutter", "git"])

    Returns:
        Decorator function

    Example:
        @cli.command()
        @ephemeral_if_missing(["cookiecutter", "git"])
        def new(...):
            ...
    """

    def deco(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            ensure_or_ephemeral(modules, sys.argv)
            return func(*args, **kwargs)

        return wrapper

    return deco
