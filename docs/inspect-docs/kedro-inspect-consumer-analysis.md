## Consumer analysis: kedro-viz

kedro-viz is the visualization and UI consumer for Kedro projects. Unlike most plugins
which are either small CLI wrappers or hook-based runtime integrations, kedro-viz
implements both an out-of-session snapshot-based importer (for remote/CLI usage) and
local helpers that historically duplicated some project-introspection responsibilities.

### How kedro-viz currently consumes Kedro

| What it needs | Current Kedro API / file | Purpose |
|---|---|---|
| Project/session bootstrap | `integrations/kedro/data_loader.py` → creates `KedroSession` | Read project metadata, catalog and pipelines for local preview mode |
| AST-based dependency detection (lite mode) | `integrations/kedro/lite_parser.py` (project-specific parser) | Fast dependency detection without full import/materialization |
| Graceful dataset fallback for previews | `integrations/kedro/abstract_dataset_lite.py` | Provide safe dataset wrappers for preview rendering |
| UnavailableDataset helper | `integrations/utils.py` | Fallback when `catalog.get()` fails at preview time |
| Graph construction & factory resolution | `data_access/managers.py` | Build the directed graph used by the UI; resolve factory-based datasets |
| Domain and API models | `models/flowchart/`, `api/rest/responses/` | Serialize snapshot and build UI models |
| REST endpoints for remote mode | `api/rest/router.py` | Serve the snapshot and previews via HTTP |

Notes: kedro-viz historically owns several responsibilities that span both static
inspection (discover pipelines, nodes, dataset metadata) and live preview materialization
(creating sessions, loading datasets). That ownership led to duplicated parsing logic
(the `lite_parser`) and tight coupling to session creation.

### Coverage mapping: proposed inspection API vs kedro-viz needs

| kedro-viz need | Proposed inspection API | Coverage / Action |
|---|---|---|
| List pipelines and nodes | `/inspect/snapshot` → `snapshot.pipelines[]`, `PipelineInfo`, `NodeInfo` | Covered — snapshot supplies pipeline/node structure |
| Node metadata (name, namespace, tags) | `NodeInfo.name`, `.namespace`, `.tags` | Covered — used to build modular tree and sidebar |
| Dataset metadata (type, catalog extra) | `DatasetInfo.type`, `DatasetInfo.metadata` | Covered — layer ordering via `metadata["kedro-viz"]["layer"]` preserved |
| Fast lite-mode dependency detection | `lite_shim` in core (safe_context + AST/lightweight parser) | Covered — move AST concerns into core `lite_shim` and remove `lite_parser` from viz |
| Dataset preview materialization | Still requires local `catalog.get()` & safe wrappers | Partial — snapshot can't materialize; keep `abstract_dataset_lite.py` for safe previews when running locally or via sandboxed preview endpoints |
| Unavailable dataset handling | Keep `UnavailableDataset` helper | Keep in viz (or move small helper to `integrations/utils.py`) |
| Graph construction (viz domain models) | Build from `ProjectSnapshot` client-side | Covered — `data_access/managers.py` consumes snapshot instead of creating session |
| REST endpoints for remote mode | `/inspect/*` endpoints served by kedro core; viz fetches them | Covered — viz becomes client of inspection REST endpoints |

### How kedro-viz would use the inspection API

```
Before (current)
─────────────────────
bootstrap project → KedroSession() → parse pipelines via lite_parser / data_loader
build graph in-process → materialize previews via catalog

After (with inspection API)
───────────────────────────
option A: viz (local) calls `inspect_project()` → receives `ProjectSnapshot` → build UI models
option B: viz (remote) fetches `/inspect/snapshot` and `/inspect/pipelines` → build UI models
preview endpoints (optional) call into a small, sandboxed preview runner that uses
`abstract_dataset_lite.py` to materialize safe previews only when requested
```

### What's NOT needed from the inspection API

- Full dataset materialization — previews are runtime concerns and should remain in
    a controlled sandbox or local session. The snapshot should not include dataset
    contents except as optional small pre-computed summaries.
- Full AST parsing inside viz — move this responsibility into core `lite_shim` so
    all consumers can reuse the logic.

### Practical code changes (proposed)

- Remove `integrations/kedro/lite_parser.py` from kedro-viz and replace its tests with
    tests against core `lite_shim`.
- Update `data_access/managers.py` to accept a `ProjectSnapshot` input and stop creating
    a `KedroSession` when a snapshot is present.
- Keep `integrations/kedro/abstract_dataset_lite.py` and `integrations/utils.py` for
    safe preview materialization; optionally extract small helpers back into a shared
    `integrations` module if desired.
- Update REST router to prefer servable `/inspect/*` endpoints when available and
    fall back to local snapshot generation only when running in embedded/local mode.

### Verdict

kedro-viz should follow the same consumer pattern as other plugins: treat the
inspection API as the authoritative source of project structure and use lightweight,
shared shims for any fast/unsafe parsing. Keep runtime preview materialization confined
to viz-specific helpers (or a small shared helper module), but stop duplicating
AST/parsing logic and stop creating global `KedroSession` objects when a snapshot is
available.


## Consumer analysis: vscode-kedro

vscode-kedro is the **official VS Code extension** for Kedro and the **highest-value consumer**
of the proposed inspection API. It has a dual-layer architecture: a TypeScript VS Code client
communicating over LSP (Language Server Protocol) with a Python server that directly imports
Kedro framework internals. It uses **5 private Kedro APIs** — the most fragile integration
of any consumer analyzed.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  VS Code Extension (TypeScript)                              │
│    ├── Project detection (pyproject.toml)                     │
│    ├── Python interpreter resolution (ms-python extension)   │
│    ├── Language client (vscode-languageclient)               │
│    ├── File watchers (conf/**/*.yml, pipelines/**/*.py)      │
│    └── Webview panel (Kedro-Viz via React)                   │
│                                                              │
│  Communication: JSON-RPC over stdio (LSP)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│  Python LSP Server (pygls)                                   │
│    ├── bootstrap_project() + KedroSession.create()           │
│    ├── DummyDataCatalog (catalog structure, no materialization)│
│    ├── OmegaConfigLoader (config file paths + resolution)    │
│    ├── DataCatalog.from_config() (YAML validation)           │
│    └── kedro-viz import (flowchart webview data)             │
│                                                              │
│  LSP Handlers:                                               │
│    ├── textDocument/definition    → go-to dataset/param def  │
│    ├── textDocument/references    → find dataset usage in .py│
│    ├── textDocument/completion    → dataset name autocomplete │
│    ├── textDocument/hover         → dataset config on hover  │
│    ├── textDocument/didOpen       → validate catalog YAML    │
│    ├── textDocument/didChange     → real-time YAML validation│
│    └── kedro.getProjectData      → viz JSON for webview      │
└─────────────────────────────────────────────────────────────┘
```

### How vscode-kedro currently consumes Kedro

#### Project initialization (every LSP startup)

```python
project_metadata = bootstrap_project(root_path)
session = KedroSession.create(root_path, env=env)
session._hook_manager = _NullPluginManager()          # PRIVATE API — disable hooks for perf
context = session.load_context()
config_loader = context.config_loader
```

The extension creates a full `KedroSession` on every startup, then immediately disables the
hook manager via a **private API** to avoid triggering telemetry and other plugins.

#### DummyDataCatalog — the key architectural insight

The extension independently invented a **"catalog without materialization"** pattern:

```python
class DummyDataCatalog:
    """Stores raw config dicts without instantiating dataset classes."""
    def __init__(self, conf_catalog, feed_dict=None):
        self._datasets = conf_catalog or {}    # raw config, not dataset objects
        self._params = feed_dict or {}
```

This is **exactly** what `inspect_project()` provides — catalog structure resolved from
factory patterns via `config_resolver.resolve_pattern()` without importing dataset libraries.
The DummyDataCatalog validates that the inspection API's approach is what IDE consumers need.

#### Config file path discovery (uses 3 private APIs)

```python
def _get_conf_paths(server, config_type):
    patterns = server.config_loader.config_patterns[config_type]
    conf_source = server.config_loader.conf_source
    base_env = server.config_loader.base_env
    for pattern in patterns:
        for match in server.config_loader._fs.glob(...):        # PRIVATE
            if not server.config_loader._is_hidden(match):       # PRIVATE
                if server.config_loader._is_valid_config_path(match):  # PRIVATE
                    paths.append(match)
```

#### Catalog YAML validation

Three validators, two of which need `DataCatalog.from_config()`:

| Validator | What it does | Needs Kedro? |
|---|---|---|
| `FactoryPatternValidator` | Regex bracket matching + variable consistency | No — pure regex |
| `DatasetConfigValidator` | `DataCatalog.from_config({name: config})` → validates individual entries | Yes — needs DataCatalog |
| `FullCatalogValidator` | `DataCatalog.from_config(full_catalog)` → validates cross-references | Yes — needs DataCatalog |

### Complete Kedro import surface

```python
# bundled/tool/lsp_server.py
from kedro.io import DataCatalog
from kedro.config import OmegaConfigLoader
from kedro.framework.hooks.manager import _NullPluginManager        # PRIVATE
from kedro.framework.session import KedroSession
from kedro.framework.startup import ProjectMetadata, bootstrap_project
from kedro.framework.project import PACKAGE_NAME

# bundled/tool/validators/dataset_config.py
from kedro.io import DataCatalog

# bundled/tool/validators/full_catalog.py
from kedro.io import DataCatalog
```

**Private API usage** (5 symbols — highest of any consumer):
- `_NullPluginManager` — disable hooks during LSP init
- `config_loader._fs.glob()` — find config files
- `config_loader._is_hidden()` — filter hidden config files
- `config_loader._is_valid_config_path()` — validate config paths
- `catalog._get_dataset()` — Kedro 0.19.x fallback for dataset access

### Feature-by-feature data requirements

| Feature | What Kedro data it needs | Current source |
|---|---|---|
| **Go-to-definition** | Config file paths + YAML line numbers | `OmegaConfigLoader._fs.glob()` + `SafeLineLoader` |
| **Find references** | Pipeline source file paths | `PACKAGE_NAME` + `importlib_resources.files()` |
| **Autocomplete** | Dataset + parameter name list | `DummyDataCatalog.list()` |
| **Hover** | Resolved dataset config dict, parameter values | `config_loader["catalog"]`, `config_loader["parameters"]` |
| **Catalog validation** | `DataCatalog.from_config()` result | Direct DataCatalog instantiation |
| **Viz webview** | Full kedro-viz JSON | `kedro_viz.server.load_and_populate_data()` |
| **Environment selection** | Available environments | Manual `conf/` directory scan |

### Coverage mapping: proposed API vs vscode-kedro needs

| vscode-kedro need | Phase 1 | Phase 2 | Still needs direct Kedro? |
|---|---|---|---|
| Project detection + metadata | `ProjectSnapshot.metadata` | — | No |
| Dataset names (autocomplete) | `NodeInfo` where `type == "data"` | — | No |
| Parameter names (autocomplete) | `NodeInfo` where `type == "parameters"` | — | No |
| Dataset type (hover enrichment) | `NodeInfo.dataset_type` | `DatasetInfo.type` | No |
| Parameter values (hover) | `NodeInfo.parameters` | `ParametersInfo.resolved` | No |
| Pipeline list | `snapshot.pipelines[].id` | — | No |
| Pipeline graph (nodes, edges) | `PipelineInfo.nodes`, `.edges` | — | No |
| Node namespace | `NodeInfo.namespace` | — | No |
| Environment list | — | `ProjectMetadataSnapshot.environments` | No (with Phase 2) |
| Config file paths | — | `ProjectMetadataSnapshot.config_paths` | No (with Phase 2) |
| Dataset resolved config | — | `DatasetInfo` (filepath, layer, metadata) | No (with Phase 2) |
| Node source location | — | `NodeInfo.source_location` | No (with Phase 2) |
| Go-to-definition (datasets + params) | — | `DatasetInfo.definition_file/line`, `ParametersInfo.parameter_locations` | No (with Phase 2) |
| **Catalog YAML validation** | — | — | **Yes** |
| **Find references (text search)** | — | — | **Yes** |
| **Viz webview (full viz JSON)** | — | — | **Yes (kedro-viz)** |

### How the inspection API would transform this extension

#### Phase 1 replaces ~40% of Kedro API surface

**Before** — heavy initialization with private API hacks:
```python
project_metadata = bootstrap_project(root_path)
session = KedroSession.create(root_path, env=env)
session._hook_manager = _NullPluginManager()   # PRIVATE API
context = session.load_context()
config_loader = context.config_loader
dummy_catalog = DummyDataCatalog(config_loader["catalog"], ...)
```

**After** — single call, no private APIs:
```python
snapshot = inspect_project(root_path, env=env)
# Dataset names for autocomplete:
dataset_names = [n.name for p in snapshot.pipelines for n in p.nodes if n.type == "data"]
# Dataset types for hover:
dataset_types = {n.name: n.dataset_type for p in snapshot.pipelines for n in p.nodes if n.type == "data"}
# Parameter values for hover:
param_values = {n.name: n.parameters for p in snapshot.pipelines for n in p.nodes if n.type == "task" and n.parameters}
```

**What gets deleted**:
- `DummyDataCatalog` class — replaced by `NodeInfo` data from snapshot
- `_NullPluginManager` hack — `inspect_project()` handles this internally via `safe_context()`
- `bootstrap_project()` + `KedroSession.create()` — replaced by single `inspect_project()` call
- `OmegaConfigLoader` direct access (for autocomplete/hover) — replaced by snapshot data

#### Phase 2 replaces ~75% of Kedro API surface

Additionally eliminates:
- `config_loader._fs.glob()`, `_is_hidden()`, `_is_valid_config_path()` — replaced by `ProjectMetadataSnapshot.config_paths`
- Manual environment scanning — replaced by `ProjectMetadataSnapshot.environments`
- `config_loader["catalog"]` raw dict access for hover — replaced by `DatasetInfo`
- `SafeLineLoader` hack for YAML line numbers — replaced by `DatasetInfo.definition_file/line` and `ParametersInfo.parameter_locations`

#### What remains (~25%) — inherently IDE-specific

| Feature | Why inspection API can't replace it |
|---|---|
| **Catalog YAML validation** | Requires `DataCatalog.from_config()` to detect instantiation errors — read-only inspection can't do this |
| **Find references** | Text-searching .py files for string matches is an IDE concern |
| **Viz webview** | Full kedro-viz data stack (layers, modular pipelines, stats, previews) |

### Phase 2 definition locations close the biggest gap

Phase 2 includes `DatasetInfo.definition_file/line` and `ParametersInfo.parameter_locations`
(see Phase 2 models above). This eliminates the `SafeLineLoader` hack and **all 3 private
`OmegaConfigLoader` API usages**, which together are the extension's most fragile code.

### Alternative: REST endpoint as LSP backend

An alternative architecture: the extension's Python LSP server could be replaced by fetching
from `kedro server`'s REST endpoints:

```
VS Code Extension (TypeScript)
    │
    ├── GET /inspect/snapshot         → project metadata, pipeline graphs, autocomplete data
    ├── GET /inspect/datasets/{name}  → hover information
    ├── GET /inspect/parameters       → parameter hover + autocomplete
    └── GET /inspect/pipelines/{id}   → node details
```

This would **eliminate the Python LSP server entirely** for read-only features (autocomplete,
hover, pipeline graph). Only validation (which needs `DataCatalog.from_config()`) and
go-to-definition (which needs YAML source mapping) would still need Python.

### Verdict: highest-value consumer — validates the inspection API's purpose

vscode-kedro is the **strongest validation** that the inspection API is needed:

1. **It independently invented `DummyDataCatalog`** — the same "catalog without materialization"
   pattern that `inspect_project()` provides. This proves the need is real.

2. **It uses 5 private Kedro APIs** — all of which the inspection API would eliminate. Every
   Kedro version upgrade risks breaking the extension.

3. **Phase 1 alone replaces 40% of its Kedro surface** — project init, dataset enumeration,
   parameter resolution, pipeline graph.

4. **Phase 2 replaces 75%** — adding config paths, environments, dataset details,
   definition locations (`definition_file/line` on `DatasetInfo`, `parameter_locations` on `ParametersInfo`).

5. **The REST endpoint alternative** could eliminate the Python LSP server entirely for
   read-only features, making the extension a pure TypeScript HTTP client.


## Consumer analysis: kedro-airflow

kedro-airflow (`kedro airflow create`) generates Airflow DAG `.py` files from a Kedro project.
It has **4 source files** — the plugin is small but touches many Kedro APIs.

### How kedro-airflow currently consumes Kedro

| What it needs | Current Kedro API | File |
|---|---|---|
| **Pipeline discovery** | `from kedro.framework.project import pipelines`; `pipelines.get(name)`, `dict(pipelines)` | `plugin.py` |
| **Node iteration** | `pipeline.nodes` → `node.name`, `node.inputs`, `node.outputs` | `grouping.py` |
| **Tag filtering** | `pipeline.only_nodes_with_tags(*tags)` | `plugin.py` |
| **Namespace grouping** | `pipeline.group_nodes_by(group_by="namespace")` | `plugin.py` |
| **MemoryDataset detection** | `catalog.get(name)` + `isinstance(..., MemoryDataset)` | `grouping.py` |
| **Airflow-specific config** | `context.config_loader["airflow"]` | `plugin.py` |
| **Project metadata** | `metadata.project_path`, `metadata.package_name` | `plugin.py` |
| **Kedro parameters** | Not read at generation time — read at Airflow runtime via `session.run()` | `airflow_dag_template.j2` |

### Coverage mapping: proposed API vs kedro-airflow needs

| kedro-airflow need | Phase 1 | Phase 2 | Gap? |
|---|---|---|---|
| List all pipelines by name | `/inspect/snapshot` → `pipelines[].id` | — | Covered |
| Get nodes in a pipeline | `PipelineInfo.nodes` | — | Covered |
| Node name, tags, namespace | `NodeInfo.name`, `.tags`, `.namespace` | — | Covered |
| **Node inputs/outputs (dataset names)** | `EdgeInfo` gives graph edges | — | **Gap — see below** |
| Filter by tags | Client-side filter on `NodeInfo.tags` | — | Covered (client-side) |
| **MemoryDataset detection** | `NodeInfo.dataset_type` = `"MemoryDataset"` | `DatasetInfo.type` | **Partially covered — see below** |
| **Namespace grouping** | `NodeInfo.namespace` available | `/inspect/modular-pipelines` | Covered (client builds groups from namespace) |
| Package name, project path | `ProjectMetadataSnapshot` | — | Covered |
| Environments, config paths | `ProjectMetadataSnapshot` | — | Covered |
| **Airflow config loading** | — | `/inspect/config/{type}` | Covered in Phase 2 |
| **Pipeline operations** (`only_nodes_with_tags`, `group_nodes_by`) | — | — | **Not applicable — see below** |


### How kedro-airflow would use the inspection API

```
Before (current)                          After (with inspection API)
─────────────────────                     ──────────────────────────
bootstrap_project()                       snapshot = inspect_project(project_path, env=env)
pipelines singleton                       snapshot.pipelines
pipeline.only_nodes_with_tags()           client-side filter on NodeInfo.tags
pipeline.group_nodes_by("namespace")      client-side group on NodeInfo.namespace
pipeline.nodes → node.inputs/outputs      NodeInfo.inputs / NodeInfo.outputs (proposed)
catalog.get() + isinstance(MemoryDataset) NodeInfo.dataset_type is None or == "MemoryDataset"
context.config_loader["airflow"]          /inspect/config/airflow (Phase 2)
metadata.package_name                     snapshot.metadata.package_name
```

**Key benefit**: kedro-airflow would no longer need to `bootstrap_project()`, create a
`KedroSession`, or access the catalog directly. The entire DAG generation could work from
the snapshot — including in a **remote** scenario where `kedro server` provides the snapshot
via REST and the Airflow environment doesn't have the Kedro project installed locally.

### What's NOT needed from the inspection API

| kedro-airflow concern | Why inspection API doesn't need to handle it |
|---|---|
| Airflow DAG template rendering | Plugin-specific — Jinja2 template stays in kedro-airflow |
| `KedroOperator` runtime execution | Happens at Airflow runtime, not at generation time |
| `session.run()` | Runtime, not inspection |
| `apache-airflow` dependency | Only needed at Airflow runtime, never at generation time |

---

## Consumer analysis: kedro-docker

kedro-docker provides `kedro docker init`, `build`, `run`, `ipython`, and `jupyter` commands.
It has **3 source files** + **4 static templates** and is the most loosely coupled Kedro plugin.

### How kedro-docker currently consumes Kedro

| What it needs | Current approach | Kedro API used? |
|---|---|---|
| **Project root path** | `Path.cwd()` | No — pure filesystem |
| **Project/image name** | `Path.cwd().name` | No — directory name |
| **Dockerfile generation** | Copies static template files (`Dockerfile.simple` / `Dockerfile.spark`) | No — `shutil.copyfile()` |
| **Volume mounts** | Hardcoded `DOCKER_DEFAULT_VOLUMES = ("conf/local", "data", "logs", "notebooks", "references", "results")` | No — convention-based |
| **Docker ignore patterns** | Static `.dockerignore` template (excludes `data/`, `conf/local/`, credentials) | No — convention-based |
| **Pipeline/runner selection** | Forwards CLI args verbatim to `kedro run` inside container | No — pass-through |
| **Kedro version** | `from kedro import __version__` — parsed but **never used** (dead code) | Minimal |
| **CLI utilities** | `KedroCliError`, `call`, `forward_command` | CLI framework only |

### Complete Kedro import surface

```python
# plugin.py
from kedro import __version__ as kedro_version              # dead code
from kedro.framework.cli.utils import KedroCliError, call, forward_command

# helpers.py
from kedro.framework.cli.utils import KedroCliError
```

That's it. **Zero imports** from `kedro.pipeline`, `kedro.io`, `kedro.framework.session`,
`kedro.framework.context`, or `kedro.framework.project`.

### Coverage mapping: proposed API vs kedro-docker needs

| kedro-docker need | Inspection API coverage | Verdict |
|---|---|---|
| Project root path | `ProjectMetadataSnapshot.project_path` | Covered, but plugin doesn't need it — uses `Path.cwd()` |
| Image name | `ProjectMetadataSnapshot.package_name` | Could replace `Path.cwd().name` with a proper project name |
| Volume mount paths | `ProjectMetadataSnapshot.config_paths` | Could derive from config paths instead of hardcoding |
| Source directory | `ProjectMetadataSnapshot.source_dir` | Could use for smarter Dockerfile `COPY` |
| Pipeline structure | `PipelineInfo`, `NodeInfo` | Not needed — docker doesn't inspect pipelines |
| Dataset types | `NodeInfo.dataset_type` | Not needed — docker doesn't inspect catalog |
| Parameters | `NodeInfo.parameters` | Not needed — docker doesn't read params |

### Potential improvements with inspection API

The inspection API could **optionally** improve kedro-docker, but none of these are blockers:

| Improvement | How | Priority |
|---|---|---|
| **Smarter image naming** | Use `snapshot.metadata.package_name` instead of `Path.cwd().name` | Low — current approach works fine |
| **Dynamic volume mounts** | Use `snapshot.metadata.config_paths` to mount the right config dirs instead of hardcoding `conf/local` | Low — convention rarely changes |
| **Auto-detect Spark** | Check if any `NodeInfo.dataset_type` contains `"spark"` → auto-select `Dockerfile.spark` template | Medium — could eliminate `--spark` flag |
| **Dockerfile templating** | Use `snapshot.metadata` to generate Dockerfile with correct source dir, package name, Python version | Medium — would make Dockerfile less generic but more correct |
| **Config-aware .dockerignore** | Read actual config paths to exclude sensitive dirs | Low — current static template is sufficient |

### Verdict: minimal impact

kedro-docker is essentially a **Docker command wrapper** that treats the Kedro project as an
opaque directory tree. It delegates all Kedro-specific logic to `kedro run` inside the container.

The inspection API **does not need any changes** to support kedro-docker. The plugin works today
with zero Kedro internals knowledge and would continue to work the same way. The potential
improvements listed above are nice-to-haves, not requirements.

**No new endpoints or model changes needed.**

---

## Consumer analysis: kedro-telemetry

kedro-telemetry collects **anonymous usage statistics** (CLI commands, aggregate project metrics)
and sends them to Heap. It has **2 source files** (`plugin.py`, `masking.py`) and is the most
deeply coupled Kedro plugin — 12 unique Kedro imports across its codebase.

### How kedro-telemetry currently consumes Kedro

Unlike kedro-airflow (which creates sessions at generation time) or kedro-docker (which doesn't
touch Kedro internals), kedro-telemetry operates **inside a running Kedro session** via framework
hooks. It never creates a `KedroSession` itself — it receives objects injected by Kedro's hook
mechanism.

| What it needs | Current Kedro API | Hook |
|---|---|---|
| **Project path** | `context.project_path` | `after_context_created` |
| **Package name** | `PACKAGE_NAME` singleton from `kedro.framework.project` | module-level import |
| **Kedro version** | `kedro.__version__` | module-level import |
| **Pipeline count** | `pipelines.keys()` from `kedro.framework.project` | `after_catalog_created` |
| **Node count** | `pipelines.get("__default__").nodes` — length only | `after_catalog_created` |
| **Dataset count** | `catalog.keys()` → filter non-parameter datasets | `after_catalog_created` |
| **Dataset type distribution** | `catalog.get_type(ds_name)` for each dataset | `after_catalog_created` |
| **CLI command masking** | `KedroCLI(project_path)` → introspects Click commands | `before_command_run` |
| **Tooling metadata** | Reads `pyproject.toml` `[tool.kedro]` `tools`, `example_pipeline` | `before_command_run` |
| **Consent** | Reads `.telemetry` file from project path | `after_context_created` |

### Complete Kedro import surface

```python
# plugin.py
from kedro import __version__ as KEDRO_VERSION
from kedro.framework.cli.cli import KedroCLI
from kedro.framework.cli.hooks import cli_hook_impl
from kedro.framework.hooks import hook_impl
from kedro.framework.project import PACKAGE_NAME, pipelines
from kedro.framework.startup import ProjectMetadata
from kedro.io.data_catalog import DataCatalog
from kedro.pipeline import Pipeline

# masking.py — no kedro imports (only click)
```

### What telemetry data it collects (two Heap events)

**Event 1: "CLI command"** — sent from `after_command_run`:

| Property | Source |
|---|---|
| `username` | UUID from `~/.config/kedro/telemetry.toml` |
| `project_id` | `sha512(project_uuid + package_name)` |
| `project_version` | `kedro.__version__` |
| `command` | Masked CLI command (args redacted) |
| `os`, `python_version` | `sys.platform`, `sys.version` |
| `is_ci_env` | Checks `CI` env var + known CI tool env vars |
| `tools` | From `pyproject.toml [tool.kedro] tools` |
| `example_pipeline` | From `pyproject.toml [tool.kedro] example_pipeline` |

**Event 2: "Kedro Project Statistics"** — sent from `after_catalog_created`:

| Property | Source |
|---|---|
| `number_of_datasets` | `len([d for d in catalog.keys() if not d.startswith("param")])` |
| `number_of_nodes` | `len(default_pipeline.nodes)` (from `__default__` only) |
| `number_of_pipelines` | `len(pipelines.keys())` |
| `dataset_types` | `{catalog.get_type(ds): count}` — bucketed into kedro types vs `"custom"` |

### What it does NOT access

- Does not iterate individual nodes
- Does not inspect node functions, inputs, outputs, or tags
- Does not read parameters
- Does not call `catalog.load()` or `catalog.save()`
- Does not inspect modular pipeline namespaces or layers

### Coverage mapping: proposed API vs kedro-telemetry needs

| kedro-telemetry need | Phase 1 | Phase 2 | Gap? |
|---|---|---|---|
| Pipeline count | `len(snapshot.pipelines)` | — | Covered |
| Node count (`__default__` only) | Count `NodeInfo` where `type == "task"` | — | Covered |
| Dataset count (non-parameter) | Count `NodeInfo` where `type == "data"` | — | Covered |
| Dataset type distribution | `NodeInfo.dataset_type` strings | `DatasetInfo.type` | Covered |
| Kedro version | `snapshot.metadata.kedro_version` | — | Covered |
| Package name | `snapshot.metadata.package_name` | — | Covered |
| Project path | `snapshot.metadata.project_path` | — | Covered |
| **`tools` from pyproject.toml** | — | — | **Gap — not in snapshot** |
| **`example_pipeline` from pyproject.toml** | — | — | **Gap — not in snapshot** |
| CLI command masking | — | — | Not applicable — CLI-level concern |

### Why kedro-telemetry should NOT adopt `inspect_project()`

The inspection API and telemetry solve fundamentally different problems:

| Concern | Inspection API | Telemetry |
|---|---|---|
| **When it runs** | On-demand, external to session | Inside every `kedro run` / CLI command |
| **How it gets data** | Creates its own session + context | Receives objects via framework hooks |
| **Performance budget** | Seconds (one-time snapshot) | Milliseconds (runs on every command) |
| **Data scope** | Full project structure | 4 aggregate numbers |

Calling `inspect_project()` inside `after_catalog_created` would:
1. Create a **redundant** KedroSession (one already exists — that's how the hook fired)
2. Build a full `ProjectSnapshot` when telemetry only needs aggregate counts
3. Add **unnecessary latency** to every `kedro run`

The hook-based approach (receiving `catalog` and `pipelines` directly) is the correct pattern
for plugins that operate within a running session.

### Potential future benefit

If telemetry ever needed an **out-of-session** mode — e.g., a `kedro telemetry report` command
that analyzes a project without running it — then `inspect_project()` would be the right entry
point. The snapshot provides all the data needed for aggregate statistics without requiring a
full session.

### Verdict: no API changes needed

kedro-telemetry's needs are fully covered by the data already in the session hooks. The two
`pyproject.toml` fields (`tools`, `example_pipeline`) are scaffolding metadata, not project
structure — they belong in telemetry's own TOML parsing, not in the inspection API.

**No new endpoints or model changes needed.**

---

## Consumer analysis: kedro-mlflow

kedro-mlflow (third-party, by Galileo-Galilei) is the **most deeply coupled** Kedro plugin
analyzed — 25 unique Kedro symbols across 12 source files, including 2 private APIs.
It provides MLflow experiment tracking, metric logging, artifact management, and
pipeline-to-model serving for Kedro projects.

### Fundamental difference: runtime augmentation vs static inspection

kedro-mlflow is a **runtime augmentation plugin** — it hooks into Kedro's execution lifecycle
to add MLflow tracking. The inspection API is a **static analysis tool** for understanding
project structure without running it. These solve fundamentally different problems.

| Concern | Inspection API | kedro-mlflow |
|---|---|---|
| **Purpose** | Understand project structure | Track and serve pipeline executions |
| **When it runs** | On-demand, external to session | During every `kedro run` via hooks |
| **What it needs** | Serializable project snapshot | Live `Pipeline`, `DataCatalog`, `KedroContext` objects |
| **Catalog usage** | `config_resolver.resolve_pattern()` (no materialization) | `catalog.load()`, `catalog.save()`, `catalog.items()`, `catalog[name] = ...` |

### How kedro-mlflow currently consumes Kedro

#### Hook-based runtime integration (core mechanism)

kedro-mlflow registers **one hook class** (`MlflowHook`) implementing **5 framework hooks**:

| Hook | Kedro objects received | What it does |
|---|---|---|
| `after_context_created` | `KedroContext` | Loads `mlflow.yml` via `context.config_loader`, gets experiment name from `context._package_name`, exports credentials via `context._get_config_credentials()` |
| `after_catalog_created` | `CatalogProtocol` | Iterates `catalog.items()` to fix metric dataset names in-place |
| `before_pipeline_run` | `Pipeline`, `DataCatalog`, `run_params` | Starts MLflow run, sets tags from `run_params`, checks `isinstance(pipeline, PipelineML)` |
| `before_node_run` | `Node`, `DataCatalog`, `inputs` | Extracts parameters from `inputs` dict (keys starting with `params:` or `parameters`), logs to MLflow |
| `after_pipeline_run` | `Pipeline`, `DataCatalog`, `run_params` | Logs `PipelineML` model, extracts artifacts, ends MLflow run |
| `on_pipeline_error` | `Pipeline`, `DataCatalog`, `run_params` | Closes all active MLflow runs with FAILED status |

#### Custom dataset types (9 classes)

kedro-mlflow defines **3 categories** of custom datasets extending Kedro's abstract classes:

| Category | Classes | Base class | Purpose |
|---|---|---|---|
| **Artifacts** | `MlflowArtifactDataset` | `AbstractVersionedDataset` | Dynamic wrapper — uses `parse_dataset_definition()` to wrap any Kedro dataset type, adds `mlflow.log_artifact()` on `_save()` |
| **Metrics** | `MlflowMetricDataset`, `MlflowMetricHistoryDataset`, `MlflowMetricsHistoryDataset` | `AbstractDataset` | Log scalar metrics and metric histories via `mlflow_client.log_metric()` |
| **Models** | `MlflowModelLocalFileSystemDataset`, `MlflowModelRegistryDataset`, `MlflowModelTrackingDataset` | `AbstractVersionedDataset` | Save/load MLflow models from filesystem, registry, or tracking server |

#### Pipeline subclass: `PipelineML`

`PipelineML` **subclasses `kedro.pipeline.Pipeline` directly** and overrides ~15 methods
(`only_nodes_with_tags`, `filter`, `__add__`, `__sub__`, etc.) to preserve the
training-inference pipeline linkage. It accesses:

- `pipeline.nodes`, `pipeline.inputs()`, `pipeline.outputs()`, `pipeline.all_outputs()`, `pipeline.datasets()`
- Every filtering method (`only_nodes_with_*`, `from_inputs`, `to_nodes`, `filter`, `tag`)

#### Pipeline-to-model serving: `KedroPipelineModel`

`KedroPipelineModel` extends `mlflow.pyfunc.PythonModel` to serve Kedro inference pipelines.
At prediction time it:

- Creates a bare `_create_hook_manager()` (**private API**)
- Constructs a `DataCatalog` with `MemoryDataset` entries
- Calls `runner.run(pipeline, catalog, hook_manager)` — runs the actual pipeline

#### CLI commands

| Command | Kedro APIs used |
|---|---|
| `kedro mlflow init` | `find_kedro_project()`, `bootstrap_project()`, `settings.CONF_SOURCE` |
| `kedro mlflow ui` | `KedroSession.create()`, `context.config_loader` |
| `kedro mlflow modelify` | `pipelines[name]`, `catalog.load()`, `KedroSession.create()` |

### Complete Kedro import surface

```python
# framework/hooks/mlflow_hook.py
from kedro.config import MissingConfigException
from kedro.framework.context import KedroContext
from kedro.framework.hooks import hook_impl
from kedro.framework.startup import _get_project_metadata    # PRIVATE
from kedro.io import CatalogProtocol, DataCatalog
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node

# mlflow/kedro_pipeline_model.py
from kedro.framework.hooks import _create_hook_manager        # PRIVATE
from kedro.io import DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline
from kedro.runner import AbstractRunner, SequentialRunner
from kedro.utils import load_obj

# framework/cli/cli.py
from kedro import __version__ as kedro_version
from kedro.framework.project import pipelines, settings
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.utils import find_kedro_project, is_kedro_project

# pipeline/pipeline_ml.py
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node

# io/artifacts/mlflow_artifact_dataset.py
from kedro.io import AbstractVersionedDataset
from kedro.io.core import parse_dataset_definition

# io/metrics/*.py
from kedro.io import AbstractDataset, DatasetError

# io/models/*.py
from kedro.io import AbstractVersionedDataset, Version
from kedro.io.core import DatasetError

# config/kedro_mlflow_config.py
from kedro.framework.context import KedroContext
from kedro.utils import load_obj
```

**Private API usage** (2 symbols):
- `_get_project_metadata` — fallback when `context._package_name` is None (interactive sessions)
- `_create_hook_manager` — creates bare hook manager for model prediction (no hooks registered)

### Kedro-to-MLflow concept mapping

| Kedro concept | MLflow concept | Mapping mechanism |
|---|---|---|
| Package name | Experiment name | `context._package_name` → `mlflow.set_experiment()` |
| Pipeline name | Run name | `run_params["pipeline_name"]` → MLflow run name |
| `run_params` dict | Run tags | All non-None run_params → `mlflow.set_tags()` |
| Node parameter inputs (`params:*`) | MLflow parameters | `mlflow.log_param()` per key |
| `MlflowArtifactDataset._save()` | MLflow artifact | `mlflow.log_artifact(local_path)` |
| `MlflowMetricDataset._save()` | MLflow metric | `mlflow_client.log_metric()` |
| `MlflowModelTrackingDataset._save()` | MLflow model | `flavor.log_model()` |
| `PipelineML` (training + inference) | MLflow pyfunc model | `mlflow.pyfunc.log_model(KedroPipelineModel)` |
| Pipeline error | Failed run status | `mlflow.end_run(RunStatus.FAILED)` |
| Pipeline success | Successful run | `mlflow.end_run()` |

### Coverage mapping: proposed API vs kedro-mlflow needs

| kedro-mlflow need | Proposed API coverage | Why |
|---|---|---|
| `context.config_loader` (load `mlflow.yml`) | Not in scope | Runtime config loading, plugin-specific |
| `context._package_name` → experiment name | `ProjectMetadataSnapshot.package_name` | Covered |
| `context.project_path` → resolve URIs | `ProjectMetadataSnapshot.project_path` | Covered |
| `context._get_config_credentials()` | Not in scope | Runtime credentials, never exposed |
| `pipeline.nodes` | `PipelineInfo.nodes` | Structure only — not Pipeline objects |
| `pipeline.inputs()` / `pipeline.outputs()` | Derivable from `PipelineInfo.edges` | Covered for read-only |
| `pipeline.filter()` / `only_nodes_with_tags()` | Not in scope | Requires live Pipeline objects |
| `isinstance(pipeline, PipelineML)` | Not in scope | Plugin-specific type check |
| `catalog.items()` / `catalog[name] = ...` | Not in scope | Runtime catalog mutation |
| `catalog.load()` / `catalog.save()` | Not in scope | Runtime I/O |
| `runner.run(pipeline, catalog)` | Not in scope | Runtime execution |
| `AbstractDataset` / `AbstractVersionedDataset` | Not in scope | Framework extension points |
| `settings.CONF_SOURCE` | `ProjectMetadataSnapshot.config_paths` | Partial — paths available, not the raw setting |

### Why kedro-mlflow should NOT adopt `inspect_project()`

kedro-mlflow needs **live Kedro objects** at every layer:

1. **Hooks receive** `KedroContext`, `Pipeline`, `DataCatalog`, `Node`, `inputs` — not serializable snapshots
2. **Custom datasets extend** `AbstractDataset` / `AbstractVersionedDataset` — framework inheritance, not API consumption
3. **`PipelineML` subclasses** `Pipeline` — overrides 15+ methods for training-inference linkage
4. **`KedroPipelineModel` runs** actual pipelines via `runner.run()` for model serving
5. **Catalog manipulation** — hooks modify the catalog in-place (`catalog[name] = ...`)

The only place `inspect_project()` could marginally help is the CLI `init` command
(replacing `bootstrap_project()` + `settings.CONF_SOURCE` with `ProjectMetadataSnapshot.config_paths`),
but the simplification is minimal.

### Implications for the inspection API design

kedro-mlflow validates two design decisions in the inspection API:

1. **Returning Pydantic models, not Kedro objects, is correct.** kedro-mlflow demonstrates that
   plugins needing live objects (Pipeline, DataCatalog, Node) must use hooks — the inspection API
   correctly does not try to replace this. It occupies a different niche.

2. **`NodeInfo.dataset_type` as a plain string is the right level of abstraction.** kedro-mlflow's
   `MlflowArtifactDataset` wraps arbitrary datasets at runtime — the inspection API only needs to
   report the configured type string (e.g., `"kedro_mlflow.io.artifacts.MlflowArtifactDataset"`),
   not understand the wrapping mechanics.

### Verdict: different problem space, minimal overlap

kedro-mlflow is a **runtime plugin** that augments Kedro's execution lifecycle. The inspection API
is a **static analysis tool**. Their overlap is limited to `ProjectMetadataSnapshot` fields (package name,
project path) which kedro-mlflow already gets through more direct channels (`KedroContext`).

**No new endpoints or model changes needed.**
