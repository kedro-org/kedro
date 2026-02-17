# Draft: Kedro Inspection API Surface

> **Status**: Draft proposal for [kedro#5266](https://github.com/kedro-org/kedro/issues/5266)
> **Goal**: A project snapshot — understand any Kedro project's graph structure with **zero dependencies beyond Kedro itself**

---

## Core idea

The inspection API provides a **project snapshot**: pipelines, nodes, edges, dataset types, and parameters — without requiring pandas, spark, or any dataset library to be installed.

It does this by **using Kedro's own framework** (KedroSession, OmegaConfigLoader, DataCatalog) with a **safety net** that mocks missing dependencies and catches instantiation failures gracefully — exactly how kedro-viz's lite mode already works.

```
┌──────────────────────────────────────────────────────────────────┐
│                    Kedro Framework (used as-is)                  │
│                                                                  │
│  KedroSession.create() → session.load_context()                  │
│    ├── OmegaConfigLoader: env merging, variable interpolation    │
│    ├── DataCatalog: factory pattern resolution via               │
│    │   CatalogConfigResolver (no materialization)                │
│    └── Pipeline registry: nodes, edges, tags, namespaces         │
└─────────────────────┬────────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │     Safety net layer    │
         │                         │
         │  LiteParser (AST scan)  │  ← detect missing modules
         │  MagicMock sys.modules  │  ← mock missing imports
         │  (no AbstractDatasetLite│  ← we never materialize,
         │   needed — we never     │     so no fallback needed)
         │   call catalog.get())   │
         └────────────┬────────────┘
                      │
              ┌───────────────────┐
              │ inspect_project() │
              │ → ProjectSnapshot │
              └───────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   Programmatic use          REST endpoint
   (Python import)           (kedro server)
```

### What it does NOT do

| Capability | Why not |
|---|---|
| Materialize datasets | Uses `config_resolver.resolve_pattern()` instead — never calls `catalog.get()` |
| Call `catalog.load()` / `catalog.save()` | Runtime I/O, not inspection |
| `inspect.getsource()` on node functions | Viz-specific sidebar feature |
| Build modular pipeline tree | Viz-specific expand/collapse UI construct |
| Resolve layers | Viz-specific — `metadata["kedro-viz"]["layer"]` |

---

## Design principles

| Principle | Rationale |
|---|---|
| **Use Kedro's framework** | OmegaConf, factory resolution, env merging all work correctly; just add a safety net for missing deps |
| **Lite mode pattern** | AST-scan for missing deps → mock with `MagicMock` in `sys.modules` → pipeline imports succeed without heavy deps |
| **No Kedro object references in output** | Models must serialize cleanly; no lazy validators tied to `kedro_obj` |
| **Single model layer** | One set of Pydantic models = domain + API response |
| **Stateless function** | `inspect_project()` returns data; no global mutable state |

---

## How `inspect_project()` works internally

Directly inspired by kedro-viz's `load_data(is_lite=True)` flow:

```
inspect_project(project_path, env, extra_params)
│
├── 1. AST-scan project for missing dependencies
│      LiteParser(package_name).parse(project_path)
│      → {"pipelines/dp.py": {"pandas", "sklearn"}, ...}
│
├── 2. Mock missing modules
│      for module in missing_deps:
│          sys_modules_patch[module] = MagicMock()
│
├── 3. Patch sys.modules (mock missing imports so pipeline modules can load)
│      with patch.dict("sys.modules", sys_modules_patch):
│
│          ├── 4. Create KedroSession + load context
│          │      KedroSession.create(project_path, env=env, runtime_params=extra_params)
│          │      context = session.load_context()
│          │      → OmegaConf resolves configs, merges envs, interpolates vars
│          │
│          ├── 5. Get catalog (NO materialization happens here)
│          │      catalog = context.catalog
│          │      → DataCatalog.from_config() creates CatalogConfigResolver
│          │      → Explicit datasets stored as _LazyDataset (not materialized)
│          │      → Factory patterns stored in config_resolver._dataset_patterns
│          │
│          ├── 6. Resolve factory patterns + extract types (NO materialization)
│          │      for dataset_name in all_pipeline_datasets:
│          │          ds_config = catalog.config_resolver.resolve_pattern(dataset_name)
│          │          dataset_type = ds_config.get("type")  # plain string!
│          │      → CatalogConfigResolver matches "{namespace}.{name}" patterns
│          │      → Substitutes placeholders → returns resolved config dict
│          │      → config["type"] = "pandas.CSVDataset" (string, no import)
│          │      → NEVER calls catalog.get() — avoids materialization entirely
│          │
│          ├── 7. Get parameters from config
│          │      params = context.params
│          │      → Resolved via OmegaConf (merging, interpolation)
│          │
│          ├── 8. Build snapshot for each pipeline
│          │      for pipeline_id, pipeline in pipelines.items():
│          │          ├── Iterate pipeline.nodes → NodeInfo(type=task)
│          │          ├── For each node input/output:
│          │          │   ├── Classify → DATA or PARAMETERS
│          │          │   ├── dataset_type from resolved config["type"] string
│          │          │   └── NodeInfo(type=data or parameters)
│          │          ├── Derive edges from input/output wiring
│          │          ├── Detect free inputs (pipeline.inputs())
│          │          └── Collect tags
│          │
│          └── 9. Return ProjectSnapshot
│
│   NOTE: AbstractDatasetLite patch is NOT needed here — we never call
│   catalog.get(), catalog.load(), or trigger materialization.
│   The only patch needed is sys.modules mocking for pipeline imports.
```

---

## Proposed module structure

```
kedro/
└── inspection/
    ├── __init__.py          # Public API: inspect_project()
    ├── models.py            # Pydantic response schemas (ProjectSnapshot, PipelineInfo, etc.)
    ├── snapshot.py          # Core logic: session → catalog → pipelines → snapshot
    ├── lite_shim.py         # safe_context() — sys.modules mocking via LiteParser
    └── utils.py             # Helpers (param detection, hashing, type extraction)
```

---

### New public API in kedro core

```python
# kedro/inspection/lite_shim.py

from contextlib import contextmanager

@contextmanager
def safe_context(project_path: Path, package_name: str):
    """Context manager that mocks missing heavy dependencies so that
    Kedro session loading and config resolution succeed without them.

    Only patches sys.modules — does NOT patch AbstractDataset.
    Uses config_resolver.resolve_pattern() for dataset info (no materialization).

    Usage:
        with safe_context(project_path, package_name) as missing_deps:
            session = KedroSession.create(project_path=project_path)
            with session as s:
                context = s.load_context()
                catalog = context.catalog
    """
    # 1. AST-scan for missing modules
    parser = LiteParser(package_name)
    unresolved = parser.parse(project_path)

    # 2. Build mock dict
    sys_patch = sys.modules.copy()
    missing_modules = set()
    if unresolved:
        for deps in unresolved.values():
            missing_modules.update(deps)
        sys_patch.update(parser.create_mock_modules(missing_modules))

    # 3. Patch sys.modules only
    with patch.dict("sys.modules", sys_patch):
        yield missing_modules
```

### Who benefits

| Consumer | How they use `safe_context()` / `inspect_project()` |
|---|---|
| **kedro-viz** | Replaces its own lite mode stack; consumes `ProjectSnapshot` |
| **IDE plugins** (VS Code, PyCharm) | `inspect_project()` → show pipeline graph, node list, dataset types in editor |
| **CI/CD pipelines** | Validate pipeline structure without installing data deps |
| **kedro CLI** | `kedro inspect` command — print project structure |
| **Documentation generators** | Auto-generate pipeline docs from snapshot |
| **Custom tooling** | Any tool that needs to understand a Kedro project without running it |

---

## Public API

### Entry point

```python
from kedro.inspection import inspect_project

snapshot: ProjectSnapshot = inspect_project(
    project_path="/path/to/project",
    env="production",                    # optional, defaults to "local"
    extra_params={"key": "value"},       # optional, runtime param overrides
    pipeline_id="data_processing",       # optional, None = all pipelines
)
```

### Return type

```python
class ProjectSnapshot(BaseModel):
    """Complete snapshot of a Kedro project's structure."""
    metadata:           ProjectMetadata
    pipelines:          List[PipelineInfo]
    selected_pipeline:  str
    has_missing_deps:   bool              # True if any modules were mocked
```

---

## Pydantic models

### Project metadata

```python
class ProjectMetadata(BaseModel):
    project_name:   str                  # from pyproject.toml / settings
    project_path:   str                  # absolute path
    package_name:   str                  # Python package name
    kedro_version:  str                  # e.g. "1.0.0"
    source_dir:     str                  # e.g. "src"
    environments:   List[str]            # e.g. ["base", "local", "production"]
    config_paths:   List[str]            # e.g. ["conf/base", "conf/local"]
```

### Pipeline structure

```python
class PipelineInfo(BaseModel):
    """One registered pipeline with its full graph."""
    id:                str
    name:              str
    nodes:             List[NodeInfo]
    edges:             List[EdgeInfo]
    tags:              List[TagInfo]
```

> **Not included**: `layers` (viz-specific, from `metadata["kedro-viz"]["layer"]`)
> and `modular_pipelines` (viz-specific, built from `node.namespace` for expand/collapse UI).

### Nodes

```python
class NodeType(str, Enum):
    TASK              = "task"
    DATA              = "data"
    PARAMETERS        = "parameters"

class NodeInfo(BaseModel):
    """A node in the pipeline graph."""
    id:                str
    name:              str
    type:              NodeType
    tags:              List[str]
    pipelines:         List[str]

    # Task-specific
    parameters:        Optional[Dict]          = None   # resolved via OmegaConf from parameters.yml
    namespace:         Optional[str]           = None   # flat string, e.g. "uk.data_processing"
    inputs:            Optional[List[str]]     = None   # dataset names (human-readable, e.g. "companies")
    outputs:           Optional[List[str]]     = None   # dataset names (human-readable, e.g. "preprocessed_companies")

    # Data-specific
    dataset_type:      Optional[str]           = None   # from resolved catalog config["type"] string
    is_free_input:     Optional[bool]          = None

    # Transcoded-specific
    transcoded_versions: Optional[List[str]]   = None
    original_name:       Optional[str]         = None
```

> `dataset_type` comes from the resolved catalog config string (after factory pattern resolution),
> NOT from instantiating the dataset. Works even when the dataset library isn't installed.

### Edges

```python
class EdgeInfo(BaseModel, frozen=True):
    source: str    # node ID
    target: str    # node ID
```

### Tags

```python
class TagInfo(BaseModel):
    id:   str
    name: str
```
