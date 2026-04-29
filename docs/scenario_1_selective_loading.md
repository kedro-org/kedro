# Scenario 1 — Selective Pipeline Loading

**Part of spike [#5406](https://github.com/kedro-org/kedro/issues/5406) · [← Overview](on_demand_dependency_loading.md) · [Scenario 2 →](scenario_2_dep_free_commands.md)**

**Assumption:** All project dependencies are installed. The goal is to avoid importing unrelated pipeline modules when a specific pipeline is requested via `--pipeline`.

---

## Background

`find_pipelines(pipelines_to_find=...)` from [PR #5401](https://github.com/kedro-org/kedro/pull/5401) already supports selective loading. If called with `["data_science"]`, it only imports `my_project/pipelines/data_science/`. The capability exists; it just needs to be wired to the CLI `--pipeline` flag.

For projects using the default registry pattern:

```python
# my_project/pipeline_registry.py
from kedro.framework.project import find_pipelines

def register_pipelines():
    return find_pipelines()  # pipelines_to_find=None → loads everything today
```

If `_requested_pipelines` is set before `find_pipelines()` runs, only the requested pipeline directory is imported.

---

## Solution

### Step 1 — `set_requested()` on `_ProjectPipelines`

`_ProjectPipelines` stores which pipelines are needed before the first dict access. Invalidates the cache if the filter changes so a subsequent full run still loads everything.

```python
# kedro/framework/project/__init__.py

class _ProjectPipelines(MutableMapping):
    def __init__(self) -> None:
        self._pipelines_module: str | None = None
        self._is_data_loaded = False
        self._content: dict[str, Pipeline] = {}
        self._requested_pipelines: list[str] | None = None  # NEW

    def set_requested(self, pipeline_names: list[str] | None) -> None:
        """Store which pipelines are needed before first dict access.
        Invalidates the cache if the filter changes.
        """
        if self._requested_pipelines != pipeline_names:
            self._is_data_loaded = False
            self._content = {}
        self._requested_pipelines = pipeline_names
```

### Step 2 — `find_pipelines()` reads `_requested_pipelines` with CLI precedence

The CLI-set filter (via `set_requested()`) takes precedence over the explicit `pipelines_to_find` kwarg. When no CLI filter is active (`_requested_pipelines` is `None`), the explicit kwarg is used as before.

Since `find_pipelines()` and the `pipelines` global are in the **same file**, there is no circular import risk. **No changes to `_load_data()` are needed for Scenario 1.**

```python
# kedro/framework/project/__init__.py

def find_pipelines(raise_errors: bool = False, pipelines_to_find: list[str] | None = None):
    # CLI-set filter takes precedence; falls back to the explicit kwarg.
    requested_pipelines = (
        pipelines._requested_pipelines
        if pipelines._requested_pipelines is not None
        else pipelines_to_find
    )
    load_all = requested_pipelines is None or "__default__" in requested_pipelines
    pipeline_filter: set[str] | None = None if load_all else set(requested_pipelines)
    # ... rest of function unchanged
```

### Step 3 — CLI commands call `set_requested()` before pipeline access

`set_requested()` must be called **before** any dict access on `pipelines`. For session-based commands, this means before `_create_session()` — the first catalog or pipeline access inside the session triggers `_load_data()`.

#### Current status

| Command | File | Call | Status |
|---------|------|------|--------|
| `kedro run --pipeline X` | `session.py:348` | `pipelines.set_requested(names)` | **Done** |
| `kedro registry describe X` | `registry.py:38` | `pipelines.set_requested([name])` | **Done** |
| `kedro catalog describe-datasets -p X` | `catalog.py:56` | `pipelines.set_requested([pipeline])` | **Done** |
| `kedro catalog resolve-patterns -p X` | `catalog.py:104` | `pipelines.set_requested([pipeline])` | **Done** |
| `inspection: get_project_snapshot(pipelines=["X"])` | `snapshot.py:136` | requires new `pipeline_names` parameter first | **Future** |

---

## Limitation — Custom `register_pipelines` Without `find_pipelines()`

This fix only works for projects using `find_pipelines()`. Projects with a hand-written `register_pipelines` receive no benefit — `find_pipelines()` is never called so `_requested_pipelines` is never read. This includes top-level imports in `pipeline_registry.py`:

```python
# pipeline_registry.py — these fire BEFORE register_pipelines() is called
from my_project.pipelines.reporting import create_pipeline as reporting_pipeline
from my_project.pipelines.data_science import create_pipeline as ds_pipeline

def register_pipelines():
    return {"reporting": reporting_pipeline(), "data_science": ds_pipeline()}
```

**Options for affected projects:**

1. **Switch to `find_pipelines()`** — the default layout since Kedro 0.18.3.

2. **Read `_requested_pipelines` manually** — gate local imports behind the stored filter:
   ```python
   from kedro.framework.project import pipelines as _pipelines

   def register_pipelines():
       requested = _pipelines._requested_pipelines  # None means load all
       result = {}
       if requested is None or "data_ingestion" in requested:
           from my_project.pipelines import data_ingestion
           result["data_ingestion"] = data_ingestion.create_pipeline()
       if requested is None or "reporting" in requested:
           from my_project.pipelines import reporting
           result["reporting"] = reporting.create_pipeline()
       return result
   ```

3. **Use Scenario 2, Approach C** — the only zero-user-code-change path. `sys.meta_path` stubs intercept all non-requested pipeline module imports before `pipeline_registry.py` runs, regardless of how `register_pipelines` is written. See [scenario_2_dep_free_commands.md](scenario_2_dep_free_commands.md).

---
