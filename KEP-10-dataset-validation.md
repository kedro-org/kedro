# KEP-10: Dataset validation

> This is a restructured version of KEP-7. The original proposal (type-hint-driven validation) was paused after community feedback. This version pivots to schema-on-dataset with a pluggable validator protocol, as announced in the discussion thread.

> **On how this was written:** the design and the calls in here are mine, but I leaned on Claude (AI) a fair bit — to pressure-test the approach, draft the writeup, and check claims against the Kedro source. I've verified the load-bearing details against the codebase and a working prototype, so I can stand behind them, but I wanted to be upfront that this was AI-assisted. If something reads as wrong, that's on me — please call it out.

**Context:** Explore a Kedro-First Approach to Data Validation (#5390) · Spike: Prototype Dataset Validation Using Pandera (#5391)
**Authors:** @SajidAlamQB
**KEP shepherd:** @SajidAlamQB
**Supersedes:** KEP-7 (type-hint-driven dataset validation)

---

## What changed since v1 (summary for previous readers)

| | KEP-7 | KEP-10 (this document) |
|---|---|---|
| Schema declared | On node function signatures (type hints) | On the catalog entry (`validator:` key) |
| Discovery | `TypeExtractor` walks pipeline node signatures | `DataCatalog` parses catalog config |
| Enforcement | `_ValidatingDataset` proxy wrapper | The catalog `load()`/`save()` path — no wrapper |
| Backend | Pandera only | Pluggable `Validator` protocol; Pandera is the reference implementation |
| Validates on | Load only | Load and save |
| Schema conflicts | Last-wins silently (known bug) | Can't happen: one entry, one validator |
| Outside pipeline runs | Not addressed | Public `validate_catalog_dataset()` API + `kedro catalog validate` CLI |
| Opt-out | Deferred | `DATASET_VALIDATION` setting + `KEDRO_DATASET_VALIDATION` env var |
| Node type hints | The validation driver | Optional documentation (`pd.DataFrame[Schema]` still valid, no longer load-bearing) |

The pivot is a direct response to the review on KEP-7: @deepyaman on schema-on-dataset, save-side validation, catalog inspectability, and why-not-hooks; @noklam on a global disable plus a programmatic API for IDE diagnostics; and @Adeikalam on how schemas-next-to-nodes create cross-pipeline coupling.

---

## What are we trying to do?

Add native dataset validation to Kedro, declared in the catalog:

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
# nodes.py — plain Python, nothing validation-specific here
import pandas as pd


def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    companies["iata_approved"] = companies["iata_approved"].map({"t": True, "f": False})
    return companies
```

Whenever something calls `catalog.load("companies")` — a pipeline run, a notebook, the IDE extension, CI — the loaded DataFrame is checked against `CompaniesSchema` before it comes back. On save, the data is checked before it's written, so invalid data never reaches disk. A failure raises `DataValidationError` and reports every failed check at once (Pandera's `lazy=True`), naming the dataset, the validator, and whether it failed on load or save.

The catalog entry is the single source of truth: one dataset, one validator. The KEP-7 bug where two pipelines annotate the same dataset and the last one silently wins simply can't occur here, because the binding is a key in a YAML mapping rather than something we discover by walking every pipeline.

### Who is this for?

- A team ingesting third-party data can put a contract on the raw dataset, so a bad supplier file fails at the I/O boundary with a full report, before any node runs.
- The Kedro VSCode extension (@noklam) can call `validate_catalog_dataset(catalog, name)` and render the structured failures as editor diagnostics — no run, nothing raised.
- A CI job can run `kedro catalog validate --resolve-only` to catch typo'd validator paths and missing dependencies on every PR, and optionally run full data validation on a schedule.
- Kedro-Viz can surface declared schemas statically through `catalog.to_config()` and `catalog.validators`, without executing anything.
- Plugin authors (Great Expectations, Pydantic, custom in-house checks) implement one small protocol and plug into the same `validator:` key.

## What this is not

- **Not a breaking change.** No key means no validation and no behaviour change. `validator:` is a new reserved key; everything else is untouched.
- **Not a replacement for hooks.** Hooks still work and still fire in the same places.
- **Not a mandatory Pandera dependency.** Pandera comes in through an optional extra: `pip install "kedro[validation]"`.
- **Not function-level contracts.** This validates data at rest — what's loaded or saved under a catalog name. If you want a function-boundary contract ("everything entering this node must be numeric"), Pandera's `@check_types` on the function is still the right tool and works alongside this. Using both on the same dataset just validates twice, which we document.

## How is it done today, and where does it fall short?

There are roughly four ways people validate data in Kedro projects now:

1. **Hand-written hooks** (`after_dataset_loaded` / `before_dataset_saved`) pointing at schemas in another module. The control flow is hidden, it's hard to discover, every new dataset means editing the hook, and — this is the important one — dataset I/O hooks only fire inside a pipeline run, so a notebook or an ad-hoc `catalog.load()` isn't covered at all.
2. **The `kedro-pandera` plugin**, which declares Pandera schemas under the catalog `metadata:` key and validates via hooks. It's essentially unmaintained now, but it proved there's real demand for declarative, catalog-adjacent schemas, and it's the direct inspiration for this proposal. We should pull on its design experience and credit it properly in the launch writeup. This KEP brings the idea into core with a first-class key, an enforcement point that also covers non-run access, and a backend-agnostic protocol.
3. **Pandera's `@check_types` decorator** on node functions. It ties validation to the function, so it runs in every test and notebook call, and says nothing about data loaded outside that function.
4. **The unreleased KEP-7 v1 prototype** (type-hint-driven).

We'll still rewrite Kedro's own `docs/integrations-and-plugins/pandera.md` to lead with `validator:` and move the hand-rolled hook recipe down into an "advanced / conditional validation" section, with a note not to double-validate the same dataset. I don't think we owe a formal migration path: kedro-pandera is effectively unmaintained and the v1 prototype never shipped.

## What's new here, and why I think it'll work

### Architecture overview

```
conf/base/catalog.yml ("validator:" key)
        │
        ▼
DataCatalog._add_from_config()          ← parses the key into a _ValidatorSpec, stores it
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

Save mirrors this: `catalog.save(name, data)` validates before `dataset.save()`, so invalid data is never persisted.

### Design decision 1: validation lives in the catalog's load/save path, not a wrapper

Heads up — this is a change from what I said in the pivot announcement, where I expected to keep the `_ValidatingDataset` wrapper. Once I started actually building it, the wrapper caused more trouble than it was worth, and dropping it cleared up several review comments at once.

The problems with the wrapper were structural, not cosmetic. A proxy around the dataset breaks `isinstance(ds, AbstractVersionedDataset)` in the catalog's own version handling, has to fake `_EPHEMERAL` (which runners check) and `_SINGLE_PROCESS`, has to delegate `exists()`/`release()`, and has to survive `ForkingPickler` for `ParallelRunner`. Putting the check in `catalog.load`/`save` instead means none of that applies — the dataset stays exactly what the YAML says it is.

A few things fall out of that:

- @deepyaman's repr concern goes away because there's nothing to repr — the catalog shows the real datasets. You can still inspect the bindings: there's a read-only `catalog.validators` property, they show up in `kedro catalog` output, and they round-trip through `catalog.to_config()` (which re-injects the `validator:` key, which is what lets Kedro-Viz show schemas statically).
- `Task` calls `catalog.load`/`catalog.save` ([task.py:152, 186](kedro/runner/task.py)), and so do notebooks, `kedro ipython`, plugins, and CI scripts. One enforcement point covers all of them. (What it *doesn't* cover is in the Risks section — I'd rather be upfront about that.)
- Hook ordering becomes predictable: `before_dataset_loaded` → `catalog.load` (validates) → `after_dataset_loaded` always sees validated data. If validation were itself a hook, that ordering would depend on pluggy registration order.

The cost is honest to state: about 25 lines in `kedro/io`, which is one of the most stable modules we have, and on a hot path. The mitigations are that the disabled/no-spec path is a dictionary miss, `kedro.validation` is imported lazily inside `_maybe_validate`, and I'll ship a micro-benchmark of the no-op path with the PR (see Performance).

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
        exc.dataset_name, exc.mode = ds_name, mode          # add context here
        exc.args = (f"Validation failed for dataset '{ds_name}' on {mode}: {exc}",)
        if spec.severity == "warn":
            logger.warning(...); return data
        raise
    except Exception as exc:                                 # any raise == failure
        wrapped = DataValidationError(str(exc), dataset_name=ds_name, mode=mode, ...)
        if spec.severity == "warn":
            logger.warning(...); return data
        raise wrapped from exc
```

Two contracts the path defines, both pinned by tests:

- Any exception out of `validate()` counts as a validation failure. A custom validator can raise `ValueError`, `pydantic.ValidationError`, whatever — the catalog normalises it to `DataValidationError` with the dataset name and mode attached. The separate `errored` status (see the API) is only for failures *before* `validate()` runs at all: an import error, or the dataset failing to load.
- Validators are allowed to transform data. Pandera with `coerce=True` hands back a coerced frame, and that coerced frame is what the node gets on load and what gets written on save. This is a real behaviour and we document it prominently — see Risks for the hook-observability wrinkle it creates.

### Design decision 2: the `validator:` key

`validator:` becomes a reserved top-level dataset-config key, sitting alongside `type:` / `versioned:` / `credentials:` / `metadata:`. Two forms:

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

**Parsing.** `DataCatalog._add_from_config()` is the one place both explicit entries and lazily-resolved factory patterns pass through. We capture the key into `catalog._validator_specs[name]` and hand a cleaned copy of the config (without `validator:`) on to dataset instantiation. The resolver's own config store isn't mutated, so `kedro catalog resolve` and Kedro-Viz still see consistent, validator-bearing configs. `parse_dataset_definition()` also strips the key defensively (the same way it already pops `metadata`, [core.py:250](kedro/io/core.py#L250)) so a direct `AbstractDataset.from_config()` call doesn't blow up with a `TypeError`. A `validator:` nested inside a `CachedDataset` `dataset:` block is a configuration error with a fix-it message ("declare it on the top-level entry") rather than a silent strip — if you asked for validation, you shouldn't quietly lose it. I'll also audit kedro-datasets for any dataset whose `__init__` takes a `validator` kwarg and document the key as reserved next to `versioned`/`credentials`.

**Spec validation.** `_ValidatorSpec.from_config` only accepts a `str` or a `dict`. It rejects unknown long-form keys (allowed: `class`, `on`, `severity`, `enabled`, `skip_load_after_save`, `options`), checks `on ⊆ {load, save}` and non-empty, and rejects a YAML list with a "reserved for future use" message — so we can add a per-direction list form later (`validator: [{class: A, on: [load]}, {class: B, on: [save]}]`) without breaking anyone. There's one YAML 1.1 wrinkle worth calling out: an unquoted `on` key parses as boolean `True` (the "Norway problem", and it survives the OmegaConf round-trip — I checked). `from_config` normalises the `True` key back to `"on"` so the examples above work unquoted, as written.

**Lifecycle.** The spec follows the catalog entry, not the name forever. If you replace a dataset explicitly (`catalog["companies"] = df` in a notebook) the spec is cleared, so no stale validator fires against the replacement. Factory materialisation does *not* clear it. Both are pinned by tests.

### Design decision 3: schemas live in `src/<package>/schemas/`, referenced by import path

Schemas are code, kept in one conventional place — the same idea as `conf/<env>/parameters.yml` for parameters:

```
src/spaceflights/
├── pipelines/
└── schemas/
    ├── __init__.py
    └── companies.py        # CompaniesSchema
```

The catalog points at them with a full dotted import path, resolved with the existing `kedro.utils.load_obj`. It's a convention rather than anything magic: no implicit module prefixes, so the paths are grep-able (@Adeikalam's discoverability point) and unambiguous. The one rule is that a validator path has to be a top-level attribute of an importable module, which is exactly what the `schemas/` convention gives you; nested classes and notebook-defined `__main__` schemas are rejected with a hint. The spaceflights starters get the folder scaffolded with one example schema and a commented-out `validator:` line; other starters are left alone.

**Resolution is lazy, with a cheap pre-flight.** At catalog build time we only parse the spec — strings, no imports, no pandera, no startup cost, and factory entries work naturally. The actual import happens on first load/save or first API call. To stop a typo from surfacing three hours into a run, catalog build runs a near-zero-cost pre-flight: `importlib.util.find_spec()` on each spec's top-level package, no module execution. A miss is a warning by default and a hard error under `DATASET_VALIDATION = "strict"`. The complete fail-fast gate is `kedro catalog validate --resolve-only` in CI.

### Design decision 4: a small pluggable `Validator` protocol

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

The resolution order matters, and it's deliberate:

1. Adapters get first refusal on the imported object (v1: the Pandera adapter; later a `kedro.validators` entry-point group).
2. If it's a class, we instantiate it with `options` and protocol-check the *instance*. We never duck-type the class object directly, because `isinstance(SomeClass, runtime_checkable_protocol)` is true for any class that merely *defines* a `validate` method — which would quietly return the uninstantiated class and drop `options`. (This one bit me in the prototype, so there's a test for it.)
3. If it's already an instance (e.g. a module-level `pa.DataFrameSchema.from_yaml(...)` result), we protocol-check it; passing `options` to an instance is a config error, since they can't be applied.
4. Anything else is a `ValidationConfigurationError` that names the dataset, the path, and what it actually found.

The **Pandera reference adapter** handles real-world Pandera, not just the legacy import style:

- It detects `pandera.pandas`, `pandera.polars`, and `pandera.pyspark` `DataFrameModel`/`DataFrameSchema`. The top-level `pandera.DataFrameModel` is deprecated as of pandera 0.30 and on its way out, so detecting only that (like the prototype did at first) would miss every modern schema.
- pyspark is the odd one out: `pandera.pyspark` doesn't raise on failure, it accumulates errors on `df.pandera.errors`. The adapter branches per backend and raises `DataValidationError` off the accessor when it's non-empty, otherwise invalid Spark data would sail through as a false pass.
- For a polars `LazyFrame`, Pandera validates at schema-only depth by default, so data-level checks are silently skipped. The adapter logs a one-time warning per dataset saying what depth actually ran, and offers `options: {collect: true}` to validate `data.collect()` and return the original LazyFrame. The docs recommend validating eagerly on save of the producing dataset instead.
- `head`/`tail`/`sample`/`random_state` are forwarded to `schema.validate()` as the cost knob for large frames. An unknown option is a configuration error naming the option and the adapter version, not a silently-ignored no-op.
- `SchemaErrors.failure_cases` is mapped into structured, grouped failures (the `CheckFailure` type) with capped row examples, so error messages stay bounded even on million-row frames. The full Pandera report stays available on `err.__cause__`.

A worked Great Expectations adapter and a non-tabular metrics validator are in Appendix A — I checked the protocol against both, plus a per-row Pydantic validator, to make sure `validate(data) -> data` is actually enough.

### Design decision 5: save-side behaviour

- Save validation runs before `dataset.save()`, so invalid data is never written.
- Validating on save does *not* automatically skip validation on the next load. Persistence round-trips aren't identity-preserving (CSV drops dtypes, for one), so an automatic skip would be certifying data the schema never actually saw.
- The scoped answer to @deepyaman's "if you wrote it, you shouldn't have to re-validate it" point is the opt-in `skip_load_after_save: true` flag. It's a per-catalog-instance set (never pickled, cleared on `release()`) that records save-validated datasets, and load validation is skipped only when *this* process wrote the data. Unlike `on: [save]`, this stays safe under partial runs — `kedro run --from-nodes B` loads data this run never wrote, so it validates normally. I'd recommend it for round-trip-faithful formats like Parquet; a later extension could key on `save_version` for cross-process caching.
- Generator (chunked) nodes: the runner saves once per chunk, so save validation runs per chunk. Cross-chunk invariants (`unique`, frame-level checks) aren't enforced across the whole output — I'd rather say that plainly than imply a guarantee we don't have. For chunk-appended outputs, use `on: [load]` so the whole persisted dataset is validated on the next read. The per-chunk behaviour is pinned by a test so it's intentional rather than accidental.

### Design decision 6: opt-out and the kill switch

```python
# settings.py
DATASET_VALIDATION = True   # True (default) | False | "warn" | "strict"
```

- `True` — validation on, lazy resolution, pre-flight warns on missing packages.
- `False` — validation off everywhere; the path short-circuits before any import, so disabled really is zero cost. Explicit API calls still validate (below).
- `"warn"` — like `True`, but a *configuration* error (an unresolvable validator, e.g. a deliberately slimmed serving image) downgrades to a warning and skips. Data failures still raise. Per-dataset failure tolerance is the `severity: warn` key, not this.
- `"strict"` — like `True`, plus every declared validator (including pattern-level ones) is resolved eagerly at catalog build, and any resolution failure fails the session immediately.

The setting is validated at load (`is_in (True, False, "warn", "strict")`), so a typo is a settings error rather than something that silently evaluates as truthy-and-on. I went with `DATASET_VALIDATION` rather than the `VALIDATION_ENABLED` name I floated earlier, to keep it clearly separate from KEP-1 parameter validation.

The env var `KEDRO_DATASET_VALIDATION=0|false|1|true|warn|strict` is read directly in `_maybe_validate` (same idea as `KEDRO_MP_CONTEXT` being read inside `kedro/runner`) and wins over the setting in both directions. Reading it in `kedro.io`, which never imports framework settings, means the emergency kill switch covers every catalog instance — including catalogs a plugin rebuilds from config inside a hook (the kedro-telemetry pattern) and a bare `DataCatalog.from_config()` in a notebook.

For standalone catalogs, `DataCatalog` itself defaults `validation_enabled=True`, so declared config is honoured everywhere unless something turns it off; `KedroContext` overrides it from settings/env. A catalog rebuilt inside a hook therefore validates on its own and idempotently — validation is per-`load()`, there's no wrapping, so there's nothing to double-apply. There's a kedro-telemetry-shaped regression test for that.

Custom `DATA_CATALOG_CLASS` is the one rough edge. The path members are deliberately *not* added to `CatalogProtocol`, because adding members to a `runtime_checkable` protocol would instantly fail settings-load for every existing custom catalog, which would be a breaking change. Instead, at context catalog-creation, if validation is on and specs exist but the catalog class doesn't have the path (a `hasattr` check), Kedro logs a clear warning that declared validators will be ignored — so it's at least diagnosable rather than silent. `SharedMemoryDataCatalog` inherits the path, and there's a regression test that validators fire inside `ParallelRunner` workers.

### Design decision 7: the programmatic API (IDEs, notebooks, CI)

```python
from kedro.validation import validate_catalog_dataset, validate_catalog

result = validate_catalog_dataset(catalog, "companies")   # never raises for outcomes
if not result:
    for f in result.failures:
        print(f.column, f.check, f.failure_count, f.failure_examples)
```

Full signatures and dataclasses are in Appendix A. The behaviour that matters:

- Explicit calls always validate. They ignore the global flag *and* per-dataset `enabled: false` (one rule, no special cases), and the result carries the enabled-state so an IDE can grey it out rather than flag it red.
- The result is a `ValidationResult` with `status ∈ {passed, failed, skipped, errored}` plus a machine-readable `error_type` (`missing_dependency` / `unresolvable_validator` / `dataset_error`), so the VSCode extension can collapse "pandera not installed" into one workspace notice instead of painting every dataset red.
- `data` is optional and isn't something a user writes by hand: omit it and the dataset is loaded via `catalog.get(name).load()` (the raw path, which bypasses the catalog check, so the API never double-validates). Internally a sentinel distinguishes "not passed" from an explicit `None`, because `None` is itself validatable data (the JSON metrics example) — users never see or type the sentinel. `version=` passes through to versioned datasets. `on="save"` needs explicit `data`, since validating loaded data against save rules wouldn't mean anything.
- `raise_if_failed()` flips it back to raising semantics in one call, and the validated/coerced data is on the result.
- `validate_catalog(catalog)` validates in bulk, and it includes factory-pattern entries by resolving the patterns against the project pipelines (the same machinery `kedro catalog resolve` uses). Without that, the CI gate would silently skip exactly the lazily-resolved entries that most need checking.

### The CLI: `kedro catalog validate`

```
kedro catalog validate [--resolve-only] [--pipeline <name>] [dataset ...]
```

- `--resolve-only` imports and resolves every declared validator (explicit and pattern-level) without loading data — the cheap CI gate for typos and missing dependencies that lazy resolution otherwise gives up. Non-zero exit on any `errored`.
- Full mode loads and validates, bounded by `--pipeline` or explicit names. Validating all data across a big catalog is unbounded cost, so the docs recommend resolve-only as the default CI gate.
- It reports, per dataset, which validator resolved and from where (explicit entry vs pattern, which config source) — which is how you see environment-overlay validator loss (see Risks).
- It reports `skipped: no validator` for pipeline datasets that don't have one, which also surfaces the namespace gap: a validator on `companies` doesn't match a namespaced `ns.companies`, and the recipe for that is a `"{namespace}.companies"` pattern entry.

### What a failure actually looks like

```
$ kedro run
...
DataValidationError: Validation failed for dataset 'companies' on load
(validator: spaceflights.schemas.companies.CompaniesSchema, declared in conf/base/catalog.yml)
3 checks failed across 2 columns — 4,210 failure cases:
  - company_rating: greater_than_or_equal_to(0) — 4,208 cases (e.g. -0.5 @ row 17, -1.2 @ row 102, ...)
  - company_rating: less_than_or_equal_to(1)    — 1 case   (e.g. 4.2 @ row 33)
  - id: field_uniqueness                        — 1 case   (e.g. 10542 @ rows 88, 91)
(full Pandera report available on __cause__)
```

## Key features and benefits

- One schema per dataset, by construction — the silent-conflict bug class is gone rather than mitigated.
- Validation everywhere data flows through the catalog: pipeline runs, notebooks, `kedro ipython`, plugins, the programmatic API — not just runner-mediated loads.
- No wrapper, so datasets keep their identity, repr, pickling, and `isinstance` behaviour. Catalog inspection stays honest.
- Load and save in v1, with invalid data never written.
- Pluggable: Pandera is about 200 lines of adapter against a public protocol, and GX / Pydantic / custom / non-tabular validators are implementable today, with installable adapters via a `kedro.validators` entry-point group in v1.x.
- Opt-in by default and cheap to opt out: no key means no cost, and `DATASET_VALIDATION=False` or the env var is a zero-cost short-circuit.
- A foundation for more: the `to_config()` round-trip plus `catalog.validators` already unlock Kedro-Viz schema display and schema-driven catalog docs without further core changes.

### One schema across many datasets (@deepyaman's training-node example)

Within a single catalog file, declare it once and reference it per dataset with a YAML anchor (the leading-underscore key is dropped by `OmegaConfigLoader` after merge — verified at `omegaconf_config.py:384`):

```yaml
_all_numeric: &all_numeric
  class: spaceflights.schemas.shared.AllNumericFeatures

X_train: {type: pandas.ParquetDataset, filepath: ..., validator: *all_numeric}
X_test:  {type: pandas.ParquetDataset, filepath: ..., validator: *all_numeric}
```

To be honest about the limit: anchors are per-file. Kedro's multi-file catalog convention means cross-file sharing is either "repeat the one-line dotted path" (which is grep-able, so not the worst thing) or a dataset factory pattern where the naming allows it, e.g. `"{name}_model_input":`. The cost versus v1's single node annotation is N one-line references instead of one — and that's the trade I'm deliberately making, because the per-dataset declaration is exactly what kills the silent conflicts and the cross-pipeline coupling. For genuinely function-shaped contracts, `@check_types` on the node is still the better fit.

### YAML-defined Pandera schemas already work

Because the adapter accepts `DataFrameSchema` instances, a module-level schema loaded from YAML:

```python
# src/spaceflights/schemas/companies_yaml.py
import pandera.pandas as pa
schema = pa.DataFrameSchema.from_yaml(Path(__file__).parent / "companies.yml")
```

referenced as `validator: spaceflights.schemas.companies_yaml.schema`, works with no new code. The caveats are documented: Pandera YAML is pandas-only and only serialises registered checks. A `PanderaYamlValidator(schema_file=...)` convenience with package-relative path resolution is v1.x sugar, not something v1 depends on.

## Risks

A consolidated list, each with how I'd handle it:

1. **Core surface area on a hot path.** ~25 lines in `DataCatalog.load/save`. Mitigated by the dict-miss fast path, lazy imports, and a published no-op-path micro-benchmark (see Performance). Any bug in this path touches every load/save, which is why the test matrix below is large.
2. **Raw-access bypass, by design.** `catalog.get(name).load()`, `catalog[name].load()`, and direct dataset access all skip validation — that's the raw path the API itself needs. Worth flagging specifically: Kedro-Viz previews call `dataset.preview()` directly and are *not* validated; Viz's benefit here is static schema surfacing, not validated previews. We document this clearly.
3. **Coercion changes the data.** With `coerce=True`, the node and the disk get the coerced frame, which is a behaviour change if you add a validator to an existing pipeline. Needs a prominent docs and release-notes callout.
4. **Hooks see different data on save.** `after_dataset_saved` gets the runner-local pre-coercion object ([task.py:183-188](kedro/runner/task.py#L183-L188)), so what was actually persisted may differ. The contract we document: dataset I/O hooks see pre-validation data on save and post-validation data on load; a lineage/profiling plugin that needs the persisted truth has to read it back. Pinned by a test.
5. **`save_args` blind spot.** The schema validates what the node produced, not whatever dataset-side save processing actually wrote. A documented limitation.
6. **Environment-overlay validator loss.** A `conf/local` override of an entry that omits `validator:` drops the base validator under destructive merge — the same family as last-wins, but at config level. Mitigations: `kedro catalog validate` reports which validator resolved and from where; a resolve-time warning when an explicit entry shadows a pattern that carries a validator; and a docs recommendation to declare validators in `base` and override with `enabled: false` rather than redeclaring the whole entry.
7. **Custom catalog degradation.** Covered above — the `hasattr` warning at context creation, and keeping the path members out of `CatalogProtocol`.
8. **Config errors despite the pre-flight.** `find_spec` catches missing packages, not a bad attribute name. `kedro catalog validate --resolve-only` in CI and `"strict"` mode close that gap for teams that want build-time failure.
9. **Lazy/distributed backends.** Load-side validation triggers Spark actions / forces evaluation inside `catalog.load()`, which changes job shape and can be expensive on a cluster. The docs will ship a per-backend eager/lazy table; the guidance is to prefer `on: [save]` or sampled options for Spark/Dask and schema-only depth for polars-lazy. Streaming datasets aren't supported with load validation.
10. **ParallelRunner imports.** Workers re-resolve validators from string specs (`__getstate__` drops the resolved cache), so schema modules have to be importable in workers — which is already true for node functions.
11. **Import-path execution.** `validator:` imports and runs module code on first use, the same trust surface as `type:`. No new surface, just stating it.
12. **Thread concurrency.** Under `ThreadRunner`, first-use resolution can race (harmless: `setdefault` keeps one instance), and `validate()` can be called concurrently — the protocol docstring asks for thread-safety, and the GE adapter shows the lock-guarded lazy-state pattern.

## Performance

Three micro-benchmarks ship with the implementation PR (numbers in the PR description, methodology in `benchmarks/`):

1. Per-call `_maybe_validate` overhead on the disabled/dict-miss path over N `MemoryDataset` loads — to defend adding code to the hot path.
2. Catalog-build spec parsing plus pre-flight on a ~500-entry catalog.
3. Representative Pandera timings (1M-row frame; lazy vs eager; with and without coerce; `sample` option) — so the cost guidance in the docs is evidence, not vibes.

The v1 cost knobs are: narrowing `on:`, `severity: warn` during adoption, `options: {head/sample: …}`, `skip_load_after_save`, per-dataset `enabled: false`, and the global flag.

## Migration

- **From the unreleased v1 prototype:** type-hint discovery and `_ValidatingDataset` go away; `DataValidationError` moves to `kedro.validation` with an import shim kept for one release. v1 never shipped, so there's no real deprecation cycle owed — but for one release, if pandera is importable and a node input is annotated with a `DataFrameModel` whose dataset has no `validator:`, Kedro logs a warning linking to migration docs (reusing the discovery code that's otherwise being deleted), so nobody's validation silently evaporates. The deletion order keeps `_is_pandera_model` available to KEP-1 code that imports it.
- **From hooks / kedro-pandera:** a migration table in the docs, and an INFO log when an entry has both `validator:` and `metadata: pandera:`, which probably means double validation.
- **KEP-1 parameter validation:** untouched.

---

## Appendix A: Proposed API changes

### User-facing (YAML)

See Design decision 2 — `validator:` shorthand and long form. The reserved key is documented next to `versioned`/`credentials`.

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


_UNSET = object()   # internal sentinel; users never write this (omit `data` instead)

def validate_catalog_dataset(
    catalog: CatalogProtocol,
    name: str,
    data: Any = _UNSET,                  # omit => load raw via catalog.get(name).load()
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

| `DATASET_VALIDATION` | pandera installed | `validator:` declared | `kedro run` / `catalog.load()` | `validate_catalog_dataset()` |
|---|---|---|---|---|
| `True` (default) | yes | yes | validates; raises on failure (or warns, per `severity`) | validates → result |
| `True` | yes | no | no-op (dict miss) | `skipped`, reason "no validator declared" |
| `True` | no | yes | pre-flight WARNING at build; `ValidationConfigurationError` at first use | `errored`, `error_type="missing_dependency"` |
| `False` | * | yes | specs parsed; validation skipped; zero cost | still validates (explicit calls always validate) |
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

`to_config()` re-injects `validator:`. Explicitly-replaced entries drop their spec; in-memory (`MemoryDataset`) validators are runtime-only and surfaced via `catalog.validators` (`to_config()` skips memory datasets today). Whether `DataCatalog.__eq__` should consider validator specs is a small open call for PR review (currently it doesn't, which we'd document).

### Settings / CLI

```python
# kedro/framework/project — dynaconf Validator, is_in (True, False, "warn", "strict")
DATASET_VALIDATION = True
```

```
kedro catalog validate [--resolve-only] [--pipeline <name>] [dataset ...]   # exit != 0 on failed/errored
```

### Packaging

```toml
[project.optional-dependencies]
validation = ["pandera[pandas]>=0.24"]
```

Note: modern pandera ships a core package with no dataframe backend, so a plain `pandera>=…` pin would make the tutorial's first CSV validation fail with an import error. `pandera[pandas]` is the headline extra; non-pandas backends are user-installed (`pip install "pandera[polars]"` etc., since the validation path is backend-agnostic). The exact version floor is an open question below.

> Review note (post-feedback): @deepyaman pushed back on bundling `pandera[pandas]` under a generic `kedro[validation]` and on advertising pyspark. The follow-up direction is per-backend, thin-forwarding extras (`kedro[pandera-pandas]`, `kedro[pandera-polars]`, …) that mirror Pandera's own extras and the `lib-backend` convention kedro-datasets already uses for Ibis, plus treating pyspark as experimental until the Narwhals-backed Pandera backend lands. I'm tracking that separately rather than rewriting this section mid-thread.

### Worked adapter sketches (showing the protocol holds up)

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

## Open questions

1. **Pandera version floor.** I'm proposing `>=0.24` (the first release with the `pandera.pandas` namespace and per-backend extras). Worth a quick check that the `SchemaErrors.failure_cases` shape the `CheckFailure` mapping relies on is stable from there to current (0.31.x).
2. **`kedro catalog validate` full-data default.** Should it require an explicit `--all-data` (resolve-only by default) so nobody accidentally runs unbounded validation in CI?
3. **`severity: warn` and CLI exit code.** Should warn-level failures affect the exit code (report-only, vs a `--strict-warnings`)?
4. **`ContextAwareValidator`.** An optional `validate(data, *, context)` form that hands validators the dataset name/mode for richer messages — reserve the name in v1, or actually ship it?
5. **pyspark.** Ship it as experimental and revisit once the Narwhals-backed Pandera backend lands on PyPI, or leave it out of the advertised matrix for now? I'd want to confirm before launch either way.
6. **Entry-point group.** Is `kedro.validators` for third-party adapters a v1 thing or v1.x?
7. **Pandera community.** I'd like @deepyaman in the review, and to reach out to Niels/Neeraj for a joint look — the integration surface is small on purpose (public API only: `DataFrameModel`, `validate(lazy=)`, `SchemaErrors.failure_cases`).

## Reference

- Prototype branch: `prototype/kep7-v2-catalog-validation` (this design — the funnel/spec mechanism)
- Tech design notes: #5391
- Parent issue: #5390
