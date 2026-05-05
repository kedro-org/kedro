# Pipeline Loading Architecture

**Branch:** `spike/dep_free` · **Related:** [Registry Architecture](pipeline_registry_architecture.md)

---

## Three Layers of Laziness

```
Layer 1 — Pipeline names     zero imports, directory scan or pyproject.toml read only
Layer 2 — Pipeline modules   import only the requested pipeline's __init__.py
Layer 3 — Node functions     import heavy dependencies only when the node runs  [TBD]
```

Today Kedro partially addresses Layer 1 and Layer 2 via the `_requested_pipelines` side-channel. Layer 3 is unaddressed. The entire mechanism lives in a god module (`framework/project/__init__.py`).

---

## What `__init__.py` Looks Like After

The `pyproject.toml` + `AutoDiscoveryRegistry` approach removes **all pipeline-related code** from `__init__.py`:

| Removed | Why gone |
|---|---|
| `_ProjectPipelines` class | `AutoDiscoveryRegistry` in `kedro/pipeline/registry.py` replaces it |
| `_load_data_wrapper` decorator | No more lazy dict proxy needed |
| `_get_pipelines_registry_callable` | No `register_pipelines` function to call |
| `_load_data()` | Discovery logic lives in the registry class |
| `find_pipelines()` | Moves to `AutoDiscoveryRegistry.list()` / `.load()` |
| `_load_modular_pipelines()` | Same |
| `_load_default_pipeline()` | Same |
| `set_requested()` / `_requested_pipelines` | Commands call `registry.load(name)` directly — no global state |
| `pipelines` global singleton | Gone |

`__init__.py` becomes settings + logging + bootstrap only. The pipeline concern moves entirely to `kedro/pipeline/registry.py`.

### New file topology

```
kedro/
  pipeline/
    registry.py        # PipelineRegistry Protocol + AutoDiscoveryRegistry
  framework/
    project/
      __init__.py      # settings, LOGGING, PACKAGE_NAME, configure_project() only
      _settings.py     # _ProjectSettings (Dynaconf wrapper)
      _logging.py      # _ProjectLogging
    session/
      session.py       # no set_requested(), no pipelines global
    cli/
      project.py       # explicit load sequence per command
```

---

## CLI-Demand-Driven Loading

Each command has a well-defined demand profile. Today this is implicit and scattered across `session.py`, `cli/catalog.py`, `cli/registry.py` with manual `set_requested()` calls. Making it explicit:

| Command | Layer 1 (names) | Layer 2 (modules) | Config | Catalog |
|---|---|---|---|---|
| `kedro -h` | — | — | — | — |
| `kedro info` | — | — | — | — |
| `kedro registry list` | yes | — | — | — |
| `kedro registry describe X` | — | X only | — | — |
| `kedro catalog list` | — | — | yes | yes |
| `kedro catalog list -p X` | X only | — | yes | yes |
| `kedro run --pipeline X` | — | X only | yes | yes |
| `kedro run` | default set | default set | yes | yes |

### What the run command looks like

```python
# kedro/framework/cli/project.py

@click.command()
@click.option("--pipeline", multiple=True)
def run(pipeline, ...):
    registry = _get_registry()                        # reads pyproject.toml — zero imports
    names = pipeline or registry.default_names        # Layer 1

    with KedroSession.create(...) as session:
        catalog = session.load_catalog()              # config + catalog only
        for name in names:
            pl = registry.load(name)                  # Layer 2, one at a time
            runner.run(pl, catalog, ...)
```

No global `pipelines` object. No `set_requested()`. No temporal ordering to manage. Each command owns its loading sequence explicitly.

### `AutoDiscoveryRegistry` — the full picture

```python
# kedro/pipeline/registry.py

class AutoDiscoveryRegistry:
    def __init__(self, package_name: str, config: PipelineConfig):
        self._package = package_name
        self._exclude = set(config.exclude or [])
        self._default_names = config.default          # None means "all discovered"
        self._cache: dict[str, Pipeline] = {}

    def list(self) -> list[str]:
        """Layer 1 — directory scan only, zero pipeline imports."""
        pkg = importlib.resources.files(f"{self._package}.pipelines")
        return [
            d.name for d in pkg.iterdir()
            if d.is_dir()
            and not d.name.startswith("_")
            and d.name not in self._exclude
        ]

    def load(self, name: str) -> Pipeline:
        """Layer 2 — import one pipeline module on demand."""
        if name not in self._cache:
            mod = importlib.import_module(f"{self._package}.pipelines.{name}")
            self._cache[name] = mod.create_pipeline()
        return self._cache[name]

    @property
    def default_names(self) -> list[str]:
        return self._default_names or self.list()

    @property
    def default(self) -> Pipeline:
        return sum(self.load(n) for n in self.default_names) or Pipeline([])
```

### `pyproject.toml` configuration

```toml
[tool.kedro.pipelines]
exclude  = ["experimental", "legacy"]        # never surfaced, never run
default  = ["data_processing", "data_science"]  # what kedro run runs with no --pipeline flag
```

- `exclude` — directories exist but Kedro ignores them. Absent from `kedro registry list` and from the default run.
- `default` — explicit composition for the no-flag case. If absent, all non-excluded pipelines are combined.
- `PIPELINE_REGISTRY_CLASS` in `settings.py` provides the programmatic escape hatch for namespaced pipelines, dynamic pipeline generation, or any case `pyproject.toml` cannot express.

---

## Migration Path

| Phase | Change | Breaking |
|---|---|---|
| 1 | Introduce `PIPELINE_REGISTRY_CLASS` in `settings.py`, default `AutoDiscoveryRegistry` | No |
| 2 | If `pipeline_registry.py` exists: use it with a deprecation warning | No |
| 3 | If `pipeline_registry.py` absent: auto-discover from `pyproject.toml` + directory scan | No |
| 4 | Remove `pipeline_registry.py` support, `find_pipelines()`, `_ProjectPipelines` | Yes (major) |
