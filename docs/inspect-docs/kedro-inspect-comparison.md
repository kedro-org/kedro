# Comparison: `AlpAribal/kedro-inspect` vs our `kedro.inspection` proposal

> **Context**: [AlpAribal/kedro-inspect](https://github.com/AlpAribal/kedro-inspect) is an existing community package. This document compares it with our [inspection API proposal](kedro-inspect-presentation.md).

---

## What `kedro-inspect` does

It's a **small, focused CLI tool** (6 source files, ~300 lines) that serialises a Kedro pipeline's node structure to JSON:

```
bootstrap_project(path) → pipelines["__default__"] → InspectedPipeline.from_kedro_pipeline() → JSON
```

Its core value is **function introspection** — it captures:

- Function signatures via `inspect.signature()`
- Type hints via `typing.get_type_hints()`
- Parameter kinds (positional, keyword, var_positional, var_keyword)
- Parameter-to-dataset mapping (which function param binds to which dataset name)
- Fully qualified function names (`obj_to_fqn` / `fqn_to_obj` for serialisation/deserialisation)

### Module structure

```
src/kedro_inspect/
├── __init__.py
├── cli.py              # CLI entry point: bootstrap_project → pipeline → JSON
├── node.py             # InspectedNode: wraps KedroNode with serialisation
├── node_func.py        # NodeFunction: function signatures, type hints, argument metadata
├── pipeline.py         # InspectedPipeline: flat list of InspectedNode
├── serialisation.py    # obj_to_fqn / fqn_to_obj helpers
└── py.typed
```

### Dependencies

- `kedro` (full framework)
- `typing-extensions`

---

## Detailed comparison

| Dimension | `AlpAribal/kedro-inspect` | Our `kedro.inspection` proposal |
|---|---|---|
| **Scope** | Node function introspection | Full project snapshot (pipelines, nodes, edges, datasets, parameters, metadata) |
| **Primary output** | Function signatures + type hints + param-to-input mapping | `ProjectSnapshot` with graph structure, dataset types, resolved parameters, project metadata |
| **Dependency handling** | None — requires all project deps installed (`bootstrap_project()` must succeed) | `safe_context()` / `lite_shim` — AST-scans for missing deps, mocks them with `MagicMock` |
| **Catalog awareness** | None — no catalog, no dataset types, no factory pattern resolution | Full — resolves factory patterns via `CatalogConfigResolver`, extracts dataset type strings without materialisation |
| **Graph structure** | No edges, no graph — just a flat list of nodes | Full DAG: `NodeInfo` + `EdgeInfo` + node type classification (task/data/parameters) |
| **Parameters** | Not resolved — only maps function params to dataset names | Resolved from `parameters.yml` via OmegaConf (merged, interpolated) |
| **Project metadata** | None | `ProjectMetadataSnapshot`: project name, package name, kedro version, source dir, environments, config paths |
| **REST API** | None — CLI only | `/inspect/snapshot`, `/inspect/pipelines`, `/inspect/pipelines/{id}`, Phase 2 endpoints |
| **Programmatic API** | `InspectedPipeline.from_kedro_pipeline(pipeline)` | `inspect_project(path, env, extra_params, pipeline_id)` |
| **Serialisation format** | Custom `TypedDict` classes with `to_dict()` / `from_dict()` | Pydantic `BaseModel` with built-in JSON serialisation |
| **Round-trip** | Yes — `from_dict()` can reconstruct `InspectedNode` and even `KedroNode` via `to_kedro_node()` | No — snapshot is read-only; no reconstruction of live Kedro objects |
| **Entry point** | `bootstrap_project()` — requires full project setup | `inspect_project()` with `safe_context()` — works even without heavy deps |
| **Target consumers** | Documentation generation, pipeline sharing | kedro-viz, vscode-kedro, kedro-airflow, CI/CD, CLI |
| **Maturity** | Proof-of-concept (6 commits, 3 stars) | Detailed proposal with consumer analysis for 6 plugins |

---

## What `kedro-inspect` does that we don't

| Feature | Details | Should we adopt? |
|---|---|---|
| **Function signatures** | Extracts `inspect.signature()` with parameter names, kinds (POSITIONAL_ONLY, VAR_KEYWORD, etc.) | Possibly — useful for IDE tooltips and documentation generation |
| **Type hints** | Resolves `typing.get_type_hints()` for each parameter and return value | Possibly — useful for autocomplete and validation |
| **Fully qualified names** | `obj_to_fqn()` / `fqn_to_obj()` for serialising/deserialising function references | Partially — our `NodeInfo` doesn't serialise function references |
| **Parameter-to-dataset mapping** | `get_param_to_input()` maps function parameter names → dataset names using `inspect.signature().bind()` | Yes — genuinely useful for understanding how data flows into functions |
| **Round-trip reconstruction** | `to_kedro_node()` reconstructs a live `KedroNode` from the inspected representation | No — our design principle is "no live Kedro objects in output" |
| **Private API access** | Uses `node._name`, `node._namespace`, `node._inputs`, `node._outputs` | No — we should use public APIs only |

---

## What we do that `kedro-inspect` doesn't

| Feature | Details |
|---|---|
| **Lite mode / safe_context()** | Works without installing project dependencies — the core value proposition |
| **Catalog + factory pattern resolution** | Resolves `{namespace}.{name}` patterns to dataset type strings |
| **Graph edges** | Full DAG structure with source → target edges |
| **Node type classification** | Distinguishes task / data / parameters nodes |
| **Free input detection** | Identifies datasets with no producer node |
| **Resolved parameters** | OmegaConf-merged parameter values from `parameters.yml` |
| **Project metadata** | Name, path, kedro version, environments, config paths |
| **REST API** | HTTP endpoints for non-Python consumers |
| **Multi-pipeline support** | Inspects all registered pipelines in one snapshot |
| **Transcoded dataset handling** | Detects and groups transcoded versions |
| **Consumer-driven design** | Designed around kedro-viz, vscode-kedro, kedro-airflow needs |

---

## Key architectural differences

### 1. Dependency philosophy

`kedro-inspect` assumes all deps are installed — it calls `bootstrap_project()` directly and relies on pipeline modules importing successfully. If `pandas` or `sklearn` aren't installed, it fails.

Our proposal's core innovation is `safe_context()` — making inspection work **without** heavy dependencies. This is what makes it useful for deployment plugins, CI/CD, and remote scenarios.

### 2. Catalog blindness vs catalog awareness

`kedro-inspect` doesn't touch the catalog at all. It only sees nodes and their function signatures. It has no concept of dataset types, factory patterns, or catalog configuration.

Our proposal uses `CatalogConfigResolver.resolve_pattern()` to extract dataset type strings (for example, `"pandas.CSVDataset"`) without ever instantiating a dataset — the key trick that makes kedro-viz's lite mode work.

### 3. Function-level vs graph-level

`kedro-inspect` operates at the **function level** — it deeply introspects what each node function looks like (parameters, types, signatures). It's like `inspect.signature()` applied to a pipeline.

Our proposal operates at the **graph level** — it captures the pipeline DAG structure, dataset metadata, and project configuration. It's like a project X-ray.

---

## Verdict

These are **complementary, not competing** approaches. `kedro-inspect` solves a niche that our proposal doesn't yet cover well: **function-level introspection** (signatures, type hints, parameter binding). Our proposal solves the much broader problem of **safe, dependency-free project structure inspection** with consumer-driven design.

### Potential integration

The `param_to_input` mapping and function signature data from `kedro-inspect` could be valuable additions to our Phase 2 `NodeInfo` model — specifically for IDE hover information and documentation generation. However, these features require the actual function to be importable (which conflicts with lite mode), so they'd only be available in "full" mode when all project dependencies are installed.
