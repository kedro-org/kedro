# [KEP-7 v2] Dataset Validation

> **This is a restructured version of KEP-7.** The original proposal (type-hint-driven validation) was paused after community feedback. This version pivots to **schema-on-dataset with a pluggable validator protocol**, as announced in the discussion thread. The original KEP is preserved in Appendix C as a rejected design.

**Context:** Explore a Kedro-First Approach to Data Validation (#5390) · Spike: Prototype Dataset Validation Using Pandera (#5391)
**Authors:** @SajidAlamQB
**KEP shepherd:** @SajidAlamQB
**Supersedes:** KEP-7 v1 (type-hint-driven dataset validation)

---

## What changed since v1 (summary for previous readers)

| | KEP-7 v1 | KEP-7 v2 (this document) |
|---|---|---|
| Schema declared | On node function signatures (type hints) | On the catalog entry (`validator:` key) |
| Discovery | `TypeExtractor` walks pipeline node signatures | `DataCatalog` parses catalog config |
| Enforcement | `_ValidatingDataset` proxy wrapper | The catalog `load()`/`save()` funnel — no wrapper |
| Backend | Pandera only | Pluggable `Validator` protocol; Pandera is the reference implementation |
| Validates on | Load only | Load **and** save |
| Schema conflicts | Last-wins silently (known bug) | Impossible by construction: one entry, one validator |
| Outside pipeline runs | Not addressed | Public `validate_dataset()` API + `kedro catalog validate` CLI |
| Opt-out | Deferred | `DATASET_VALIDATION` setting + `KEDRO_DATASET_VALIDATION` env var |
| Node type hints | The validation driver | Optional documentation (`pd.DataFrame[Schema]` stays valid, no longer load-bearing) |

This pivot directly addresses the feedback from @deepyaman (schema-on-dataset, save-side validation, catalog inspectability, why-not-hooks), @noklam (global disable + programmatic API for IDE diagnostics), and @Adeikalam (schemas-next-to-nodes create cross-pipeline coupling).

---

## What are we trying to do?

Introduce native dataset validation in Kedro, declared in the catalog:

```yaml
# conf/base/catalog.yml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
  validator: spaceflights.schemas.companies.CompaniesSchema
```

```python
# src/spaceflights/schemas/companies.py
import pandera.pandas as pa


class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(nullable=False, unique=True)
    company_rating: float = pa.Field(ge=0, le=1)

    class Config:
        strict = False
```

```python
# nodes.py — plain Python, no validation machinery
import pandas as pd


def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    companies["iata_approved"] = companies["iata_approved"].map({"t": True, "f": False})
    return companies
```

When any code calls `catalog.load("companies")` — a pipeline run, a notebook, the IDE extension, CI — the loaded DataFrame is validated against `CompaniesSchema` before it is returned. When a node output is saved, the data is validated **before** it is written, so invalid data never lands on disk. Failures raise `DataValidationError`, reporting every failed check at once (Pandera `lazy=True`), naming the dataset, the validator, and the mode (load/save).

The catalog entry is the single source of truth: **one dataset, one validator, by construction**. The "two pipelines annotate the same dataset and the last one silently wins" bug from v1 cannot occur, because the binding is a YAML mapping key, not an iteration over pipelines.

### User stories (who is this for?)

1. **A pipeline team ingesting third-party data** declares a contract on the raw dataset; a malformed supplier file fails at the I/O boundary with a complete failure report, before any node runs.
2. **The Kedro VSCode extension** (@noklam) calls `validate_dataset(catalog, name)` and renders the returned structured failures as editor diagnostics — no run, no raised exception.
3. **A CI job** runs `kedro catalog validate --resolve-only` to catch typo'd validator paths and missing dependencies on every PR, and (optionally) full data validation on a schedule.
4. **Kedro-Viz** surfaces declared schemas statically via `catalog.to_config()` and `catalog.validators` — no execution needed.
5. **Plugin authors** (Great Expectations, Pydantic, custom in-house checks) implement one small protocol and slot into the same `validator:` key.

## What this is not

- **Not a breaking change.** No annotation/key → no validation → zero behaviour change. The `validator:` key is new and reserved; everything else is untouched.
- **Not a replacement for hooks.** Hooks remain fully supported and fire in exactly the same places; see Appendix B for the detailed hooks analysis.
- **Not a mandatory Pandera dependency.** Pandera ships via optional, per-backend extras that forward to Pandera's own — `pip install "kedro[pandera-pandas]"` (or `pandera-polars`); see Packaging. v1 is opinionated about Pandera as the primary backend while keeping the `Validator` protocol open to others.
- **Not node-level function contracts.** Catalog validation governs *data at rest* (what is loaded/saved under a catalog name). For *function-boundary* contracts ("everything entering this function must be numeric"), Pandera's `@check_types` on the node function remains the right, fully compatible tool. Using both on the same dataset validates twice — documented.

## How is it done today, and what are the limits of current practice?

Four ways users validate data in Kedro projects today:

1. **Hand-written hooks** (`after_dataset_loaded` / `before_dataset_saved`) referencing schemas in a separate module. Hidden control flow, low discoverability, every new dataset means editing the hook, and — crucially — dataset I/O hooks only fire inside pipeline runs (see Appendix B), so notebooks and ad-hoc `catalog.load()` calls are unguarded.
2. **The `kedro-pandera` community plugin**, which declares Pandera schemas under the catalog `metadata:` key and validates via hooks. It is essentially unmaintained today, but it proved the demand for declarative, catalog-adjacent schemas and is the direct inspiration for this KEP — we should draw on its design experience and credit it in the launch announcement. This KEP brings the idea into core with a first-class key, an enforcement point that also covers non-run access, and a backend-agnostic protocol.
3. **Pandera's `@check_types` decorator** on node functions. Couples validation to the function: it runs in every test and notebook call, and says nothing about data loaded outside that function.
4. **The unreleased KEP-7 v1 prototype** (type-hint-driven). Rejected for the reasons in Appendix C.

We will still rewrite Kedro's own `docs/integrations-and-plugins/pandera.md` to lead with `validator:` and demote the hand-rolled hook recipe to an "advanced/conditional validation" section (with a "don't double-validate the same dataset" note). No formal migration path is owed: kedro-pandera is unreleased-adjacent in practice and the v1 prototype never shipped.

## What is new in this approach, and why will it be successful?

### Architecture overview

```
conf/base/catalog.yml ("validator:" key)
        │
        ▼
DataCatalog._add_from_config()          ← parses key into _ValidatorSpec, stores it
        │                                 in catalog._validator_specs (single funnel:
        │                                 explicit entries AND resolved factory patterns)
        ▼
catalog.load("companies")
        │
        ├─► dataset.load()               ← the dataset is untouched: no wrapper,
        │                                  real type, real repr, picklable as-is
        ▼
catalog._maybe_validate(data, "load")
        │
        ├─ flag off / no spec → return data unchanged (dict-miss fast path)
        ├─ first use → resolve_validator(spec)   (lazy import, cached)
        ▼
validator.validate(data)                 ← Pandera adapter or any Validator
        │
        ├─ valid   → node receives validated (possibly coerced) data
        └─ invalid → DataValidationError(dataset, mode, structured failures)
```

Save is symmetric: `catalog.save(name, data)` validates **before** `dataset.save()` — invalid data is never persisted.

### Design decision 1: enforcement lives in the catalog `load()`/`save()` funnel — not a wrapper

> ⚠️ This deviates from the pivot announcement, which said "the wrapper mechanism carries over". During detailed design the wrapper turned out to be strictly worse, and deleting it resolves several pieces of feedback at once.

The v1 `_ValidatingDataset` proxy has structural problems that the catalog funnel does not:

- A wrapper breaks `isinstance(ds, AbstractVersionedDataset)` checks in the catalog's own version handling, must fake `_EPHEMERAL` (checked by runners) and `_SINGLE_PROCESS`, must delegate `exists()`/`release()`, and must survive `ForkingPickler` for `ParallelRunner`. The funnel touches none of this: **datasets stay exactly what the YAML says**.
- @deepyaman's repr concern is resolved by deletion, not decoration: the catalog repr shows real datasets. Validator bindings are inspectable via a read-only `catalog.validators` property, in `kedro catalog` CLI output, and round-trip through `catalog.to_config()` (which re-injects the `validator:` key — this is what lets Kedro-Viz surface schemas statically).
- `Task` calls `catalog.load`/`catalog.save` ([task.py:152, 186](kedro/runner/task.py)), and so do notebooks, `kedro ipython`, plugins, and CI scripts — one enforcement point covers all of them. (What it does **not** cover is enumerated honestly below under "Raw-access surface".)
- Hook ordering becomes deterministic: `before_dataset_loaded` → `catalog.load` (validates) → `after_dataset_loaded` **always observes validated data**. If validation were itself a hook, that guarantee would depend on pluggy registration order.

Cost (honest): ~25 LOC in `kedro/io`, Kedro's most stable module, on the hottest path. Mitigations: the disabled/no-spec path is a dict miss; `kedro.validation` is imported lazily inside `_maybe_validate`; a micro-benchmark of the no-op path ships with the PR (see Performance).

```python
# data_catalog.py (sketch)
def load(self, ds_name, version=None):
    ...                                   # existing get() + logging
    return self._maybe_validate(ds_name, dataset.load(), mode="load")

def save(self, ds_name, data):
    dataset = self[ds_name]
    ...
    dataset.save(self._maybe_validate(ds_name, data, mode="save"))

def _maybe_validate(self, ds_name, data, mode):
    if not self._validation_enabled():    # settings/env, see "Opt-out"
        return data
    spec = self._validator_specs.get(ds_name)
    if spec is None or mode not in spec.on or not spec.enabled:
        return data
    from kedro.validation import resolve_validator  # lazy import
    validator = self._validators.get(ds_name) or self._validators.setdefault(
        ds_name, resolve_validator(spec)
    )
    try:
        return validator.validate(data)
    except DataValidationError as exc:
        exc.dataset_name, exc.mode = ds_name, mode          # funnel enrichment
        exc.args = (f"Validation failed for dataset '{ds_name}' on {mode}: {exc}",)
        if spec.severity == "warn":
            logger.warning(...); return data
        raise
    except Exception as exc:                                 # contract: any raise == failure
        wrapped = DataValidationError(str(exc), dataset_name=ds_name, mode=mode, ...)
        if spec.severity == "warn":
            logger.warning(...); return data
        raise wrapped from exc
```

Two contracts the funnel defines (both pinned by tests):

- **Any exception raised from `validate()` is a validation failure.** Custom validators may raise `ValueError`, `pydantic.ValidationError`, anything — the funnel normalises to `DataValidationError` with the dataset name and mode attached. The `errored` status (see API) is reserved exclusively for failures *before* `validate()` is invoked (import errors, dataset load errors).
- **Validators MAY transform data.** Pandera with `coerce=True` returns a coerced frame; the coerced frame is what the node receives (load) and what is persisted (save). This is a documented, prominent contract — see Risks for the hook-observability asymmetry it creates.

### Design decision 2: the `validator:` key — syntax

`validator:` becomes a **reserved top-level dataset-config key**, a peer of `type:`/`versioned:`/`credentials:`/`metadata:`. Two forms:

```yaml
# Shorthand: dotted import path to a Pandera schema (or any Validator)
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
  validator: spaceflights.schemas.companies.CompaniesSchema

# Long form: full control
reviews:
  type: pandas.ParquetDataset
  filepath: data/02_intermediate/reviews.parquet
  validator:
    class: spaceflights.schemas.reviews.ReviewsSchema
    on: [save]                 # subset of [load, save]; default: both
    severity: error            # error (default) | warn — warn logs and continues
    enabled: true              # per-dataset kill switch (default true)
    skip_load_after_save: true # opt-in: skip load validation if THIS process
                               # already save-validated this dataset (see below)
    options:                   # forwarded to the adapter/constructor
      lazy: true               # PanderaValidator: lazy error collection (default)
      # head/tail/sample/random_state are forwarded to schema.validate() —
      # the v1 cost knob for large frames (validates a subset, documented trade-off)

# Dataset factory: one validator covers every match; {placeholder}
# interpolation works inside validator strings (resolver formats all strings
# before the spec is captured)
"{partner}_shuttles":
  type: pandas.ExcelDataset
  filepath: data/01_raw/{partner}_shuttles.xlsx
  validator: spaceflights.schemas.shuttles.ShuttlesSchema

# Non-tabular custom validator: any class exposing validate(data) -> data
model_metrics:
  type: json.JSONDataset
  filepath: data/08_reporting/metrics.json
  validator:
    class: spaceflights.schemas.metrics.MetricsValidator
    options:
      required_keys: [accuracy, f1]
```

**Parsing.** `DataCatalog._add_from_config()` is the single funnel through which both explicit entries and lazily-resolved factory patterns pass. The key is captured into `catalog._validator_specs[name]` and a **cleaned copy** of the config (without `validator:`) proceeds to dataset instantiation — the resolver's own config store is *not* mutated, so `kedro catalog resolve` and Kedro-Viz keep seeing consistent, validator-bearing configs. `parse_dataset_definition()` also defensively strips the key (mirroring the existing `metadata` pop, [core.py:250](kedro/io/core.py#L250)) so direct `AbstractDataset.from_config()` calls don't `TypeError`. A `validator:` nested inside a `CachedDataset` `dataset:` block is a **configuration error** with a fix-it message ("declare it on the top-level entry") — not a silent strip; the user declared validation and must not silently lose it. We will audit kedro-datasets for any dataset whose `__init__` takes a `validator` kwarg and document the key as reserved alongside `versioned`/`credentials`.

**Spec validation.** `_ValidatorSpec.from_config` accepts `str | dict` only; rejects unknown long-form keys (allowed: `class`, `on`, `severity`, `enabled`, `skip_load_after_save`, `options`), validates `on ⊆ {load, save}` and non-empty, and rejects a YAML *list* with "reserved for future use" — so a future per-direction list form (`validator: [{class: A, on: [load]}, {class: B, on: [save]}]`) can be added without breaking anyone. One YAML 1.1 wrinkle is handled for users: an unquoted `on` key parses as boolean `True` (the "Norway problem", and it survives the OmegaConf round-trip — verified); `from_config` normalises the `True` key back to `"on"`, so the examples above work as written, unquoted.

**Lifecycle.** The spec follows the catalog *entry*, not the name forever: explicitly replacing a dataset (`catalog["companies"] = df` in a notebook) clears its spec (no stale validator firing on the replacement); factory materialisation does **not** clear it. Both behaviours are pinned by tests.

### Design decision 3: schemas live in `src/<package>/schemas/`, referenced by import path

Schemas are code, in one conventional place — the analogue of `conf/<env>/parameters.yml` for parameters:

```
src/spaceflights/
├── pipelines/
└── schemas/
    ├── __init__.py
    └── companies.py        # CompaniesSchema
```

The catalog references them by **full dotted import path**, resolved with the existing `kedro.utils.load_obj`. Convention, not magic: no implicit module prefixes, so paths are grep-able (@Adeikalam's discoverability point) and unambiguous. Contract: a validator path must reference a **top-level attribute of an importable module** (which is exactly what the convention produces; nested classes and notebook-defined `__main__` schemas are rejected with a hint). The spaceflights starters scaffold the folder with one example schema and a commented-out `validator:` line; other starters are unchanged.

**Resolution is lazy with an eager pre-flight.** At catalog build, specs are parsed (string handling only — no imports, no pandera, no startup cost, and factory entries work naturally). The actual import happens at first load/save or API call. To avoid a typo surfacing hours into a run, catalog build runs a near-zero-cost pre-flight: `importlib.util.find_spec()` on each spec's **top-level** package — a miss is a WARNING by default and an immediate error under `DATASET_VALIDATION = "strict"`. This is the same pattern Kedro already uses elsewhere (e.g. the optional-`rich` checks at [project/\_\_init\_\_.py:257](kedro/framework/project/__init__.py#L257) and [ipython/\_\_init\_\_.py:53](kedro/ipython/__init__.py#L53), and the `settings.py` pre-flight at [project/\_\_init\_\_.py:368](kedro/framework/project/__init__.py#L368)), so it is consistent and proven. `find_spec` locates a spec via the import finders without executing module code; checking only the top-level package (`class_path.split(".")[0]`) avoids the one caveat — `find_spec` on a *sub*module imports its parent package. The complete fail-fast gate is `kedro catalog validate --resolve-only` in CI.

### Design decision 4: a minimal pluggable `Validator` protocol

```python
# kedro/validation/core.py — no pandera import at module level
@runtime_checkable
class Validator(Protocol):
    """Validate data, returning it (possibly transformed) or raising on failure.

    Any exception raised is treated as a validation failure. ``validate()``
    may be called concurrently from multiple threads; implementations must be
    thread-safe or stateless.
    """

    def validate(self, data: Any) -> Any: ...
```

Resolution order (deliberate, in this order — see Appendix A for why):

1. **Adapters** (v1: the Pandera adapter; later a `kedro.validators` entry-point group) get first refusal on the imported object.
2. **A class** is instantiated with `options` and the *instance* is protocol-checked. A class object is never duck-typed directly — `isinstance(SomeClass, runtime_checkable_protocol)` is true for any class merely *defining* a `validate` method, which would silently return the uninstantiated class and drop `options`.
3. **A non-class instance** (e.g. a module-level `pa.DataFrameSchema.from_yaml(...)` result) is protocol-checked; `options` on instances are a config error (they cannot be applied).
4. Anything else → `ValidationConfigurationError` naming the dataset, the path, and what was found.

**The Pandera reference adapter** handles real-world Pandera, not just the legacy import style:

- **v1 is built and tested against pandas and Polars** — the backends with standard raise-on-failure semantics and the most complete check coverage.
- Detection covers `pandera.pandas`, `pandera.polars`, and `pandera.pyspark` `DataFrameModel`/`DataFrameSchema` (the top-level `pandera.DataFrameModel` is deprecated as of pandera 0.24 and slated for removal — detecting only that, as the prototype did, would miss every modern schema).
- **pyspark is experimental in v1, not advertised support** (per review). Pandera's pyspark backend behaves unlike the others: `schema.validate(df)` does *not* raise — it returns the frame with errors on `df.pandera.errors` — and it lacks element-wise checks, row sampling, and `drop_invalid_rows`. The adapter does inspect the accessor and raise `DataValidationError` so failures aren't a silent false-green, but we will **confirm before launch** whether to promote it, gated on the maturing Narwhals-backed backend (Pandera #1894 / 0.32.x, not yet on PyPI as of 0.31.1) that aims to unify check coverage and laziness across Polars/Ibis/pyspark.
- **polars `LazyFrame`:** Pandera validates lazy frames at schema-only depth by default (data-level checks silently skipped). The adapter logs a one-time warning per dataset naming the depth actually applied, and offers `options: {collect: true}` (validates `data.collect()`, returns the original LazyFrame). Docs recommend validating eagerly at `on: [save]` of the materialising producer.
- `head`/`tail`/`sample`/`random_state` options are forwarded to `schema.validate()` in v1 as the large-frame cost knob. Unknown options are a **configuration error** naming the option and adapter version — not a silently-ignored "reserved" no-op.
- `SchemaErrors.failure_cases` is mapped into structured, *grouped* failures (see `CheckFailure` in Appendix A) with capped row examples — error messages stay bounded on million-row frames; the full Pandera report remains available as `err.__cause__`.

A worked Great Expectations adapter sketch and a non-tabular metrics validator are in Appendix A — the protocol was adversarially checked against both, plus a Pydantic per-row validator.

### Design decision 5: save-side semantics

- Save validation runs **before** `dataset.save()`: invalid data is never written.
- **Validated-on-save does not automatically skip revalidation-on-load.** Persistence round-trips are not identity-preserving (CSV drops dtypes) — an automatic skip would certify data the schema never saw.
- The explicit, scoped answer to @deepyaman's "if you wrote it, don't revalidate" point is the opt-in **`skip_load_after_save: true`** flag: a per-catalog-instance set (never pickled, cleared on `release()`) records save-validated datasets, and load validation is skipped only when *this process* wrote the data. Unlike `on: [save]`, this stays safe under partial runs (`kedro run --from-nodes B` loads data this run never wrote → validates normally). Recommended for round-trip-faithful formats (Parquet); a future extension can key on `save_version` for cross-process caching.
- **Generator (chunked) nodes:** the runner saves once per chunk, so save-side validation runs **per chunk**. Cross-chunk invariants (`unique`, frame-level checks) are NOT enforced across chunks — documented honestly, with the recommendation to use `on: [load]` for chunk-appended outputs (the whole persisted dataset is validated on next read). Per-chunk semantics are pinned by a test so they're contractual, not accidental.

### Design decision 6: opt-out and the kill switch

```python
# settings.py
DATASET_VALIDATION = True   # True (default) | False | "warn" | "strict"
```

- `True` — validation on; lazy resolution; pre-flight warns on missing packages.
- `False` — runtime validation off everywhere (the funnel short-circuits before any import; disabled == zero cost). Explicit API calls still validate (see below).
- `"warn"` — like `True`, but *configuration* errors (unresolvable validator, e.g. an intentionally slimmed serving image) downgrade to a WARNING and skip. Data validation failures still raise. (Per-dataset failure-tolerance is the `severity: warn` key, not this.)
- `"strict"` — like `True`, plus all declared validators (including pattern-level ones) are resolved eagerly at catalog build; any resolution failure fails the session immediately.

The setting is validated at load (`is_in (True, False, "warn", "strict")`) — a typo is a settings error, never silently-enabled-by-truthiness. Named `DATASET_VALIDATION` rather than the earlier-floated `VALIDATION_ENABLED` to stay disjoint from KEP-1 parameter validation.

*Symmetry with parameter validation:* KEP-1 parameter validation currently has **no** opt-out flag — it always runs ([context.py](kedro/framework/context/context.py) `_get_validated_params`). Dataset validation is the first to get one. Whether to add a matching `PARAMETER_VALIDATION` flag for symmetry is a reasonable follow-up but is out of scope here.

**Env var:** `KEDRO_DATASET_VALIDATION=0|false|1|true|warn|strict` is read directly in `_maybe_validate` (precedent: `KEDRO_MP_CONTEXT` is read inside `kedro/runner`), and **wins over settings in both directions**. Reading it in `kedro.io` (which never imports framework settings) makes the emergency kill switch govern *every* catalog instance — including catalogs rebuilt from config inside plugin hooks (the kedro-telemetry pattern) and bare `DataCatalog.from_config()` in notebooks.

**Default for standalone catalogs:** `DataCatalog` itself defaults `validation_enabled=True` — declared config is honoured everywhere by least surprise; `KedroContext` overrides it per settings/env. A catalog rebuilt inside a hook therefore validates independently and idempotently (validation is per-`load()` call; there is no wrapping, so there is nothing to double-apply — pinned by a kedro-telemetry-shaped regression test).

**Custom `DATA_CATALOG_CLASS`:** the funnel members are explicitly **not** added to `CatalogProtocol` (adding members to a `runtime_checkable` protocol would instantly fail settings-load for every existing custom catalog — a breaking change). Instead, at context catalog-creation, if validation is enabled and specs exist but the catalog class lacks the funnel (`hasattr` check), Kedro logs a prominent WARNING that declared validators will be ignored — converting silent degradation into a diagnosable one. `SharedMemoryDataCatalog` inherits the funnel; a regression test asserts validators fire inside `ParallelRunner` workers.

### Design decision 7: the programmatic API (IDEs, notebooks, CI)

```python
from kedro.validation import validate_dataset, validate_catalog

result = validate_dataset(catalog, "companies")   # never raises for outcomes
if not result:
    for f in result.failures:
        print(f.column, f.check, f.failure_count, f.failure_examples)
```

(Named `validate_dataset` — simpler than `validate_catalog_dataset`, and unambiguous next to the batch `validate_catalog`.) Full signatures and dataclasses in Appendix A. Key semantics (the full behaviour matrix is in Appendix A):

- **Explicit calls always validate** — they ignore the global flag *and* per-dataset `enabled: false` (one consistent rule), with the result carrying the enabled-state so IDEs can grey out rather than red-flag.
- Returns `ValidationResult` with `status ∈ {passed, failed, skipped, errored}` plus a machine-readable `error_type` (`missing_dependency` / `unresolvable_validator` / `dataset_error`) so the VSCode extension can collapse "pandera not installed" into one workspace notice instead of painting every dataset red.
- **`data` is optional and never written by the user** — omit it and the dataset is loaded via `catalog.get(name).load()` (raw, bypassing the funnel, so the API never double-validates). An internal sentinel distinguishes "not passed" from an explicit `None` (literal `None` is validatable data — e.g. the JSON metrics example), so users never see or type the sentinel. `version=` passes through to versioned datasets. `on="save"` requires explicit `data` (validating loaded data against save rules is meaningless).
- `raise_if_failed()` converts back to raising semantics in one call; validated/coerced data is exposed on the result.
- `validate_catalog(catalog)` batch-validates; **factory-pattern entries are included** by resolving patterns against project pipelines (the mechanism `kedro catalog resolve` already uses) — without this, the CI gate would silently skip exactly the lazily-resolved entries that most need it.

### The CLI: `kedro catalog validate`

```
kedro catalog validate [--resolve-only] [--pipeline <name>] [dataset ...]
```

- `--resolve-only`: imports and resolves every declared validator (explicit + pattern-level) without loading data — the cheap CI typo/dependency gate that lazy runtime resolution gives up. Non-zero exit on any `errored`.
- Full mode loads and validates (bounded by `--pipeline` / explicit names; full-data validation across a large catalog is unbounded cost — docs recommend resolve-only as the default CI gate).
- Reports, per dataset, which validator resolved *and from where* (entry vs pattern, config source) — making environment-overlay validator loss visible (see Risks).
- Reports `skipped: no validator` for pipeline datasets without one — which also surfaces the namespace gap (a validator on `companies` does not match a namespaced `ns.companies`; the recipe is a `"{namespace}.companies"` pattern entry).

### What this looks like end to end

```
$ kedro run
...
DataValidationError: Validation failed for dataset 'companies' on load
(validator: spaceflights.schemas.companies.CompaniesSchema, declared in conf/base/catalog.yml)
3 checks failed across 2 columns — 4,210 failure cases:
  - company_rating: greater_than_or_equal_to(0) — 4,208 cases (e.g. -0.5 @ row 17, -1.2 @ row 102, ...)
  - company_rating: less_than_or_equal_to(1)    — 1 case   (e.g. 4.2 @ row 33)
  - id: field_uniqueness                        — 1 case   (e.g. 10542 @ rows 88, 91)
(full Pandera report: raise ... from SchemaErrors, available as __cause__)
```

## Key features and benefits

- **One schema per dataset, by construction.** The silent-conflict bug class is gone, not mitigated.
- **Validation everywhere data flows through the catalog**: pipeline runs, notebooks, `kedro ipython`, plugins, the programmatic API — not just runner-mediated loads.
- **No wrapper**: datasets keep their identity, repr, pickling, and `isinstance` behaviour. Catalog inspection stays honest.
- **Save and load in v1**, with invalid data never written.
- **Pluggable**: Pandera is ~200 LOC of adapter against a public protocol; GX/Pydantic/custom/non-tabular validators are implementable today and become installable adapters via a `kedro.validators` entry-point group in v1.x.
- **Fully opt-in, cheaply opt-out**: no key → no cost; `DATASET_VALIDATION=False` or the env var → zero-cost short-circuit.
- **Foundation**: `to_config()` round-trip + `catalog.validators` unlock Kedro-Viz schema display and schema-driven catalog docs without further core changes.

### One schema across many datasets (@deepyaman's training-node example)

Within one catalog file, declare once and reference per dataset via a YAML anchor (the leading `_` key is dropped by `OmegaConfigLoader` after merge — verified at `omegaconf_config.py:384`):

```yaml
_all_numeric: &all_numeric
  class: spaceflights.schemas.shared.AllNumericFeatures

X_train: {type: pandas.ParquetDataset, filepath: ..., validator: *all_numeric}
X_test:  {type: pandas.ParquetDataset, filepath: ..., validator: *all_numeric}
```

Honest scope: **anchors are per-file** (Kedro's multi-file catalog convention means cross-file sharing is "repeat the one-line dotted path" — which is grep-able, the design's own virtue — or a dataset factory pattern where naming permits, e.g. `"{name}_model_input":`). The cost versus v1's single node annotation is N one-line references instead of 1 — deliberate, because per-dataset declaration is exactly what kills last-wins conflicts and cross-pipeline coupling. For genuinely *function-shaped* contracts, `@check_types` on the node remains the right tool.

### YAML-defined Pandera schemas work in v1

Because the adapter accepts `DataFrameSchema` *instances*, a module-level

```python
# src/spaceflights/schemas/companies_yaml.py
import pandera.pandas as pa
schema = pa.DataFrameSchema.from_yaml(Path(__file__).parent / "companies.yml")
```

referenced as `validator: spaceflights.schemas.companies_yaml.schema` works with zero new code (caveats documented: Pandera YAML is pandas-only and serialises registered checks only). A `PanderaYamlValidator(schema_file=...)` convenience with package-relative path resolution is v1.x sugar, not a v1 dependency.

## What are the risks?

Consolidated register — each with its mitigation:

1. **Core surface area on the hottest path.** ~25 LOC in `DataCatalog.load/save`. Mitigated: dict-miss fast path, lazy imports, and a published no-op-path micro-benchmark (see Performance). Any funnel bug affects every load/save — hence the test matrix below.
2. **Raw-access bypass surface (by design).** `catalog.get(name).load()`, `catalog[name].load()`, and direct dataset access bypass validation — this *is* the raw path the API needs. **Kedro-Viz previews call `dataset.preview()` directly and are NOT validated** — Viz benefits are static surfacing, not validated previews. Documented loudly as the contract.
3. **Coercion changes data identity.** With `coerce=True`, nodes receive and disk receives the coerced frame — a behaviour change when adding a validator to an existing pipeline. Prominent docs + release-notes callout.
4. **Hook observability asymmetry.** `after_dataset_saved` receives the runner-local *pre-coercion* object ([task.py:183-188](kedro/runner/task.py#L183-L188)); what was persisted may differ. Contract documented: *dataset I/O hooks observe pre-validation data on save and post-validation data on load*; lineage/profiling plugins needing persisted truth must read back. Pinned by a test.
5. **`save_args` blind spot.** The schema validates what the node produced, not what dataset-side save processing writes to disk. Documented limitation.
6. **Environment-overlay validator loss.** A `conf/local` override of an entry that omits `validator:` drops the base validator under destructive merge — same genus as last-wins, now at config level. Mitigations: `kedro catalog validate` reports which validator resolved and from where; a resolve-time warning when an explicit entry shadows a pattern that carries a validator; docs recommend declaring validators in `base` and overriding with `enabled: false` rather than re-declaring entries.
7. **Custom catalog degradation.** Covered above: `hasattr` warning at context creation; funnel members deliberately kept out of `CatalogProtocol`.
8. **Mid-run config errors despite pre-flight.** `find_spec` catches missing packages, not bad attribute names. `kedro catalog validate --resolve-only` in CI and `"strict"` mode close the gap for teams that want build-time failure.
9. **Lazy/distributed backends.** Load-side validation triggers Spark actions / forces evaluation inside `catalog.load()` — changed job shape, potentially significant cluster cost. Docs ship a per-backend eager/lazy table; guidance: prefer `on: [save]` or sampled options for Spark/Dask, schema-only depth for polars-lazy. Streaming datasets are unsupported with load validation.
10. **ParallelRunner imports.** Workers re-resolve validators from string specs (`__getstate__` drops the resolved cache); schema modules must be importable in workers — already true for node functions.
11. **Import-path execution.** `validator:` imports and runs module code at first use — the same trust surface as `type:`; no *new* surface, stated for completeness.
12. **Thread concurrency.** Under `ThreadRunner`, first-use resolution may race (benign: `setdefault` keeps one instance); `validate()` may be called concurrently — protocol docstring requires thread-safety, and the GE adapter recipe shows the lock-guarded lazy-state pattern.

## Performance

Three micro-benchmarks ship with the implementation PR (numbers in the PR description, methodology in `benchmarks/`):

1. Per-call `_maybe_validate` overhead on the disabled/dict-miss path over N `MemoryDataset` loads — defends adding code to the hottest path.
2. Catalog-build spec parsing + pre-flight on a ~500-entry catalog.
3. Representative Pandera timings (1M-row frame; lazy vs eager; with/without coerce; `sample` option) — so the docs' cost guidance is evidence, not vibes.

The v1 cost knobs: `on:` narrowing, `severity: warn` during adoption, `options: {head/sample: …}`, `skip_load_after_save`, per-dataset `enabled: false`, and the global flag.

## How long will it take?

| Milestone | Scope | Estimate |
|---|---|---|
| KEP vote | this document | 2 weeks |
| PR 1 — core | `kedro/validation` package (protocol, spec, resolution, errors, `CheckFailure`), Pandera adapter (pandas/Polars; pyspark experimental), catalog funnel + lifecycle, settings/env wiring | ~1.5 weeks |
| PR 2 — surfaces | programmatic API (`validate_dataset`/`validate_catalog`), `kedro catalog validate`, context warnings | ~1 week |
| PR 3 — docs | new "Data validation" page, `pandera.md` rewrite, catalog reference (`validator:` reserved), coercion/release notes, migration tables | ~0.5 week |
| Sibling PR — kedro-starters | `schemas/` scaffold in spaceflights-pandas (+ viz variant) | ~2 days, release-coupled |
| Outreach | kedro-pandera maintainers + Pandera (Niels/Neeraj) review of the adapter contract | during PR 1–2 |

Target: next minor release. Total engineering ≈ 3–4 weeks, consistent with the original estimate.

## Testing strategy

Spec parsing (shorthand/long form/unknown keys/bad `on`/list-rejection); funnel load & save incl. hook ordering (`after_dataset_loaded` sees validated data; failed save writes nothing); coercion contracts (node receives coerced; `after_dataset_saved` sees original); generator nodes per-chunk; versioned loads; transcoded entries (per-entry validators — `companies@pandas`/`@spark` are separate entries, a feature since Pandera schemas are backend-specific); factory interpolation in validator strings; pattern materialisation keeps specs / explicit replacement clears them; `CachedDataset` top-level entries + nested-key config error; `ParallelRunner` (specs survive pickling, workers resolve and raise); `ThreadRunner` concurrent first-use; telemetry-shaped catalog-rebuild idempotence; custom-catalog `hasattr` warning; settings/env matrix incl. precedence; API status taxonomy incl. `error_type`; pyspark raise-from-accessor (experimental backend); polars depth warning; non-tabular fixture through `ValidationResult` rendering (so `column=None` can't regress the IDE/CLI renderers); `skip_load_after_save` across partial runs. ~900 test LOC.

---

## Appendix A: Proposed API changes

### User-facing (YAML)

See "Design decision 2" — `validator:` shorthand and long form. Reserved key documented alongside `versioned`/`credentials`.

### `kedro.validation` (new public package)

```python
@runtime_checkable
class Validator(Protocol):
    def validate(self, data: Any) -> Any: ...
    # Contract: return (possibly transformed) data; ANY raise == validation failure.
    # May be called concurrently; implementations must be thread-safe or stateless.


@dataclass(frozen=True)
class CheckFailure:
    """One failed check, grouped. Only `message` is required — column/check/
    index are None for non-tabular validators and renderers MUST handle that
    (file-level diagnostic, not column-anchored)."""
    message: str
    check: str | None = None
    column: str | None = None
    failure_count: int = 1
    failure_examples: list[dict] = field(default_factory=list)  # capped (default 5, via options)
    index: Any | None = None


class DataValidationError(Exception):
    dataset_name: str | None
    mode: str | None            # "load" | "save" | "api"
    validator: str | None       # class path
    failures: list[CheckFailure]

class ValidationConfigurationError(Exception): ...
# Both exported from kedro.validation; siblings (DataValidationError keeps a
# re-export shim at its old prototype location for one release).


@dataclass(frozen=True)
class ValidationResult:
    dataset_name: str
    validator: str | None
    status: Literal["passed", "failed", "skipped", "errored"]
    failures: list[CheckFailure] = field(default_factory=list)
    message: str | None = None
    reason: str | None = None            # disambiguates skipped (e.g. "validator declared for save only")
    error_type: Literal["missing_dependency", "unresolvable_validator", "dataset_error"] | None = None
    enabled: bool = True                 # per-dataset enabled-state metadata for IDEs
    data: Any | None = None              # validated/coerced data when status == "passed"
    def __bool__(self) -> bool: return self.status in ("passed", "skipped")
    def raise_if_failed(self) -> None: ...
    def to_dict(self) -> dict: ...       # JSON-safe; the IDE/CI integration contract


# internal module-level sentinel; never written by users (repr renders as "<unset>")
_UNSET = _UnsetType()

def validate_dataset(
    catalog: CatalogProtocol,
    name: str,
    data: Any = _UNSET,                  # omit => load raw via catalog.get(name).load();
                                         # sentinel distinguishes "not passed" from None
    *,
    on: Literal["load", "save"] = "load",  # on="save" requires explicit data
    version: str | None = None,
) -> ValidationResult: ...

def validate_catalog(
    catalog: CatalogProtocol,
    names: Iterable[str] | None = None,  # None => all declared validators,
                                         # incl. patterns resolved against project pipelines
) -> dict[str, ValidationResult]: ...
```

### Behaviour matrix

| `DATASET_VALIDATION` | pandera installed | `validator:` declared | `kedro run` / `catalog.load()` | `validate_dataset()` |
|---|---|---|---|---|
| `True` (default) | yes | yes | validates; raises on failure (or warns, per `severity`) | validates → result |
| `True` | yes | no | no-op (dict miss) | `skipped`, reason "no validator declared" |
| `True` | no | yes | pre-flight WARNING at build; `ValidationConfigurationError` at first use | `errored`, `error_type="missing_dependency"` |
| `False` | * | yes | specs parsed; validation skipped; zero cost | **still validates** (explicit calls always validate) |
| `"warn"` | no | yes | WARNING + skip (config errors only; data failures still raise where resolvable) | `errored` |
| `"strict"` | * | yes | eager resolution at catalog build; resolution failure fails the session | validates |
| any | * | `enabled: false` | skipped | validates (carries `enabled=False`) |
| env `KEDRO_DATASET_VALIDATION` set | * | * | env wins over settings, both directions, all catalog instances | unaffected |

### `DataCatalog` (framework-facing)

```python
class DataCatalog:
    def __init__(self, ..., validation_enabled: bool = True): ...
    @property
    def validators(self) -> dict[str, dict]: ...
    # public plain-dict shape matching to_config(): {"class": ..., "on": [...],
    # "severity": ..., "enabled": ..., "options": {...}}; pattern-level specs
    # exposed in a separate section. (No private types in the public API.)
    def _maybe_validate(self, ds_name: str, data: Any, mode: str) -> Any: ...  # impl detail,
    # deliberately NOT part of CatalogProtocol
```

`to_config()` re-injects `validator:`. Explicitly-replaced entries drop their spec; in-memory (`MemoryDataset`) validators are runtime-only and surfaced via `catalog.validators` (documented: `to_config()` skips memory datasets today). `DataCatalog.__eq__` ignoring validator specs is documented (or `_validator_specs` joins the comparison — decided in PR review).

### Settings / CLI

```python
# kedro/framework/project — dynaconf Validator, is_in (True, False, "warn", "strict")
DATASET_VALIDATION = True
```

```
kedro catalog validate [--resolve-only] [--pipeline <name>] [dataset ...]   # exit != 0 on failed/errored
```

### Packaging

Per-backend, thin-forwarding extras that mirror Pandera's own and match the `<lib>-<backend>` convention kedro-datasets already uses for Ibis (`kedro-datasets[ibis-duckdb]` → `ibis-framework[duckdb]`):

```toml
[project.optional-dependencies]
pandera-pandas  = ["pandera[pandas]>=0.24"]
pandera-polars  = ["pandera[polars]>=0.24"]
pandera-pyspark = ["pandera[pyspark]>=0.24"]   # experimental, see Design decision 4
```

Rationale (this **replaces** the earlier single `kedro[validation]` = `pandera[pandas]` idea, per review):

- Since **pandera 0.24.0**, base `pandera` ships with **no dataframe backend** — you *must* pick `pandera[pandas]`/`[polars]`/`[pyspark]`/… So bundling a default backend into `kedro[validation]` would silently make a packaging choice for the user, and `kedro[validation]` doesn't say *which* framework it pulls (what would ship Great Expectations later?).
- Each Kedro extra is a 1:1 forwarder to the matching Pandera extra — same relationship `kedro-datasets[ibis-duckdb]` has with `ibis-framework[duckdb]`. Users can equally `pip install "pandera[polars]"` themselves; the funnel is backend-agnostic.
- Chose the `pandera-<backend>` prefix (not `<backend>-pandera`) so validation extras are discoverable under one prefix and read directly onto Pandera's own extra names. `0.24` is the floor where the `pandera.pandas` namespace and the `[pandas]` extra both exist (exact floor confirmed in open questions).
- Note: contrary to an earlier draft, Kedro has **no `pydantic` extra** to mirror — pydantic is a `test`-only dependency, soft-imported by KEP-1 parameter validation. So this scheme is anchored on Pandera's extras and the kedro-datasets precedent, not on a pydantic parallel.

### Worked adapter sketches (proving the protocol)

```python
# Great Expectations — picklable config in __init__, lazy unpicklable machinery
# built inside validate() under a lock (the thread-safety recipe):
class GreatExpectationsValidator:
    def __init__(self, suite_path: str): self._suite_path, self._lock = suite_path, threading.Lock()
    def validate(self, data):
        with self._lock:
            result = _run_checkpoint(self._suite_path, data)   # ephemeral GX context
        if not result.success:
            raise DataValidationError(..., failures=_to_failures(result))
        return data

# Non-tabular — validates a metrics dict; shows column=None failures:
class MetricsValidator:
    def __init__(self, required_keys: list[str]): self._required = required_keys
    def validate(self, data):
        missing = [k for k in self._required if k not in data]
        if missing:
            raise DataValidationError(f"missing metrics: {missing}")
        return data

# Plain callable, via the CallableValidator adapter (fn(data) -> data, or raise):
validator:
  class: spaceflights.schemas.checks.check_positive_revenue
```

---

## Appendix B: Why not hooks? (the complete answer)

This question paused the v1 vote; here is the full analysis, with each claim verified against the codebase.

**1. Dataset I/O hooks do not fire outside pipeline runs.** `before/after_dataset_loaded/saved` are invoked only by `Task` in the runner ([task.py:151-188](kedro/runner/task.py#L151-L188)) — not by `DataCatalog.load/save`. A notebook `catalog.load("companies")`, the VSCode extension, CI checks: none of them fire dataset hooks. (Precision matters here: *lifecycle* hooks like `after_catalog_created` genuinely do fire outside runs, via `session.load_context()` — the claim "hooks also run outside pipeline runs" is true for those and false for the dataset I/O hooks validation would need.)

**2. Hooks cannot implement `validate(data) -> data`.** pluggy discards hook return values on these specs, and `Task` binds the loaded object *before* the hook fires (`inputs[name] = catalog.load(name)` at [task.py:152](kedro/runner/task.py#L152)). A hook can raise, but it can never *replace* the data the node receives — so coercion (`coerce=True`), and therefore the whole Validator protocol, is unimplementable as a hook.

**3. The hybrid steelman re-derives the rejected wrapper.** "Use a built-in `after_catalog_created` hook (which *does* fire outside runs) to wrap or patch datasets, so notebooks are covered too" — that is exactly the v1 `_ValidatingDataset` wrapper with a different trigger, and inherits every wrapper liability that drove this redesign (broken `isinstance`, `_EPHEMERAL`/`_SINGLE_PROCESS` faking, pickling, the repr pollution this KEP was asked to fix), plus a double-wrap hazard on catalogs rebuilt inside hooks.

**4. Declarative binding beats a hook-side registry.** A hook *can* look up schemas dynamically — but then the dataset→schema binding lives in imperative code, the one-schema-per-dataset guarantee must be re-implemented by convention, and nothing can surface bindings statically. Catalog config gives the guarantee by construction and is inspectable by `kedro catalog`, `to_config()`, and Viz.

**5. Determinism.** With validation in the funnel, every `after_dataset_loaded` hook observes validated data, always. Validation-as-a-hook makes that depend on pluggy registration order — invisible to users.

**6. Hooks lose nothing.** They fire in the same places; the `Validator` protocol and `validate_dataset()` are usable *inside* hooks; kedro-pandera's hook-based approach keeps working unmodified.

**The one honest hooks advantage:** `Task` fires hooks regardless of the catalog implementation, while the funnel exists only in `DataCatalog`. A bespoke `DATA_CATALOG_CLASS` that reimplements `load/save` loses declared validation — which is why the context-level warning in Design decision 6 exists, and why the funnel is documented for custom catalog authors.

---

## Appendix C: Rejected designs

**1. KEP-7 v1: type-hint-driven discovery (the previous version of this KEP).** Rejected because: schema conflicts resolve by silent last-wins across pipelines; a bare `Schema` annotation lies to type checkers (the value is a `pd.DataFrame`, confirmed in the discussion thread — and `pd.DataFrame[Schema]`, the canonical Pandera form, then becomes load-bearing config hidden in a signature); schemas referenced from nodes create cross-pipeline import dependencies (@Adeikalam); bindings are undiscoverable without walking every pipeline; and validation applied per-dataset but declared per-node is a category mismatch (@deepyaman). Type hints remain welcome as documentation.

**2. Hooks-based validation (built-in or user-written).** See Appendix B.

**3. `_ValidatingDataset` proxy wrapper (the prototype mechanism, with catalog-config discovery).** Rejected for the identity problems in Design decision 1 — `isinstance`, `_EPHEMERAL`, pickling, repr — all of which the funnel dissolves rather than mitigates.

**4. Reusing the `metadata:` key (kedro-pandera's convention).** Tempting — it parses today with zero core changes. Rejected because `metadata` is contractually *ignored by the framework* (it is popped before dataset construction precisely so plugins can use it freely); making core behaviour depend on it silently changes that contract under every plugin already using the namespace, provides no key validation or reserved-key guarantees, and couldn't gate `to_config()` round-trip semantics. A first-class reserved key is honest about being framework behaviour.

**5. Wrapper dataset configured in YAML** (`type: ValidatedDataset` wrapping the real one). Rejected in v1 and still: deeply nested config, high coupling, breaks every tool that reads `type:` to learn the real dataset class.

**6. Pandera's `@check_types` as the mechanism.** Rejected as *the* mechanism (couples validation to function execution, runs in tests/notebooks whether wanted or not), retained as the complementary tool for function-shaped contracts.

**7. AbstractDataset-level integration** (validation inside the dataset base class). Rejected: pushes a catalog-config concern into every dataset instance including standalone use, requires coordinating the contract across kedro-datasets, and offers no cleaner interception than the funnel.

**8. Eager-everything resolution** (import all validators at catalog build by default). Rejected as default (startup cost, breaks pandera-less environments that never touch validated datasets, hostile to factory laziness) — but available as `DATASET_VALIDATION = "strict"`, with `--resolve-only` as the CI gate.

---

## Decided vs. genuinely open

**Decided in this KEP** (with rationale above): interception point (funnel, §Design 1); schema-on-dataset; key name and reservation (`validator:`); lazy resolution + pre-flight + `strict` mode; no automatic save→load skip (opt-in `skip_load_after_save`); fail-loud on unresolvable validators by default (`"warn"` mode as the documented escape); both directions by default; explicit-API-always-validates; `validate_dataset`/`validate_catalog` names; protocol shape incl. any-raise-is-failure; funnel members out of `CatalogProtocol`; per-chunk generator semantics; per-backend `pandera-<backend>` extras with pandas/Polars as the v1 backends.

**Open for this thread** (kept short — the rest is decided above):

1. **Pandera version floor.** `pandera[...]>=0.24` is proposed (first release with the `pandera.pandas` namespace and per-backend extras); needs a quick check that the `SchemaErrors.failure_cases` shape behind `CheckFailure` is stable from the floor to current (0.31.x).
2. **pyspark promotion.** Ship pyspark as experimental in v1 and revisit once the Narwhals-backed Pandera backend lands on PyPI (0.32.x, currently unreleased), or leave it out of the advertised matrix entirely? (Confirm before launch.)
3. **`ContextAwareValidator`** (optional `validate(data, *, context)` giving validators the dataset name/mode for richer messages): reserve the name in v1, or ship it?
4. **Pandera community engagement** — include **@deepyaman** and reach out to Niels/Neeraj for a joint review; the integration surface is deliberately small (public API only: `DataFrameModel`, `validate(lazy=)`, `SchemaErrors.failure_cases`).

## Reference

- Prototype branch: `prototype/validation-dataset-pandera` (v1 mechanism; the funnel/spec design supersedes it)
- Tech design notes: #5391
- Parent issue: #5390
