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

## Solution 1 — `lite_shim`: AST Scan + `sys.modules` Mock

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

## Solution 2 — `sys.meta_path` Catch-All Stub Finder

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

### Disadvantages

- **Stubs all unknown modules unconditionally.** If a pipeline module tries to import a package that is simply misspelled or not yet installed intentionally, the stub silently succeeds rather than raising `ImportError`. The AST-scan approach only mocks modules it actively found in source files, which limits the blast radius.

- **Module-level computed values become `_MockObject`.** Any expression that evaluates a mocked attribute at import time — e.g., `CLASSES = sklearn.utils.all_estimators()` — will store a `_MockObject` instead of the real list. If `register_pipelines` or `create_pipeline` reads that value to build pipeline structure, the result may be wrong. The AST-scan approach has the same weakness, but it is explicit about which packages are affected.

- **Harder to audit.** With AST scanning, the set of mocked modules is computed and logged before the import runs (`log.debug("Mocking %d missing …")`). With the catch-all finder it is only known after the import completes, which makes debugging missing-dep issues less transparent.

- **Thread safety.** Mutating `sys.meta_path` is not thread-safe. In a multi-threaded server (e.g. FastAPI startup), concurrent imports during the `with safe_context_v2()` block could interact with the catch-all finder unexpectedly. The AST-scan approach mutates `sys.modules` via `patch.dict`, which has the same caveat.


---

## Solution 3 — Generated Pipeline Manifest

Both `lite_shim` approaches above still execute Python imports (with mocked deps). A fundamentally different approach sidesteps the import chain entirely: **compute the pipeline structure once, serialize it, and serve read-only commands from the serialized form**.

This is the pattern used by build tools and package managers that separate a "build phase" (expensive, executes code) from a "query phase" (cheap, reads metadata):

| Tool | Build phase | Query phase |
|---|---|---|
| `cargo` | `cargo build` | `cargo metadata` reads `Cargo.lock` |
| `npm` | `npm install` | `npm list` reads `package-lock.json` |
| CMake | `cmake ..` | reads `CMakeCache.txt` |
| **Kedro (proposed)** | `kedro inspect` | `registry list/describe` reads `.kedro/pipeline_manifest.json` |

### How it works

#### Step 1 — Generate the manifest via `kedro inspect`

The manifest already has a natural generation point: **`kedro inspect`** (`kedro.inspection.get_project_snapshot`). This existing API initialises the project, loads all pipelines and configuration, and returns a [`ProjectSnapshot`](../inspect/inspect-project.md) — a dataclass that contains exactly the structure `registry list` and `registry describe` need: pipeline names, nodes, inputs, outputs, tags, datasets, and parameter keys.

Serializing it to disk is straightforward because `ProjectSnapshot` and its nested types are plain dataclasses:

```python
# kedro/framework/project/_manifest.py
import dataclasses
import json
from pathlib import Path

from kedro.inspection import get_project_snapshot

_MANIFEST_PATH = Path(".kedro") / "pipeline_manifest.json"


def write_manifest(project_path: Path) -> None:
    snapshot = get_project_snapshot(project_path)
    payload = {
        "schema_version": 1,
        **dataclasses.asdict(snapshot),
    }
    _MANIFEST_PATH.parent.mkdir(exist_ok=True)
    _MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
```

`kedro inspect` is the single authoritative source: it already handles environment resolution, catalog loading, and pipeline registration. No parallel serialization logic is needed — the manifest is just a persisted `ProjectSnapshot`.

The `kedro inspect` command can be run explicitly before inspection-only CI steps, or automatically as a post-hook after `kedro run` succeeds.

#### Step 2 — Read-only commands consume the manifest

`kedro registry list` and `kedro registry describe` check for the manifest first. If present and fresh, they read it directly — zero imports, zero mocking:

```python
def load_manifest() -> dict | None:
    if not _MANIFEST_PATH.exists():
        return None
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
```

#### Step 3 — Freshness check (optional but recommended)

Hash the pipeline source files at write time and re-check at read time. If the hash has changed, warn the user that the manifest is stale:

```python
import hashlib

def _source_hash(package_name: str) -> str:
    spec = importlib.util.find_spec(package_name)
    package_dir = Path(spec.submodule_search_locations[0])
    h = hashlib.sha256()
    for path in sorted(package_dir.rglob("*.py")):
        h.update(path.read_bytes())
    return h.hexdigest()

# Stored in the manifest JSON:
# { "source_hash": "a3f2...", "pipelines": { ... } }
```

If `source_hash` differs, the CLI can either fall back to the live import path or print a clear warning:

```
Warning: pipeline_manifest.json is stale (source files changed).
Run 'kedro inspect' to refresh, or install all project dependencies to load live.
```

### What the manifest covers

`ProjectSnapshot` already contains everything `registry list`, `registry describe`, and `catalog describe-datasets` need — it was designed for exactly this kind of read-only introspection. See [`inspect-project.md`](../inspect/inspect-project.md) for the full schema.

| CLI command | Served from manifest? | `ProjectSnapshot` field |
|---|---|---|
| `kedro registry list` | **Yes** | `snapshot.pipelines[*].name` |
| `kedro registry describe --pipeline data_science` | **Yes** | `snapshot.pipelines[*].nodes` (name, inputs, outputs, tags) |
| `kedro catalog describe-datasets` | **Yes** | `snapshot.datasets` (type, filepath) |
| `kedro run` | **No** — always loads live; manifest is never used for execution | — |

### Prior Usage

- **`cargo metadata`** ([docs](https://doc.rust-lang.org/cargo/commands/cargo-metadata.html)) — outputs JSON describing the full workspace graph without building. Cargo computes this from `Cargo.toml` and `Cargo.lock`, never by executing Rust code.
- **`npm pack --dry-run` / `npm list`** ([docs](https://docs.npmjs.com/cli/v10/commands/npm-list)) — queries the installed package graph from `node_modules/.package-lock.json` without executing any JavaScript.
- **`pip inspect`** ([PEP 566](https://peps.python.org/pep-0566/), added in pip 22.2) — returns installed package metadata as JSON by reading wheel `.dist-info` directories, never importing the packages.
- **pytest `--collect-only`** ([docs](https://docs.pytest.org/en/stable/how-to/usage.html#calling-pytest-through-python-m-pytest)) — collects test structure by importing test modules, but the conceptual separation (collection vs execution) is the same principle. Many CI pipelines cache the collection output separately from the run output.

### Disadvantages

- **Staleness.** The manifest reflects the last time pipelines were successfully loaded. If a user edits pipeline code and immediately runs `kedro registry list`, they see the old structure unless they re-run `kedro manifest build` or have the freshness check in place.
- **Requires a successful prior import.** The first time a project is set up, or after installing a new heavy dependency, the manifest does not yet exist. The CLI must fall back to the import path (with mocking) for the first run, or instruct the user to run `kedro manifest build` first.
- **Catalog serialization is harder.** `DataCatalog` entries can be parameterized via `globals.yml`, Jinja2 templates, and runtime credentials. Serializing a fully-resolved catalog to JSON is non-trivial and may expose secrets.
- **New surface area.** Introduces a new command, a new file format, a schema version, and a migration story when the schema changes.

### Summary

The manifest approach is the only alternative that is **both truly import-free and covers `registry describe`**. It is the right long-term architecture if Kedro wants to fully decouple read-only CLI tooling from the project's Python environment. The main cost is the staleness problem and the cold-start requirement.

For the import-with-mocking tier (`lite_shim` or `sys.meta_path`), which remains the fallback when no fresh manifest exists: the `sys.meta_path` catch-all is strictly more robust than AST scanning for catching transitive and dynamic imports, at the cost of silently succeeding on misspelled package names. The AST-scan approach was chosen for the initial implementation because it produces an explicit, auditable list of what was mocked. Either can replace the other; the integration point in `_load_data()` is identical.

A practical incremental path that combines all three tiers:

1. Serialize the `ProjectSnapshot` to `.kedro/pipeline_manifest.json` automatically after every successful `kedro run` (post-hook) and after every explicit `kedro inspect` call.
2. `registry list` and `registry describe` consume the manifest when present and fresh — zero imports, zero mocking.
3. When the manifest is absent or stale, fall back to `lite_shim` (or `sys.meta_path`) to load live with mocked deps.
