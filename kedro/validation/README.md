# Kedro Validation Framework

The `kedro.validation` package provides type-hint-driven validation for Kedro pipelines. It currently supports two paths:

1. **Parameter Validation** — validates `params:` inputs against Pydantic models or dataclasses (existing, shipped via [KEP-1](https://github.com/kedro-org/kedro/discussions/5234)).
2. **Dataset Validation** — validates DataFrames against Pandera `DataFrameModel` schemas (prototype, this branch).

Both paths share the same discovery mechanism (`TypeExtractor`) and follow the same pattern: **type hints on node function signatures drive validation.**

---

## Status

This branch (`prototype/validation-dataset-pandera`) contains the **dataset validation prototype**.

| Component | Status |
|---|---|
| Type-hint discovery for Pandera schemas | ✅ Implemented |
| `_ValidatingDataset` wrapper (load-side) | ✅ Implemented |
| `KedroContext._get_catalog()` integration | ✅ Implemented |
| Unit tests (30 validation + 44 context, all passing) | ✅ Implemented |
| End-to-end smoke test with real DataCatalog | ✅ Passing |
| Save-side (output) validation | ⏳ Planned for production |
| Backend dispatch (Polars, IBIS, Spark, Dask) | ⏳ Planned for production |
| Schema discovery caching | ⏳ Planned for production |
| Optional dependency packaging (`kedro[validation]`) | ⏳ Planned for production |

See [`FINDINGS.md`](../../FINDINGS.md) for the full architectural write-up and tech design notes.

---

## Quick Example

```python
# schemas.py
import pandera as pa

class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(nullable=False, unique=True)
    company_rating: float = pa.Field(ge=0, le=1)

    class Config:
        strict = False
```

```python
# nodes.py
def preprocess_companies(companies: CompaniesSchema) -> pd.DataFrame:
    # CompaniesSchema is validated automatically at load time.
    # No hooks, no catalog config, no decorators.
    return companies
```

Running `kedro run` triggers validation when `companies` is loaded. Failures raise `DataValidationError` listing every problem (Pandera `lazy=True`).

---

## Architecture

### Files

| File | Role |
|---|---|
| [`type_extractor.py`](type_extractor.py) | Shared discovery — walks pipeline nodes, reads type hints. `extract_types_from_pipelines()` finds Pydantic/dataclass params; `extract_dataset_schemas()` (NEW) finds Pandera datasets. |
| [`parameter_validator.py`](parameter_validator.py) | Parameter validation orchestrator. Existing. |
| [`model_factory.py`](model_factory.py) | Instantiates Pydantic models and dataclasses from raw config. Existing. |
| [`dataset_validator.py`](dataset_validator.py) | Dataset validation — `validate_dataframe()`, `_is_pandera_model()`, `_ValidatingDataset` proxy wrapper, `DataValidationError`. NEW. |
| [`exceptions.py`](exceptions.py) | `ParameterValidationError`, `ModelInstantiationError`. (`DataValidationError` currently lives in `dataset_validator.py` — to be moved.) |
| [`utils.py`](utils.py) | Helpers (`is_pydantic_class`, `get_typed_fields`). |

### Integration point

Dataset validation is wired into `KedroContext._get_catalog()` via the new method [`_apply_dataset_validation()`](../framework/context/context.py). This runs after the catalog is built and parameters are added, but before `after_catalog_created` hooks fire.

```python
def _get_catalog(self, ...) -> CatalogProtocol:
    catalog = catalog_class.from_config(...)              # existing
    parameters = self._get_parameters()                    # existing
    for param_name, param_value in parameters.items():
        catalog[param_name] = param_value                  # existing
    self._apply_dataset_validation(catalog)                # NEW
    _validate_transcoded_datasets(catalog)                 # existing
    self._hook_manager.hook.after_catalog_created(...)     # existing
    return catalog
```

Matching catalog datasets are replaced with `_ValidatingDataset` wrappers. The runner is unaware of this — `catalog.load()` works exactly as it does today.

---

## How parameter and dataset validation coexist

```
                        TypeExtractor (shared)
                       /                      \
                      /                        \
    extract_types_from_pipelines()     extract_dataset_schemas()
    filters FOR  params: prefix        filters OUT params: prefix
    (Pydantic/dataclass)               (Pandera DataFrameModel)
                |                                   |
                v                                   v
    ParameterValidator                 _ValidatingDataset
    instantiate_model()                validate_dataframe()
    runs at context init               runs at catalog.load() time
```

Both paths walk the same nodes and reuse the same `_build_dataset_to_arg_mapping()` helper. Same machinery, opposite filter. A single node can have both annotations without conflict:

```python
def train(companies: CompaniesSchema, params: TrainingParams) -> pd.DataFrame:
    #       ^ dataset validation            ^ parameter validation
    ...
```

---

## Running the tests

```bash
pytest tests/validation/test_dataset_validation.py -v
pytest tests/framework/context/test_context.py -v
```

All 30 validation tests and 44 context tests should pass.

---

## End-to-end smoke test

A standalone script that exercises the full chain (DataCatalog, MemoryDataset, real Pipeline, real DataFrame) with valid and invalid data is documented in the tech design notes. See [`FINDINGS.md`](../../FINDINGS.md) and the [tech design comment](https://github.com/kedro-org/kedro/issues/5391).

---

## Related links

- **KEP:** [KEP-7] Dataset Validation Using Pandera (link TBD)
- **Tech design notes:** [kedro#5391 comment](https://github.com/kedro-org/kedro/issues/5391)
- **Parent issue:** [Explore a Kedro-First Approach to Data Validation (#5390)](https://github.com/kedro-org/kedro/issues/5390)
- **Prototype issue:** [Prototype Dataset Validation Using Pandera (#5391)](https://github.com/kedro-org/kedro/issues/5391)
- **KEP-1 (precedent):** [Parameter Validation](https://github.com/kedro-org/kedro/discussions/5234)
- **Related PRs:**
  - [#5443](https://github.com/kedro-org/kedro/pull/5443) — scope `TypeExtractor` to target pipeline
  - [#5404](https://github.com/kedro-org/kedro/pull/5404) — `SourceFilter` abstraction (closed, to be revisited)
