# Kedro PR Review — Reference

Detailed reference for the `review-kedro-pr` skill. Read sections selectively — use the section headers to find what you need.

---

## Import-linter contracts

All contracts are defined in `pyproject.toml` under `[tool.importlinter]` with `root_package = "kedro"`.

### Contract 1: Layer hierarchy

```toml
[[tool.importlinter.contracts]]
name = "CLI > Context > Library, Runner > Extras > IO & Pipeline"
type = "layers"
containers = "kedro"
layers = [
    "framework.cli",
    "framework.session",
    "framework.context",
    "framework.project",
    "runner",
    "io",
    "pipeline",
    "config"
]
ignore_imports = [
    "kedro.runner.task -> kedro.framework.project",
    "kedro.framework.hooks.specs -> kedro.framework.context",
    "kedro -> kedro.ipython"
]
```

**Rule:** A module in a lower layer must not import from a higher layer. For example, `kedro.io` (layer 6) must not import from `kedro.runner` (layer 5).

**Allowed exceptions:**
- `kedro.runner.task` may import from `kedro.framework.project`
- `kedro.framework.hooks.specs` may import from `kedro.framework.context`
- `kedro` (top-level) may import from `kedro.ipython`

### Contract 2: Pipeline and IO independence

```toml
[[tool.importlinter.contracts]]
name = "Pipeline and IO are independent"
type = "independence"
modules = [
    "kedro.pipeline",
    "kedro.io"
]
ignore_imports = [
    "kedro -> kedro.ipython"
]
```

**Rule:** `kedro.pipeline` and `kedro.io` must not import each other in any direction.

**Allowed exception:** `kedro` (top-level) may import from `kedro.ipython`.

### Contract 3: Config cannot import runner/io/pipeline

```toml
[[tool.importlinter.contracts]]
name = "Config cannot import Runner et al"
type = "forbidden"
source_modules = [
    "kedro.config"
]
forbidden_modules = [
    "kedro.runner",
    "kedro.io",
    "kedro.pipeline",
]
```

**Rule:** Nothing in `kedro.config` may import from `kedro.runner`, `kedro.io`, or `kedro.pipeline`. No exceptions.

### Contract 4: Runner/io/pipeline cannot import config

```toml
[[tool.importlinter.contracts]]
name = "Runner et al cannot import Config"
type = "forbidden"
source_modules = [
    "kedro.runner",
    "kedro.io",
    "kedro.pipeline",
]
forbidden_modules = [
    "kedro.config"
]
ignore_imports = [
    "kedro.framework.context.context -> kedro.config",
    "kedro.framework.session.session -> kedro.config",
]
```

**Rule:** Nothing in `kedro.runner`, `kedro.io`, or `kedro.pipeline` may import from `kedro.config`.

**Allowed exceptions** (these are transitive chain exceptions — `framework.context` and `framework.session` are not themselves in runner/io/pipeline, but import-linter needs these listed to allow the transitive import paths through them):
- `kedro.framework.context.context` may import from `kedro.config`
- `kedro.framework.session.session` may import from `kedro.config`

---

## Kedro public API surface

### `kedro.io`

Exports (`__all__`): `AbstractDataset`, `AbstractVersionedDataset`, `CachedDataset`, `CatalogProtocol`, `CatalogConfigResolver`, `DatasetAlreadyExistsError`, `DatasetError`, `DatasetNotFoundError`, `DataCatalog`, `MemoryDataset`, `SharedMemoryDataset`, `SharedMemoryDataCatalog`, `SharedMemoryCatalogProtocol`, `Version`.

**`AbstractDataset(ABC, Generic[_DI, _DO])`** — base class for all datasets:
- `load() -> _DO` — abstract, load data
- `save(data: _DI) -> None` — abstract, save data
- `_describe() -> dict[str, Any]` — abstract, return dataset description for repr
- `exists() -> bool` — delegates to `_exists()`, default returns `False`
- `release() -> None` — delegates to `_release()`
- `from_config(name, config, load_version, save_version) -> AbstractDataset` — class method, creates instance from catalog config dict

**`AbstractVersionedDataset`** — extends `AbstractDataset` with:
- `filepath` property, `Version` namedtuple (load/save), version path resolution helpers
- `_get_load_path()`, `_get_save_path()`, `_get_versioned_path()` for version-aware file access

### `kedro.runner`

Exports (`__all__`): `AbstractRunner`, `ParallelRunner`, `SequentialRunner`, `Task`, `ThreadRunner`.

**`AbstractRunner(ABC)`** — base class for all runners:
- `__init__(is_async: bool = False)`
- `run(pipeline, catalog, hook_manager=None, run_id=None, only_missing_outputs=False) -> dict[str, Any]` — validates inputs, calls `_run`
- `_run(pipeline, catalog, hook_manager=None, run_id=None) -> None` — abstract, actual execution logic
- `_get_executor(max_workers: int) -> Executor | None` — abstract, returns the executor for parallel/async execution

Concrete runners: `SequentialRunner`, `ParallelRunner`, `ThreadRunner`.

### `kedro.pipeline`

Exports (`__all__`): `node`, `pipeline`, `Node`, `Pipeline`, `GroupedNodes`, `llm_context_node`, `LLMContext`, `LLMContextNode`, `tool`.

**`Pipeline`** — DAG of nodes:
- `pipeline(*args)` factory function for creating pipelines
- `Pipeline.filter()`, `Pipeline.inputs()`, `Pipeline.outputs()`, `Pipeline.nodes`, `Pipeline.datasets()`

**`Node`** — single computation unit:
- `node(func, inputs, outputs, name=None, ...)` factory function
- `Node.run(inputs)`, `Node.name`, `Node.inputs`, `Node.outputs`

### `kedro.config`

Exports (`__all__`): `AbstractConfigLoader`, `BadConfigException`, `MissingConfigException`, `OmegaConfigLoader`.

**`AbstractConfigLoader`** — base class for config loaders.
**`OmegaConfigLoader`** — concrete loader using OmegaConf.

### `kedro.framework.hooks`

**Spec classes** in `kedro/framework/hooks/specs.py` (Pluggy-based):

- **`DataCatalogSpecs`**: `after_catalog_created(catalog, conf_catalog, conf_creds, parameters, save_version, load_versions)`
- **`NodeSpecs`**: `before_node_run(node, catalog, inputs, is_async, run_id)`, `after_node_run(node, catalog, inputs, outputs, is_async, run_id)`, `on_node_error(error, node, catalog, inputs, is_async, run_id)`
- **`PipelineSpecs`**: `before_pipeline_run(run_params, pipeline, catalog)`, `after_pipeline_run(run_params, run_result, pipeline, catalog)`, `on_pipeline_error(error, run_params, pipeline, catalog)`
- **`DatasetSpecs`**: `before_dataset_loaded(dataset_name, node)`, `after_dataset_loaded(dataset_name, data, node)`, `before_dataset_saved(dataset_name, data, node)`, `after_dataset_saved(dataset_name, data, node)`
- **`KedroContextSpecs`**: `after_context_created(context)`

**Markers** (from `kedro/framework/hooks/markers.py`):
- `hook_spec` — marks a method as a hook specification
- `hook_impl` — marks a method as a hook implementation (this is what plugin/hook authors use)

**CLI hooks** (separate namespace `kedro_cli`):
- `CLICommandSpecs`: `before_command_run(project_metadata, command_args)`, `after_command_run(project_metadata, command_args)`
- Markers: `cli_hook_spec`, `cli_hook_impl`

### `kedro.framework.context` and `kedro.framework.session`

- **`KedroContext`** — project context, holds config loader, catalog, env.
- **`KedroSession`** — entry point for running pipelines, manages lifecycle.
- **`KedroServiceSession`** — new session implementation for multiple runs and data injection (under active development).

---

## Non-obvious patterns

These patterns look unusual but are intentional. Don't flag them. Read this section when a PR touches these files.

### `AbstractDataset.__init_subclass__` (kedro/io/core.py)

When a class subclasses `AbstractDataset`, `__init_subclass__` automatically:
1. **Wraps `__init__`** to capture `_init_args` (the arguments passed at construction time) for later use by `_init_config()`.
2. **Aliases `_load`/`_save` to `load`/`save`** if the subclass defines `_load` or `_save` (legacy pattern).
3. **Wraps `load` and `save`** with `_load_wrapper`/`_save_wrapper` for logging and error handling. Uses `__loadwrapped__`/`__savewrapped__` flags to avoid double-wrapping.

Any change to dataset base behavior affects all subclasses implicitly.

### `parse_dataset_definition` / `load_obj` (kedro/io/core.py)

Turns dataset `type:` strings from catalog YAML into Python classes by trying different module path prefixes. This is how catalog YAML connects to actual code — changes here affect all dataset loading.

### Module-level `__getattr__` in kedro/pipeline/pipeline.py

Lazy deprecation of `TRANSCODING_SEPARATOR`:

```python
def __getattr__(name: str) -> Any:
    if name == "TRANSCODING_SEPARATOR":
        warnings.warn(
            f"{name!r} has been moved to 'kedro.pipeline.transcoding', "
            f"and the alias will be removed in Kedro 1.0.0.",
            KedroDeprecationWarning,
        )
        return TRANSCODING_SEPARATOR
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

This is intentional — not a code smell. Don't flag it.

### `_NullPluginManager.__getattr__` (kedro/framework/hooks/manager.py)

Returns `self` for any attribute, so hook calls do nothing when there's no real `PluginManager`. This is intentional.

### `SharedMemoryDataset.__getattr__` (kedro/io/shared_memory_dataset.py)

Passes attribute access through to the underlying `MemoryDataset`. The `__setstate__` guard prevents infinite recursion when unpickling.

---

## RELEASE.md format

SKILL.md covers which H2 sections to use and the bullet format. This section adds the full file structure and automation details.

### Full file structure

```markdown
# Upcoming Release

## Major features and improvements
* Description of new feature or significant enhancement.

## Bug fixes and other changes
* Description of bug fix or minor change.

## Documentation changes
* Description of docs change.

## Community contributions
* [Username](https://github.com/username)


# Release X.Y.Z

## Major features and improvements
* ...
```

### Automation dependency

Shipped releases must use the exact heading `# Release X.Y.Z`. The script `tools/github_actions/extract_release_notes.py` finds the first H1 matching that heading and grabs everything until the next H1. Wrong heading format = broken GitHub Release.

### Example of a correct entry

Under `# Upcoming Release`, section `## Bug fixes and other changes`:

```markdown
* Fixed `AttributeError` when node functions have non-Pydantic/dataclass type hints on `params:` inputs. The parameter validation framework now correctly skips types it cannot validate.
```
