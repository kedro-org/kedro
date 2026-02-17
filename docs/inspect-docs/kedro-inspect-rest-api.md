## Phase 1: Proposed REST endpoints

Hosted under `kedro server` (Phase 1 PR #5368) or standalone. REST endpoints ship alongside the
programmatic `inspect_project()` API from day one — non-Python consumers (VS Code extension,
CI tools) use HTTP instead of importing Python.

| Method | Path | Response | Purpose |
|---|---|---|---|
| `GET` | `/inspect/snapshot` | `ProjectSnapshot` | Full project snapshot — mirrors `inspect_project()` |
| `GET` | `/inspect/pipelines` | `List[PipelineInfo]` (summary) | List all registered pipelines (no graph) |
| `GET` | `/inspect/pipelines/{id}` | `PipelineInfo` | Full graph for one pipeline |

> **Not included**: `/inspect/nodes/{id}` — detailed node metadata (source code, filepath,
> previews) is viz-specific and stays in viz's own API for now.


### Example: `GET /inspect/pipelines/data_processing`

```json
{
  "id": "data_processing",
  "name": "data_processing",
  "nodes": [
    {
      "id": "preprocess_companies",
      "name": "preprocess_companies",
      "type": "task",
      "tags": ["preprocessing"],
      "pipelines": ["__default__", "data_processing"],
      "parameters": {"drop_columns": ["id"]},
      "namespace": "data_processing"
    },
    {
      "id": "companies",
      "name": "companies",
      "type": "data",
      "tags": [],
      "pipelines": ["__default__", "data_processing"],
      "dataset_type": "pandas.CSVDataset",
      "is_free_input": true
    }
  ],
  "edges": [
    {"source": "companies", "target": "preprocess_companies"}
  ],
  "tags": [{"id": "preprocessing", "name": "preprocessing"}]
}
```

---

## Programmatic usage (no server needed)

```python
from kedro.inspection import inspect_project

# Snapshot works even without pandas/spark installed
snapshot = inspect_project("/path/to/project")

if snapshot.has_missing_deps:
    print("Warning: some dependencies were mocked")

# List pipeline names
for p in snapshot.pipelines:
    print(p.id, len(p.nodes), "nodes")

# Get a specific pipeline's graph
dp = next(p for p in snapshot.pipelines if p.id == "data_processing")
for edge in dp.edges:
    print(f"{edge.source} → {edge.target}")

# Get dataset types (resolved from factory patterns too)
for node in dp.nodes:
    if node.type == "data":
        print(f"{node.name}: {node.dataset_type}")  # e.g. "pandas.CSVDataset"
```

---

### Phase 2: Extended endpoints

These build on the Phase 1 snapshot and expose finer-grained inspection for consumers
that need individual resources rather than the full snapshot.

| Method | Path | Response | Phase 1 coverage | What's new |
|---|---|---|---|---|
| `GET` | `/inspect/nodes` | `List[NodeInfo]` | Yes — embedded in `PipelineInfo.nodes` | Standalone list across all pipelines, deduplicated |
| `GET` | `/inspect/nodes/{id}` | `NodeInfo` (extended) | Partial — basic fields in snapshot | Adds `source_location` (file + line number from `inspect.getsourcefile()`) |
| `GET` | `/inspect/datasets` | `List[DatasetInfo]` | Partial — `NodeInfo` has `dataset_type`, `is_free_input` | Standalone resource with full catalog config: `type`, `filepath`, `metadata`, `layer`, `credentials` key (not value), `transcoded_versions` |
| `GET` | `/inspect/datasets/{name}` | `DatasetInfo` | No | Single dataset with resolved config from `config_resolver.resolve_pattern()` + `definition_file`/`definition_line` for IDE go-to-definition |
| `GET` | `/inspect/parameters` | `ParametersInfo` | Partial — resolved values in `NodeInfo.parameters` | Full parameter tree: keys, resolved values, definition files, `parameter_locations` (key → file:line) for IDE go-to-definition |
| `GET` | `/inspect/modular-pipelines` | `List[ModularPipelineInfo]` | No — namespace is a flat string in `NodeInfo` | Namespace hierarchy tree with children, inputs, outputs (built from `node.namespace` via `_explode_namespace()`) |
| `GET` | `/inspect/config/{type}` | `Dict` | No | Resolve catalog/parameters/credentials config files per environment — uses `OmegaConfigLoader` directly |

#### New models for Phase 2

```python
class DatasetInfo(BaseModel):
    """Standalone dataset resource with full catalog config."""
    name:                str                  # e.g. "companies"
    type:                str                  # e.g. "pandas.CSVDataset"
    filepath:            Optional[str]        = None
    layer:               Optional[str]        = None   # from metadata["kedro-viz"]["layer"]
    is_free_input:       bool
    pipelines:           List[str]            # which pipelines reference this dataset
    transcoded_versions: Optional[List[str]]  = None
    credentials_key:     Optional[str]        = None   # key name only, never the value
    metadata:            Optional[Dict]       = None   # raw metadata dict from catalog config
    definition_file:     Optional[str]        = None   # e.g. "conf/base/catalog.yml"
    definition_line:     Optional[int]        = None   # line number in YAML file

class ParameterLocation(BaseModel):
    """Source location of a single parameter key."""
    file: str                                 # e.g. "conf/base/parameters.yml"
    line: int                                 # line number in YAML file

class ParametersInfo(BaseModel):
    """Full parameter tree with provenance."""
    resolved:              Dict[str, Any]              # merged + interpolated values
    definition_files:      List[str]                   # e.g. ["conf/base/parameters.yml", "conf/local/parameters.yml"]
    parameter_locations:   Optional[Dict[str, ParameterLocation]] = None  # key → file:line for go-to-definition

class ModularPipelineInfo(BaseModel):
    """Namespace hierarchy — built from node.namespace."""
    id:        str                            # e.g. "uk.data_processing"
    name:      str
    inputs:    List[str]                      # dataset IDs
    outputs:   List[str]                      # dataset IDs
    children:  List[ModularPipelineChild]     # nodes, datasets, nested modular pipelines

class ModularPipelineChild(BaseModel):
    id:   str
    type: str                                 # "task" | "data" | "parameters" | "modularPipeline"
```
