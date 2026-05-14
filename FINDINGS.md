# Dataset Validation with Pandera — Prototype Findings

> **Status:** Prototype complete. Context integration wired in. End-to-end smoke test passing.
> **Tech design:** 22 Apr 2026 — notes in [kedro#5391 comment](https://github.com/kedro-org/kedro/issues/5391)
> **KEP:** [KEP-7] Dataset Validation Using Pandera (link TBD)
> **Branch:** `prototype/validation-dataset-pandera`

## Tech Design Update (22 Apr 2026)

This document captures the **original prototype findings**. Several points were updated or corrected during the tech design session — read this section first.

### Corrections to the original findings

- **Lazy datasets** — The original findings claimed Pandera does not support Dask/Spark/Polars natively. This is **incorrect**. Pandera has native support for Polars, IBIS, Spark, and Dask (since ~0.16). The lazy datasets table below has been updated. Only truly unsupported backends need to be skipped.
- **Output validation** — Original findings deferred save-side validation. Tech design **consensus is to ship input and output validation together**. The `_ValidatingDataset` wrapper already supports `save()`; output validation needs return type hint inspection.
- **Validation timing** — Original prototype wraps datasets at catalog build time. Tech design raised that this wraps datasets not used in the current run. Production implementation should consider deferring to materialisation time, aligning with [PR #5443](https://github.com/kedro-org/kedro/pull/5443) (scoping `TypeExtractor` to the target pipeline).
- **Annotation style** — The prototype uses `def foo(df: CompaniesSchema)`. Pandera's documented convention is `def foo(df: pd.DataFrame[CompaniesSchema])`. Production implementation should support both and investigate compatibility issues reported in other frameworks (e.g. Dagster).

### Open questions raised during tech design

- Should validation be opt-out (per-dataset or project-level flag) as well as opt-in? — Defer for v1, design so it can be added later.
- Schema conflicts: warn or hard error? Per-node or per-dataset schemas? — Needs real-world user examples.
- Does catalog creation inside hooks (e.g. kedro-telemetry) trigger validation multiple times? — Needs verification.
- When and how to engage Niels (Pandera creator) for collaboration?

---

## Approach

This prototype extends Kedro's existing parameter validation framework to also handle **dataset validation** using [Pandera](https://pandera.readthedocs.io/) `DataFrameModel` schemas. The core idea: if a node function's input is annotated with a Pandera `DataFrameModel` subclass, the framework automatically validates the DataFrame against that schema at load time.

### How it extends parameter validation

| Aspect | Parameter Validation (existing) | Dataset Validation (new) |
|---|---|---|
| **Type hint target** | `params:` inputs | Regular dataset inputs |
| **Schema type** | Pydantic models, dataclasses | Pandera `DataFrameModel` |
| **Validation function** | `instantiate_model()` | `validate_dataframe()` |
| **Error type** | `ParameterValidationError` | `DataValidationError` |
| **Helper** | `is_pydantic_class()` | `_is_pandera_model()` |
| **Discovery** | `TypeExtractor.extract_types_from_pipelines()` | `TypeExtractor.extract_dataset_schemas()` |
| **When it runs** | At context init (`_get_validated_params`) | At dataset load time (proposed) |

Both flows share `TypeExtractor` and its `_build_dataset_to_arg_mapping()` helper. The parameter path inspects `params:` inputs; the dataset path inspects everything else.

## Architectural Fit

### What works well

1. **Natural extension** — `TypeExtractor` already walks pipeline nodes and maps dataset names to function arguments. Adding a second extraction method that filters for Pandera types instead of `params:` types is minimal code (~50 lines).

2. **Same opt-in pattern** — Just as parameter validation only activates when a user adds a Pydantic/dataclass type hint, dataset validation only activates when a user adds a Pandera type hint. Existing pipelines are completely unaffected.

3. **Graceful fallback** — If pandera is not installed, `_is_pandera_model()` returns `False` and no schemas are discovered. Zero overhead, no import errors.

4. **Parallel naming conventions** — The new code follows the same naming and structural patterns as the existing validation framework, making it predictable for contributors.

### Integration point

The proposed integration (shown in `examples/context_integration.py`) wraps matching catalog datasets with a `_ValidatingDataset` that calls `validate_dataframe()` on `load()`. This means:

- Validation happens at the I/O boundary, before data enters the node
- No hooks needed — it's part of the data loading path
- The catalog object itself manages validated datasets

## How Parameter and Dataset Validation Coexist

A single node can have both:

```python
def train(companies: CompaniesSchema, params: TrainingParams) -> pd.DataFrame:
    ...
```

- `TypeExtractor.extract_types_from_pipelines()` finds `params:model_options → TrainingParams` (skips non-`params:` inputs)
- `TypeExtractor.extract_dataset_schemas()` finds `companies → CompaniesSchema` (skips `params:` inputs)

They are independent — both can run on the same pipeline without conflict.

## Interaction with Lazy Datasets

> **Updated 22 Apr 2026** — The earlier draft of this section overstated the materialisation problem. Pandera has native support for most lazy backends. Only truly unsupported backends need to be skipped.

### Backend support matrix

| Backend | Pandera support | Notes |
|---|---|---|
| **pandas** | ✅ Full | Already in-memory, validation is cheap |
| **Polars** | ✅ Native (incl. lazy) | [pandera.readthedocs.io/en/latest/polars.html](https://pandera.readthedocs.io/en/latest/polars.html) |
| **IBIS** | ✅ Native (lazy by default) | [pandera.readthedocs.io/en/latest/ibis.html](https://pandera.readthedocs.io/en/latest/ibis.html) |
| **Spark (PySpark SQL)** | ✅ Native (runs inside Spark) | [pandera.readthedocs.io/en/latest/pyspark_sql.html](https://pandera.readthedocs.io/en/latest/pyspark_sql.html) — added ~0.16 |
| **Dask** | ✅ Native | [pandera.readthedocs.io/en/latest/dask.html](https://pandera.readthedocs.io/en/latest/dask.html) |
| **Other / unknown** | ⚠️ Skip with warning | Detect at load time, log, skip validation |

### Recommendation

For the production implementation, do **not** restrict validation to pandas only. Detect the DataFrame type at load time and dispatch to the appropriate Pandera backend. Only skip validation for genuinely unsupported types (with a clear warning).

There's also ongoing work in Pandera on a [Narwhals](https://narwhals-dev.github.io/narwhals/)-based integration that would make most of these supported with a single, lazy-by-default code path.

## Developer Experience

### Good

- **Just add a type hint** — No configuration, no hooks, no catalog changes. Import your schema, annotate your function, done.
- **Full error collection** — `lazy=True` means all validation errors are reported at once, not just the first one.
- **IDE support** — Type hints give autocompletion and static analysis benefits for free.
- **Discoverable** — `TypeExtractor` can report all discovered schemas, making it easy to audit what's validated.

### Could be better

- **Schema location** — Users need to define schemas somewhere and import them. No auto-generation from catalog metadata.
- **Output validation (this prototype)** — The prototype only validates on `load()`. Tech design consensus is to ship save-side validation in the production implementation.

## Limitations and Trade-offs

1. **Runtime only** — Validation happens when data is loaded, not at pipeline compile time. Schema mismatches are caught during execution, not before.
2. **Performance** — Adds validation overhead to every `load()` call for annotated datasets. For large DataFrames, this could be noticeable.
3. **Pandera dependency** — While optional, users must install pandera separately. It's not a small dependency.
4. **Save-side validation not in this prototype** — Output validation would require inspecting return type hints and wrapping `save()`. Will be implemented in the production version.
5. **Schema conflicts** — If two pipelines use different schemas for the same dataset name, the last one wins (same as parameter validation).

## Comparison: Type Hint vs Alternative Approaches

| Criteria | Type Hint (this prototype) | Wrapper Dataset | Hooks |
|---|---|---|---|
| **User effort** | Add type hint | Configure in catalog YAML | Register hook class |
| **Code changes** | Node signature only | Catalog config + schema file | Hook + schema file |
| **Discoverability** | High (visible in function signature) | Medium (in YAML) | Low (separate hook file) |
| **IDE support** | Full (autocompletion, type checking) | None | None |
| **Flexibility** | Schema per input | Schema per dataset | Full control |
| **Lazy dataset support** | Native (Pandera supports Polars/IBIS/Spark/Dask) | Can handle natively | Can handle natively |
| **Framework coupling** | Low (just type hints) | High (custom dataset class) | Medium (hook API) |
| **Reuse across projects** | Share schema modules | Share dataset classes | Share hook classes |

## Recommendation

The type hint approach is the best fit for Kedro's direction because:

1. **Consistency** — It mirrors the existing parameter validation pattern exactly, creating a unified "type hints drive validation" story.
2. **Minimal friction** — Users already write type hints for IDE support; making them functional is a natural upgrade.
3. **Opt-in by default** — No performance or behavioural impact on existing pipelines.
4. **Composable** — Works alongside parameter validation, custom datasets, and hooks without conflict.

### Suggested next steps

1. ✅ **Context integration** — Done. `_apply_dataset_validation()` wired into `KedroContext._get_catalog()`.
2. **Backend dispatch** — Detect DataFrame type at load time and use the appropriate Pandera backend (Polars, IBIS, Spark, Dask, pandas). Only skip with a warning for truly unsupported types.
3. **Output validation** — Inspect return type hints to validate node outputs on `save()`. Tech design consensus is to ship this alongside input validation.
4. **Schema discovery caching** — Cache `extract_dataset_schemas()` results so it runs once per session, not on every catalog access.
5. **Optional dependency packaging** — Add `pandera` to `pyproject.toml` under an `[extras]` group (e.g., `kedro[validation]`).
6. **Investigate annotation styles** — Support both `df: CompaniesSchema` (direct) and `df: pd.DataFrame[CompaniesSchema]` (Pandera convention). Check for Dagster-style compatibility issues.
7. **Materialisation-time validation** — Explore deferring validation from catalog build time to materialisation time, aligning with [PR #5443](https://github.com/kedro-org/kedro/pull/5443) (target pipeline scoping).
8. **Reintroduce `SourceFilter` abstraction** — Originally deferred in [PR #5404](https://github.com/kedro-org/kedro/pull/5404) as premature. Now that two mirrored filter paths exist in `TypeExtractor`, the abstraction is justified.
9. **Move `DataValidationError` to `exceptions.py`** — Currently lives in `dataset_validator.py`. Should sit alongside `ParameterValidationError` and `ModelInstantiationError`.
