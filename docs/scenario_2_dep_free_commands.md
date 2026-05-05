# Scenario 2 — CLI Commands Without Project Dependencies

**Part of spike [#5406](https://github.com/kedro-org/kedro/issues/5406) · [← Scenario 1](scenario_1_selective_loading.md) · [← Overview](on_demand_dependency_loading.md)**

**Goal:** Read-only CLI commands (`kedro registry list`, `kedro registry describe`, `kedro catalog describe-datasets`, inspection API) should function even when heavy project dependencies (sklearn, torch, seaborn) are not installed.

---

## Why This Is Hard

The import chain fires before any framework filter can intervene:

```
pipeline_registry.py
  → from my_project.pipelines.reporting import create_pipeline
  → reporting/pipeline.py
  → from .nodes import train_model
  → reporting/nodes.py
  → import seaborn          ← ModuleNotFoundError here
```

There is no hook between "load the pipeline registry" and "import seaborn" that the framework can exploit without changing user code.

---

## Solution — `lite_shim`: AST Scan + `sys.modules` Mock

Stub the **missing dependency itself** before any pipeline code is loaded. When `nodes.py` runs `import seaborn`, Python checks `sys.modules["seaborn"]` first — if a mock is already there, the import is a no-op. The pipeline loads, `create_pipeline()` runs, the `Pipeline` structure is fully populated, and seaborn is never executed.

### Step 1 — AST-scan pipeline source files

Parse every `pipelines/**/*.py` file and collect all **absolute** import names. Relative imports (`from .nodes import train_model`, `level > 0`) are explicitly excluded — they are project-internal and must never be mocked.

```python
def _collect_imports_from_file(file_path: Path) -> set[str]:
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.startswith("_"):
                    modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # level==0 means absolute import; skip relative imports (level > 0)
            if node.module and not node.module.startswith("_") and node.level == 0:
                modules.add(node.module)
    return modules
```

### Step 2 — Filter to genuinely missing modules

Check each candidate against `sys.modules`. Standard library modules (`os`, `re`, `datetime`, `functools`, …) are always loaded at Python startup and are always in `sys.modules` — they are filtered out implicitly. Only truly absent third-party packages remain.

```python
def _get_missing_modules(candidate_imports: set[str]) -> set[str]:
    missing: set[str] = set()
    for full_name in candidate_imports:
        for part in _iter_parts(full_name):   # e.g. "sklearn.base" → ["sklearn", "sklearn.base"]
            if part not in sys.modules:
                missing.add(part)
    return missing
```

Kedro's own packages (`kedro`, the project package itself) and known required deps (`yaml`) are excluded by a skip-list before this check, so they are never candidates for mocking.

### Step 3 — Pre-populate `sys.modules` with `MagicMock`

`MagicMock` is used rather than a plain `types.ModuleType` because it handles transitive attribute access automatically — `seaborn.lineplot(...)`, `torch.nn.Linear(10, 10)`, `sklearn.preprocessing.StandardScaler()` all return further `MagicMock` instances without raising `AttributeError`. Parent packages are given `__path__=[]` so the import system treats them as packages and submodule imports like `from sklearn.base import BaseEstimator` succeed.

```python
def _create_mock_modules(module_names: set[str]) -> dict[str, MagicMock]:
    result: dict[str, MagicMock] = {}
    for name in sorted(module_names):
        for part in _iter_parts(name):
            if part in result:
                continue
            is_package = "." not in part or any(
                p != part and p.startswith(part + ".") for p in module_names
            )
            mock = MagicMock(__path__=[]) if is_package else MagicMock()
            mock.__spec__ = importlib.machinery.ModuleSpec(part, None, is_package=is_package)
            result[part] = mock
    return result
```

### Step 4 — Scope with `patch.dict`

`unittest.mock.patch.dict` installs the mocks and restores `sys.modules` exactly to its prior state on exit. No manual cleanup loop required.

```python
@contextmanager
def safe_context(
    project_path: Path | str, package_name: str
) -> Generator[set[str], None, None]:
    candidate_imports = _collect_pipeline_imports(project_path, package_name)
    skip_prefixes = ("kedro", "importlib", "pathlib", "typing",
                     "collections", "json", "yaml", package_name)
    candidates = {
        n for n in candidate_imports
        if not any(n == p or n.startswith(p + ".") for p in skip_prefixes)
    }
    missing_modules = _get_missing_modules(candidates)
    mock_modules = _create_mock_modules(missing_modules) if missing_modules else {}
    with patch.dict("sys.modules", {**sys.modules, **mock_modules}, clear=False):
        yield missing_modules
```

---

## Integration Points

`safe_context` should wrap the `register_pipelines()` call inside `_load_data()` when the command is inspection-only (no runner active):

```python
# kedro/framework/project/__init__.py
def _load_data(self) -> None:
    if self._pipelines_module is None or self._is_data_loaded:
        return

    if self._inspection_mode:
        ctx = safe_context(PROJECT_PATH, PACKAGE_NAME)
    else:
        ctx = contextlib.nullcontext(set())

    with ctx as mocked_deps:
        register_pipelines = self._get_pipelines_registry_callable(
            self._pipelines_module
        )
        project_pipelines = register_pipelines()

    self._content = project_pipelines
    self._mocked_dependencies = mocked_deps
    self._is_data_loaded = True
```

CLI commands that are inspection-only (`registry list`, `registry describe`, `catalog describe-datasets`) set `inspection_mode=True` before triggering `_load_data()`. Run commands never set it.

---

## Alternative Considered — `sys.meta_path` Catch-All Stub Finder

The `lite_shim` approach above is *proactive*: it scans first, then mocks what it predicts will be missing. A well-known alternative used by Sphinx is *reactive*: install a fallback finder that only fires for modules no other finder can locate.

### How it works

Python resolves every `import` statement by walking `sys.meta_path` in order. Each finder's `find_spec` is called; if it returns `None` the next finder is tried. Only when every finder returns `None` is `ModuleNotFoundError` raised.

Appending a stub finder to the **end** of `sys.meta_path` makes it a last-resort fallback — stdlib and installed packages are found by the normal finders and load without interference. Only truly absent packages fall through to the stub:

```python
import sys
import contextlib
import importlib.abc
import importlib.machinery
from types import ModuleType


class _MockObject:
    """Absorbs any attribute access or call on a mocked dependency."""
    def __getattr__(self, key):
        return _MockObject()
    def __call__(self, *args, **kwargs):
        return _MockObject()
    def __class_getitem__(cls, item):  # handles generics: List[MockObject]
        return cls


class _MockModule(ModuleType):
    def __getattr__(self, key):
        return _MockObject()


class _CatchAllFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Stub finder appended to sys.meta_path as a catch-all fallback.

    Returns a _MockModule for any name that all preceding finders rejected.
    Because it is appended (not inserted at 0), real modules are unaffected.
    """

    def find_spec(self, fullname, path, target=None):
        return importlib.machinery.ModuleSpec(fullname, self, is_package=True)

    def create_module(self, spec):
        return _MockModule(spec.name)

    def exec_module(self, module):
        pass  # skip all module-level code — the mock handles attribute access


@contextlib.contextmanager
def safe_context_v2():
    finder = _CatchAllFinder()
    sys.meta_path.append(finder)   # append = fallback only, does not shadow real modules
    try:
        yield
    finally:
        sys.meta_path.remove(finder)
```

Usage is identical to `safe_context` from the AST-scan approach:

```python
with safe_context_v2():
    register_pipelines = _get_pipelines_registry_callable(pipelines_module)
    project_pipelines = register_pipelines()
```

### Prior Usage

This is the same mechanism that several major Python tools ship in production:

- **Sphinx `autodoc_mock_imports`** ([source](https://github.com/sphinx-doc/sphinx/blob/master/sphinx/ext/autodoc/mock.py), [docs](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_mock_imports)) — `MockFinder` / `MockLoader` are inserted into `sys.meta_path` around each autodoc import. Sphinx ships this specifically to generate API documentation for libraries whose optional heavy dependencies (e.g. `torch`, `tensorflow`) are not installed in the docs-build environment. The implementation is ~100 lines and has been stable since Sphinx 1.6 (2017).

- **pytest import modes** ([docs](https://docs.pytest.org/en/stable/explanation/pythonpath.html)) — pytest installs its own `MetaPathFinder` (`sys.meta_path.insert(0, ...)`) to control how test modules are located and loaded. While pytest's finder is not a stub finder, the pattern of scoping a `MetaPathFinder` around a targeted import via a context manager is idiomatic pytest internal practice.

- **mypy `--ignore-missing-imports`** — mypy avoids the problem entirely by never executing imports at runtime; it reads `.pyi` stubs and source AST only. Its `stubgen` tool ([source](https://github.com/python/mypy/blob/master/mypy/stubgen.py)) generates stubs without importing, which is why mypy recommends shipping `.pyi` files rather than runtime stubs. The mypy recommendation for library authors is explicit: stub out optional heavy dependencies in `.pyi` files so type checkers never need to import them ([mypy docs: missing stubs](https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports)).


### Disadvantages and risks

- **Stubs all unknown modules unconditionally.** If a pipeline module tries to import a package that is simply misspelled or not yet installed intentionally, the stub silently succeeds rather than raising `ImportError`. The AST-scan approach only mocks modules it actively found in source files, which limits the blast radius.

- **Module-level computed values become `_MockObject`.** Any expression that evaluates a mocked attribute at import time — e.g., `CLASSES = sklearn.utils.all_estimators()` — will store a `_MockObject` instead of the real list. If `register_pipelines` or `create_pipeline` reads that value to build pipeline structure, the result may be wrong. The AST-scan approach has the same weakness, but it is explicit about which packages are affected.

- **Harder to audit.** With AST scanning, the set of mocked modules is computed and logged before the import runs (`log.debug("Mocking %d missing …")`). With the catch-all finder it is only known after the import completes, which makes debugging missing-dep issues less transparent.

- **Thread safety.** Mutating `sys.meta_path` is not thread-safe. In a multi-threaded server (e.g. FastAPI startup), concurrent imports during the `with safe_context_v2()` block could interact with the catch-all finder unexpectedly. The AST-scan approach mutates `sys.modules` via `patch.dict`, which has the same caveat.

### Verdict

For Kedro's use case the `sys.meta_path` catch-all is strictly more robust than AST scanning for catching transitive and dynamic imports. The main practical risk — silently succeeding on misspelled package names — is acceptable for inspection-only commands where the output is read-only pipeline structure. The AST-scan approach was chosen for the initial implementation because it provides an explicit, auditable list of what was mocked, which aids debugging during the spike. Either approach can replace the other; the integration point in `_load_data()` is identical.
