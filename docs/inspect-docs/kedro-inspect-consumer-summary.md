## Cross-consumer summary

Six consumers analyzed, ordered from highest to lowest inspection API overlap.

### 1. Consumer ranking and integration recommendations

| Rank | Consumer | Type | Overlap | Integrate? | Reasoning |
|---|---|---|---|---|---|
| 1 | **vscode-kedro** | IDE extension (LSP) | **~75%** (5 private APIs eliminated) | **Yes — highest priority** | Independently invented `DummyDataCatalog` (catalog without materialization) — proving the need. Phase 1 replaces 40%, Phase 2 replaces 75% including definition locations for go-to-def. REST could replace Python LSP server for read-only features. |
| 2 | **kedro-viz** | Visualization tool | **~60%** (lite mode stack replaced) | **Yes — primary consumer** | Inspection API extracted from viz's own patterns. Deletes `lite_parser.py`, simplifies `data_loader.py` from ~120 to ~5 lines, provides migration path for 46 domain models. |
| 3 | **kedro-airflow** | DAG generator | **~50%** (pipeline graph + catalog) | **Yes — clean fit** | DAG generation is static analysis. `NodeInfo.inputs`/`.outputs` + `.dataset_type` replace all catalog access. Enables remote DAG generation via REST. |
| 4 | **kedro-telemetry** | Usage analytics | ~30% (wrong execution model) | **No** | Runs inside every `kedro run` via hooks. Would create redundant session + full snapshot for 4 aggregate numbers. Hook-based approach is architecturally correct. |
| 5 | **kedro-mlflow** | Runtime tracking | ~10% (only metadata overlap) | **No** | Needs live `Pipeline`, `DataCatalog`, `KedroContext`. Subclasses Pipeline (15+ overrides), extends AbstractDataset (9 classes), mutates catalog, runs pipelines via `runner.run()`. |
| 6 | **kedro-docker** | Docker wrapper | ~0% | **No** | Zero Kedro internals. Treats project as opaque directory, delegates to `kedro run` inside container. |

### 2. Integration path: current approach → Phase 1 → Phase 2

| Consumer | Current approach | With inspection API | Phase 1 covers | Phase 2 additionally covers | Remaining gap (plugin-specific) |
|---|---|---|---|---|---|
| **vscode-kedro** | `bootstrap_project()` → `KedroSession.create()` → `_NullPluginManager` hack → `DummyDataCatalog` + 3 private `OmegaConfigLoader` APIs | **Python**: `inspect_project()` → `ProjectSnapshot` for autocomplete, hover, go-to-definition. Eliminates all 5 private APIs. **REST**: Could replace Python LSP server entirely — `GET /inspect/snapshot` for metadata + graph, `GET /inspect/datasets/{name}` for hover, `GET /inspect/parameters` for parameter values. | Project metadata, dataset names (autocomplete), parameter values (hover), pipeline graph, dataset types | Environment list, config file paths, dataset resolved config, definition locations (`DatasetInfo.definition_file/line`, `ParametersInfo.parameter_locations`), node source locations | Catalog YAML validation — needs `DataCatalog.from_config()`. Find references — IDE text search. Viz webview — full kedro-viz data stack. |
| **kedro-viz** | `LiteParser` + mock injection + `DataAccessManager` graph construction + `ModularPipelinesRepository` + factory resolution. 46 domain models + 17 API models. | **Python**: `inspect_project()` + adapter layer. Deletes `lite_parser.py`, simplifies `data_loader.py` from ~120 to ~5 lines. Enriches snapshot with viz-specific data (previews, NodeExtras, layers). **REST**: Viz backend could fetch `GET /inspect/snapshot` instead of running `inspect_project()` in-process — enables decoupled deployment. | Pipeline graph (nodes, edges, tags), dataset types, parameters, free inputs, project metadata | Modular pipeline hierarchy, dataset details (filepath, layer, metadata), parameter definition files, node source locations | Layers, NodeExtras, previews — built from viz-specific config (`metadata["kedro-viz"]`, `.kedro-viz/` dir, `inspect.getsource()`). `AbstractDatasetLite` materialization for previews. |
| **kedro-airflow** | `bootstrap_project()` → `pipelines` singleton → `pipeline.nodes` iteration → `catalog.get()` + `isinstance(MemoryDataset)` | **Python**: `inspect_project()` → iterate `NodeInfo.inputs`/`.outputs` + `.dataset_type` for DAG generation. No more `catalog.get()`. **REST**: `GET /inspect/pipelines/{id}` enables remote DAG generation without local Kedro install — CI/CD generates DAGs from a running `kedro server`. | Pipeline list, node names + tags + namespace + inputs + outputs, dataset types (MemoryDataset detection), project metadata | Airflow config loading (`/inspect/config/airflow`) | Jinja template rendering — plugin-specific DAG generation. Tag filtering + namespace grouping (trivial). |

### Summary

The inspection API's sweet spot is **static, external analysis** — understanding a Kedro project's
structure without running it. Three consumers fit this model perfectly (vscode-kedro, kedro-viz,
kedro-airflow). Three do not (kedro-telemetry runs in-session, kedro-mlflow needs live objects,
kedro-docker doesn't inspect Kedro at all).

The strongest validation comes from **vscode-kedro independently inventing `DummyDataCatalog`** —
the exact same pattern that `inspect_project()` formalizes. When two independent codebases
converge on the same solution (catalog structure without materialization), it's a clear signal
that the abstraction belongs in the framework.
