"""Safe context for loading Kedro projects without optional dependencies (lite mode)."""

from __future__ import annotations

import ast
import importlib.machinery
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator


def _collect_imports_from_file(file_path: Path) -> set[str]:
    """Parse a Python file and collect full import module names (like LiteParser).

    For \"from sklearn.base import BaseEstimator\" we collect \"sklearn.base\", not
    just \"sklearn\", so that submodules can be registered in sys.modules and
    the import succeeds without the import system trying to load them.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if not name.startswith("_"):
                    modules.add(name)
        elif isinstance(node, ast.ImportFrom):
            # Only collect absolute imports (level 0). Relative imports (e.g. "from .nodes import x")
            # have node.module "nodes" but level 1; we must not mock "nodes" as a dependency.
            if node.module and not node.module.startswith("_") and node.level == 0:
                modules.add(node.module)
    return modules


def _collect_pipeline_imports(project_path: Path, package_name: str) -> set[str]:
    """
    AST-scan pipeline Python files under project_path for import names.
    Looks for src/<package>/pipelines/**/*.py and src/<package>/pipeline.py.
    """
    project_path = Path(project_path).resolve()
    # Try common layout: pyproject.toml has source_dir (e.g. "src")
    pyproject = project_path / "pyproject.toml"
    source_dir = project_path / "src"
    if pyproject.exists():
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore
            with pyproject.open("rb") as f:
                data = tomllib.load(f)
            sd = data.get("tool", {}).get("kedro", {}).get("source_dir", "src")
            source_dir = (project_path / sd).resolve()
        except Exception as e:
            logging.getLogger(__name__).debug(
                "Could not read source_dir from pyproject.toml: %s", e
            )
    if not source_dir.exists():
        source_dir = project_path
    package_dir = source_dir / package_name
    all_imports: set[str] = set()
    # Single pipeline module
    pipeline_py = package_dir / "pipeline.py"
    if pipeline_py.exists():
        all_imports |= _collect_imports_from_file(pipeline_py)
    # pipelines/ package
    pipelines_dir = package_dir / "pipelines"
    if pipelines_dir.is_dir():
        for path in pipelines_dir.rglob("*.py"):
            if path.name.startswith("_"):
                continue
            all_imports |= _collect_imports_from_file(path)
    return all_imports


def _get_missing_modules(candidate_imports: set[str]) -> set[str]:
    """Return every module part that is not already in sys.modules (like LiteParser).

    For each candidate full name (e.g. \"sklearn.base\"), we add each part that is
    missing (e.g. \"sklearn\", \"sklearn.base\") so we can register all of them
    in sys.modules and avoid ModuleNotFoundError for submodules.
    """
    missing: set[str] = set()
    for full_name in candidate_imports:
        for part in _get_module_parts(full_name):
            if part not in sys.modules:
                missing.add(part)
    return missing


def _get_module_parts(module_name: str) -> list[str]:
    """Return progressively longer module parts, e.g. 'sklearn.base' -> ['sklearn', 'sklearn.base']."""
    parts = module_name.split(".")
    return [".".join(parts[: i + 1]) for i in range(len(parts))]


def _create_mock_modules(module_names: set[str]) -> dict[str, MagicMock]:
    """Build a dict of MagicMock for each module name (and parent packages).

    Parent modules are given __path__=[] so Python treats them as packages and
    submodule imports like \"from sklearn.base import BaseEstimator\" succeed.
    All mocks get __spec__ so the import system does not raise AttributeError
    when loading submodules (e.g. sklearn.base).
    """
    result: dict[str, MagicMock] = {}
    for name in sorted(module_names):
        name_parts = _get_module_parts(name)
        for part in name_parts:
            if part in result:
                continue
            # Any module that has a submodule in our set must be a package.
            # Also treat top-level mocks as packages so "from sklearn.base import ..." works
            # even when we only collected "sklearn" (no "sklearn.base" in module_names).
            has_submodules = any(
                p != part and p.startswith(part + ".") for p in module_names
            )
            is_toplevel = "." not in part
            is_package = has_submodules or is_toplevel
            mock = MagicMock(__path__=[]) if is_package else MagicMock()
            # Import system expects __spec__ on modules; MagicMock can raise
            # AttributeError for __spec__ otherwise when loading submodules.
            mock.__spec__ = importlib.machinery.ModuleSpec(
                part, None, is_package=is_package
            )
            result[part] = mock
    return result


@contextmanager
def safe_context(
    project_path: Path | str, package_name: str
) -> Generator[set[str], None, None]:
    """
    Context manager that mocks missing heavy dependencies so that
    Kedro session loading and config resolution succeed without them.

    Only patches sys.modules. Use config_resolver.resolve_pattern() for dataset
    info (no materialization). Do not call catalog.get() inside this context.

    Usage:
        with safe_context(project_path, package_name) as missing_deps:
            session = KedroSession.create(project_path=project_path)
            with session as s:
                context = s.load_context()
                catalog = context.catalog

    Yields:
        Set of module names that were mocked (e.g. {"pandas", "sklearn"}).
    """
    project_path = Path(project_path).resolve()
    candidate_imports = _collect_pipeline_imports(project_path, package_name)
    # Skip stdlib, kedro, and the project package (so we don't mock demo_project.* and
    # shadow the real package when import_module("demo_project.pipeline_registry") runs).
    skip_prefixes = (
        "kedro",
        "importlib",
        "pathlib",
        "typing",
        "collections",
        "json",
        "yaml",
        package_name,
    )
    candidates = {
        n
        for n in candidate_imports
        if not any(n == p or n.startswith(p + ".") for p in skip_prefixes)
    }
    missing_modules = _get_missing_modules(candidates)
    sys_patch = dict(sys.modules)
    if missing_modules:
        mock_modules = _create_mock_modules(missing_modules)
        sys_patch.update(mock_modules)
    with patch.dict("sys.modules", sys_patch, clear=False):
        yield missing_modules
