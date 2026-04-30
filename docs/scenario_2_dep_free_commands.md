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
