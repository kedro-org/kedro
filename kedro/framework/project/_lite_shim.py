"""Dependency-free shim for loading pipeline structure without optional project deps.

When inspection-only CLI commands (``kedro registry list``, ``kedro registry describe``)
are run and heavy project dependencies (sklearn, torch, seaborn, …) are not installed,
this module mocks those missing packages in ``sys.modules`` before the pipeline registry
is imported. The pipeline structure (node names, inputs, outputs) becomes available
without executing any node functions or requiring the missing packages to be installed.

Scope: this shim is only safe to use when no node code will be executed. Never wrap
a ``kedro run`` inside ``safe_context`` — mocked packages produce garbage output at
runtime.
"""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

log = logging.getLogger(__name__)

# Prefixes that must never be mocked: Kedro internals, the project package itself
# (passed at call time), and a handful of always-required stdlib/deps.
# Standard library modules are implicitly safe: they are always in sys.modules at
# Python startup and are therefore filtered out by _get_missing_modules().
_ALWAYS_SKIP_PREFIXES = (
    "kedro",
    "importlib",
    "pathlib",
    "typing",
    "collections",
    "json",
    "yaml",
    "abc",
    "functools",
)


def _collect_imports_from_source(source: str) -> set[str]:
    """AST-parse Python source and return all absolute import module names.

    Only absolute imports (``import X`` / ``from X import Y``, level==0) are
    collected. Relative imports (``from .nodes import train_model``, level>0)
    are project-internal and must never be mocked.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.startswith("_"):
                    modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and not node.module.startswith("_") and node.level == 0:
                modules.add(node.module)
    return modules


def _get_module_parts(module_name: str) -> list[str]:
    """Return progressively longer dotted parts.

    Example: ``'sklearn.base'`` → ``['sklearn', 'sklearn.base']``.
    Required so that both the top-level package and every submodule referenced
    in an import are registered in sys.modules.
    """
    parts = module_name.split(".")
    return [".".join(parts[: i + 1]) for i in range(len(parts))]


def _collect_pipeline_imports(package_name: str) -> set[str]:
    """Find and AST-scan all pipeline ``.py`` files for the given package.

    Locates the package directory via ``importlib.util.find_spec`` (no module
    code is executed), then walks ``pipelines/**/*.py`` and ``pipeline.py``
    collecting absolute import module names.
    """
    spec = importlib.util.find_spec(package_name)
    if spec is None or not spec.submodule_search_locations:
        return set()

    all_imports: set[str] = set()
    for location in spec.submodule_search_locations:
        package_dir = Path(location)

        # Modular pipelines layout: src/<pkg>/pipelines/**/*.py
        pipelines_dir = package_dir / "pipelines"
        if pipelines_dir.is_dir():
            for path in pipelines_dir.rglob("*.py"):
                if path.name.startswith("_"):
                    continue
                try:
                    source = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                all_imports |= _collect_imports_from_source(source)

        # Single-file layout: src/<pkg>/pipeline.py
        pipeline_py = package_dir / "pipeline.py"
        if pipeline_py.is_file():
            try:
                source = pipeline_py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                pass
            else:
                all_imports |= _collect_imports_from_source(source)

    return all_imports


def _get_missing_modules(candidate_imports: set[str], package_name: str) -> set[str]:
    """Return the subset of *candidate_imports* that are absent from ``sys.modules``.

    Filters out:
    - Known-safe prefixes (Kedro, stdlib shorthands, ``package_name`` itself).
    - Anything already present in ``sys.modules`` — stdlib is always there at
      startup, so this implicitly protects ``os``, ``re``, ``datetime``, etc.
    """
    skip_prefixes = (*_ALWAYS_SKIP_PREFIXES, package_name)
    missing: set[str] = set()
    for full_name in candidate_imports:
        if any(full_name == p or full_name.startswith(p + ".") for p in skip_prefixes):
            continue
        for part in _get_module_parts(full_name):
            if part not in sys.modules:
                missing.add(part)
    return missing


def _create_mock_modules(module_names: set[str]) -> dict[str, MagicMock]:
    """Build ``MagicMock`` stubs for each module name and all its parent packages.

    Parent packages receive ``__path__=[]`` so the import system treats them as
    packages and submodule imports like ``from sklearn.base import BaseEstimator``
    succeed. All mocks receive ``__spec__`` so the import system does not raise
    ``AttributeError`` when loading submodules.
    """
    result: dict[str, MagicMock] = {}
    for name in sorted(module_names):
        for part in _get_module_parts(name):
            if part in result:
                continue
            is_package = "." not in part or any(
                p != part and p.startswith(part + ".") for p in module_names
            )
            mock = MagicMock(__path__=[]) if is_package else MagicMock()
            mock.__spec__ = importlib.machinery.ModuleSpec(
                part, None, is_package=is_package
            )
            result[part] = mock
    return result


@contextmanager
def safe_context(package_name: str) -> Generator[frozenset[str], None, None]:
    """Mock missing heavy project dependencies so pipeline registry loading succeeds.

    1. AST-scans all pipeline source files to collect absolute import names.
    2. Filters to those absent from ``sys.modules`` (genuinely missing packages).
    3. Pre-populates ``sys.modules`` with ``MagicMock`` stubs for the duration
       of the ``with`` block.
    4. Restores ``sys.modules`` exactly on exit via ``patch.dict``.

    Only safe for inspection commands that never execute node functions. Do not
    use this context during ``kedro run``.

    Args:
        package_name: The project's Python package name (e.g. ``"my_project"``).

    Yields:
        ``frozenset`` of module names that were mocked (e.g. ``{"seaborn", "sklearn"}``).
    """
    candidate_imports = _collect_pipeline_imports(package_name)
    missing_modules = _get_missing_modules(candidate_imports, package_name)

    if missing_modules:
        log.debug(
            "Mocking %d missing project dependency/dependencies for inspection: %s",
            len(missing_modules),
            sorted(missing_modules),
        )

    mock_modules = _create_mock_modules(missing_modules) if missing_modules else {}
    with patch.dict("sys.modules", mock_modules, clear=False):
        yield frozenset(missing_modules)
