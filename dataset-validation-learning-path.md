# From zero to expert: understanding Kedro dataset validation (KEP-10)

A curriculum that takes you from absolute-beginner Python to *fully* understanding the dataset-validation feature — Kedro internals, Pandera, the catalog funnel, the `Validator` protocol, all of it. Every phase ends pointing at real code in this repo, so you're always learning against the thing you're trying to understand.

## How to use this

- **Don't skip the "trace it in the code" exercises.** Reading about `__getattr__` is forgettable; finding it in the old `_ValidatingDataset` and realising *why* it was a problem sticks forever.
- **Build the muscle of reading source, not just docs.** By Phase 5 you'll be opening Kedro's own files. That's the real skill.
- Rough pacing assumes a few focused hours a week. If you already know some Python, blast through Phases 0–1 and slow down at Phase 2 (Protocols) and Phase 5 (Kedro internals) — those are where this feature actually lives.
- The graduation test at the bottom is the bar. When you can answer all of it without notes, you're done.

## What "expert" means here (the end state)

You can:
1. Trace a `catalog.load("companies")` call from YAML to validated DataFrame, naming every function it passes through.
2. Explain *why* validation lives in the catalog load/save path and not in a wrapper or a hook — and defend it against the obvious counter-proposals.
3. Read the `Validator` protocol and explain the `runtime_checkable` footgun without looking it up.
4. Write your own custom validator (tabular and non-tabular) that plugs into the `validator:` key.
5. Walk into the tech-design session and answer adversarial questions about coercion, pickling, factories, and the kill switch.

---

## Phase 0 — Python from absolute zero
**Goal:** read and write basic Python without friction.

**Topics:** values & variables; `int`/`float`/`str`/`bool`/`None`; `if`/`for`/`while`; functions and arguments; `list`, `dict`, `set`, `tuple` (know what each is *for*); f-strings; running a script and using the REPL.

**Resources:**
- [The official Python tutorial](https://docs.python.org/3/tutorial/) — sections 3–6.
- *Automate the Boring Stuff with Python* (free online) or *Python Crash Course* — pick one, do the early chapters.

**Practice:** write a script that reads a CSV with the standard library `csv` module and prints rows where a number column is out of a range. (You're hand-rolling the simplest possible "validator" — keep this file; you'll appreciate how much Pandera does for you later.)

**Checkpoint:** you can explain the difference between a `list`, a `dict`, and a `set`, and when you'd reach for each. *(This matters: the catalog stores datasets in a dict, validator specs in a dict, and "already-validated-on-save" names in a set — exactly these three.)*

---

## Phase 1 — Python for real programs
**Goal:** the object-oriented and module machinery every Kedro file uses.

**Topics:**
- **Classes & objects:** `class`, `__init__`, instances vs. the class itself, methods, attributes, inheritance.
- **Dunder methods:** `__repr__`, `__getattr__`, `__eq__`, `__bool__`, `__getstate__`/`__setstate__`. (These aren't trivia — the *whole* wrapper-vs-funnel argument turns on `__repr__`, `__getattr__`, and pickling.)
- **Exceptions:** `raise`, `try/except`, writing your own `Exception` subclass, exception chaining with `raise X from Y` and the `__cause__` attribute.
- **Modules & imports:** how `import` finds things, packages vs. modules, `from x import y`, and *optional* imports via `try: import pandera except ImportError`.
- **Type hints (intro):** annotating functions, `Optional`, `list[str]`, why they're just hints at runtime.

**Resources:**
- Official tutorial sections 8 (errors), 9 (classes), 6 (modules).
- [Real Python: OOP in Python](https://realpython.com/python3-object-oriented-programming/) and [Real Python: custom exceptions](https://realpython.com/python-exceptions/).

**Practice:** turn your Phase 0 CSV checker into a class `RangeValidator` with a `validate(data)` method that *raises* a custom `DataValidationError` listing every bad row. Congratulations — you've independently invented the shape of this entire feature's core protocol.

**Checkpoint:** you can write a custom exception that carries structured data (a list of failures) and chain it with `raise ... from original`. *(That's literally `DataValidationError` in [kedro/validation/core.py](kedro/validation/core.py).)*

---

## Phase 2 — The advanced Python this feature is built from
**Goal:** the specific intermediate/advanced features the prototype leans on. This is the highest-leverage phase for understanding the *cleverness* of the design.

**Topics (each tied to where it shows up):**
- **`typing.Protocol` + `@runtime_checkable` (structural typing).** The single most important concept here. Read [PEP 544](https://peps.python.org/pep-0544/) and the [typing docs](https://docs.python.org/3/library/typing.html#typing.Protocol). Understand *exactly* why `isinstance(SomeClass, a_runtime_checkable_protocol)` is `True` for any class that merely defines the right method name — that's the "footgun" in `resolve_validator`.
- **`dataclasses`**, including `frozen=True` and `field(default_factory=...)`. → `ValidatorSpec`, `CheckFailure`, `ValidationResult`.
- **Decorators** — what `@property`, `@classmethod`, `@staticmethod`, `@dataclass`, `@runtime_checkable` actually do.
- **Dynamic import** — `importlib`, `importlib.util.find_spec` (locating a module *without running it*), and import-by-string (`load_obj`). → lazy resolution + the pre-flight check.
- **Sentinels** — the `_UNSET = object()` pattern and why you can't just default to `None`. → the validation API's `data` parameter.
- **Pickling & serialization** — `pickle`, what is/isn't picklable, `__getstate__`/`__setstate__`. → why the funnel survives `ParallelRunner` and the wrapper struggled.
- **Concurrency basics** — threads, the GIL, race conditions, `threading.Lock`. → `ThreadRunner`, the `setdefault` resolution race, the GE-adapter lock recipe.

**Resources:**
- *Fluent Python* (Luciano Ramalho), 2nd ed. — chapters on the data model, protocols/ABCs, and decorators. This is the book that makes you fluent in exactly these features. Worth buying.
- [Real Python: Protocols](https://realpython.com/python-protocol/), [Real Python: dataclasses](https://realpython.com/python-data-classes/).

**Practice:** make your `RangeValidator` satisfy a `Validator` `Protocol` you define yourself (`def validate(self, data): ...`). Then write a `resolve(obj)` function that, given either the class, an instance, or a plain function, returns a working validator — and deliberately reproduce the footgun (duck-typing the class object) so you *see* it return the uninstantiated class. Then fix it the way the prototype does.

**Checkpoint:** you can explain, unprompted, why `resolve_validator` checks `inspect.isclass(obj)` *before* `isinstance(obj, Validator)`. *(See [kedro/validation/core.py](kedro/validation/core.py) `resolve_validator`.)*

---

## Phase 3 — The data-validation domain
**Goal:** understand schema validation as a field, and Pandera deeply.

**Topics:**
- **pandas essentials:** `DataFrame`, columns, dtypes, and what *dtype coercion* means (float64 → int64). → the `coerce=True` behaviour that lets validators *transform* data.
- **YAML + the gotchas:** YAML syntax, and specifically the YAML 1.1 "Norway problem" (`on`, `no`, `yes` parsing as booleans). → why `ValidatorSpec.from_config` normalises a `True` key back to `"on"`.
- **Pandera in depth:** `DataFrameModel` vs `DataFrameSchema`; `Field` and checks; `Config` (`strict`, `coerce`); `lazy=True` and the `SchemaErrors.failure_cases` frame; the backend split (`pandera.pandas` / `pandera.polars` / `pandera.pyspark`) and why bare `pandera.DataFrameModel` is deprecated; why pyspark *doesn't raise* and uses `df.pandera.errors`.
- **The neighbours (for context):** skim Great Expectations and Pydantic — enough to see how they'd each satisfy a `validate(data) -> data` protocol. (Pydantic also connects to KEP-1 parameter validation.)

**Resources:**
- [10 minutes to pandas](https://pandas.pydata.org/docs/user_guide/10min.html) and the [dtypes guide](https://pandas.pydata.org/docs/user_guide/basics.html#dtypes).
- [Pandera docs](https://pandera.readthedocs.io/) — DataFrameModel, lazy validation, error reports, and the supported-libraries page.
- A quick read of the [Great Expectations](https://docs.greatexpectations.io/) and [Pydantic](https://docs.pydantic.dev/) intros.

**Practice:** rewrite the `CompaniesSchema` from this repo's [examples/schemas.py](examples/schemas.py) from memory, feed it a deliberately broken DataFrame with `lazy=True`, and inspect `SchemaErrors.failure_cases`. Then group those failures by `(column, check)` by hand — you've just reimplemented `_failures_from_schema_errors` in [kedro/validation/pandera_validator.py](kedro/validation/pandera_validator.py).

**Checkpoint:** you can explain why a million-row failure produces a 3-line error message here, and where the full report goes (`__cause__`).

---

## Phase 4 — Kedro as a user
**Goal:** be a fluent Kedro user before you read its source.

**Topics:** what Kedro is and why (separation of config and code); project anatomy (`conf/`, `src/`, `pyproject.toml`); the **Data Catalog** (`catalog.yml`, dataset types, `load`/`save`); **configuration** (`conf/base` vs `conf/local`, environments, parameters, `OmegaConfigLoader`); **pipelines & nodes**; **runners** (`SequentialRunner`, `ThreadRunner`, `ParallelRunner`); the CLI (`kedro run`, `kedro catalog`).

**Resources:**
- [Kedro docs](https://docs.kedro.org/) — start at "Get started," then do the **spaceflights tutorial** end to end. This is non-negotiable; it's the shared vocabulary of every KEP.
- The "Data Catalog" and "Configuration" sections of the docs.

**Practice:** build the spaceflights project, run it, then open the catalog in a notebook (`kedro jupyter`) and call `catalog.load("companies")` yourself. Add a parameter and read it in a node. You now have a sandbox to test the feature in later.

**Checkpoint:** you can explain what `conf/local` overriding `conf/base` does — and predict what happens to a `validator:` key if `local` redeclares the entry without it. *(That's the "environment-overlay validator loss" risk in the KEP.)*

---

## Phase 5 — Kedro internals (read the source)
**Goal:** understand the machinery the feature plugs into. This is the big one. Open the actual files in this repo.

**Read, in this order, with the question "where could validation hook in?" in mind:**
1. **The catalog:** [kedro/io/data_catalog.py](kedro/io/data_catalog.py) — `from_config`, `__init__`, `_add_from_config` (~L834), `get` (~L557), `load`/`save` (~L981/L1017), `__setitem__`, `to_config`, `__repr__`. This is *the* file the feature modifies.
2. **Datasets:** [kedro/io/core.py](kedro/io/core.py) — `AbstractDataset`, `AbstractVersionedDataset`, `parse_dataset_definition`, and how `metadata`/`versioned` keys are popped (the precedent for popping `validator`).
3. **Factories & lazy datasets:** the `CatalogConfigResolver`, pattern resolution, `_LazyDataset`. Understand *when* a dataset is actually instantiated.
4. **The runner & Task:** [kedro/runner/task.py](kedro/runner/task.py) — find where `catalog.load`/`catalog.save` are called and where `before_dataset_loaded`/`after_dataset_saved` fire (~L151–188). This is the evidence behind "hooks only fire inside a run."
5. **Hooks & pluggy:** the hook specs, and a skim of [pluggy](https://pluggy.readthedocs.io/) — enough to understand that pluggy *discards hook return values*, which is why a hook can't coerce data.
6. **Context/session/settings:** [kedro/framework/context/context.py](kedro/framework/context/context.py), `KedroSession`, and `_ProjectSettings` in [kedro/framework/project/__init__.py](kedro/framework/project/__init__.py) — how a setting like `DATASET_VALIDATION` is declared.
7. **`CatalogProtocol`** — and why adding members to a `runtime_checkable` protocol would be a breaking change.

**Resources:** the code itself, plus the Kedro [architecture/extending docs](https://docs.kedro.org/). Use `git blame` and the GitHub history to see *why* things are the way they are.

**Practice:** with a debugger or print statements, trace a single `catalog.load("companies")` in the spaceflights project through `get` → `_LazyDataset.materialize` → `dataset.load`. Write down every function it touches. (This trace *is* the feature's insertion point.)

**Checkpoint:** you can answer "why does `_add_from_config` see both explicit entries *and* resolved factory patterns?" and "why does materialising a factory pattern *not* trip `__setitem__`'s replacement branch?"

---

## Phase 6 — The validation lineage
**Goal:** understand what came before this feature.

**Topics:**
- **KEP-1 parameter validation** — read [kedro/validation/](kedro/validation/) as it relates to parameters (`TypeExtractor`, `ParameterValidator`, `model_factory`, `utils`). This is the pattern KEP-10 deliberately mirrors and diverges from. Note that parameter validation has *no* opt-out flag — dataset validation is the first.
- **The KEP process & governance** — how a Kedro Enhancement Proposal is written, discussed, voted, and accepted (you're living this right now). Read a couple of past accepted KEPs to see the house style.

**Practice:** diff the parameter-validation flow against the dataset-validation flow. Where do they share machinery? Where did KEP-10 *intentionally* break the symmetry (discovery from config vs. type hints), and why?

**Checkpoint:** you can explain how parameter validation discovers Pydantic models from node type hints, and why KEP-10 chose *not* to discover dataset schemas the same way.

---

## Phase 7 — The feature itself (synthesis)
**Goal:** total command of KEP-10 and the prototype.

**Read, in order:**
1. The KEP documents: [KEP-10-dataset-validation.md](KEP-10-dataset-validation.md) (the posted version) and [KEP-7-dataset-validation-v2.md](KEP-7-dataset-validation-v2.md) (the fuller working version with appendices and the why-not-hooks analysis).
2. The prototype, file by file:
   - [kedro/validation/core.py](kedro/validation/core.py) — `Validator`, `CheckFailure`, `DataValidationError`, `ValidatorSpec`, `resolve_validator`, `CallableValidator`, `preflight_check`.
   - [kedro/validation/pandera_validator.py](kedro/validation/pandera_validator.py) — multi-namespace detection, the per-backend branches, failure grouping.
   - [kedro/validation/api.py](kedro/validation/api.py) — `ValidationResult`, `validate_catalog_dataset`, `validate_catalog`, the `_UNSET` sentinel.
   - The funnel in [kedro/io/data_catalog.py](kedro/io/data_catalog.py) — `_maybe_validate`, `_validation_enabled_effective`, the lifecycle hooks.
   - The framework wiring in [context.py](kedro/framework/context/context.py) and [project/__init__.py](kedro/framework/project/__init__.py).
3. The tests as the executable spec: [tests/validation/](tests/validation/) — one file per concept.
4. The runnable demo: `python examples/demo_catalog_validation.py`.

**Then study the *decisions*, not just the code:** for each of the 7 design decisions in the KEP, be able to state the alternative that was rejected and why (the funnel vs. wrapper vs. hook; schema-on-dataset vs. schema-on-node; lazy vs. eager resolution; etc.).

**Practice:** re-derive the five-level walkthrough we did — pitch → five nouns → trace a run → module-by-module → the subtle "why" of each line.

**Checkpoint:** the graduation test below.

---

## Phase 8 — Capstone (true expert)
**Goal:** prove mastery by building and defending.

Pick at least two:
- **Write a custom validator** that isn't Pandera: a non-tabular one (validate a metrics dict, like `MetricsValidator`) and a `CallableValidator`-style plain function. Wire them via `validator:` in a real catalog and watch them fire.
- **Sketch the Great Expectations adapter** from the KEP appendix as working code, including the lazy-build-under-a-lock pattern. This exercises pickling *and* concurrency *and* the protocol at once.
- **Implement one open question:** e.g. the per-backend extras naming, or a `severity: warn` path, and run the test suite green.
- **Run the tech design:** present the architecture to someone (or rubber-duck it), and have them throw the adversarial questions at you.

---

## Graduation test (answer all without notes)

1. Trace `catalog.load("companies")` from YAML to validated DataFrame, naming each function.
2. Why does validation live in the catalog load/save path rather than a `_ValidatingDataset` wrapper? Give three concrete failures the wrapper had.
3. Why can't this be implemented as a hook? (Two reasons — one about *where hooks fire*, one about *return values*.)
4. Why would `isinstance(MetricsValidator, Validator)` returning `True` be a bug, and where is it prevented?
5. A shared schema is attached to `X_train` and `X_test` and fails mid-run. How does the error message know *which* dataset failed, given the validator object doesn't?
6. Why is `skip_load_after_save` safe under `kedro run --from-nodes B` while `on: [save]` would silently certify stale data?
7. What does a dataset with *no* validator pay, per load, when validation is enabled?
8. Why does `validate_catalog_dataset` still validate even when `DATASET_VALIDATION=False`?
9. What's the YAML 1.1 "Norway problem," where does it bite this feature, and how is it handled?
10. Why is `DATASET_VALIDATION` read from an env var *inside* `kedro/io`, when `kedro.io` is forbidden from importing framework settings?

---

## Appendix: concept → where it lives

| Concept (phase) | Where it shows up in the feature |
|---|---|
| `dict` / `set` (P0) | `catalog._datasets`, `_validator_specs`, `_validators`; `_save_validated` set |
| Custom exceptions + chaining (P1) | `DataValidationError`, full Pandera report on `__cause__` |
| `__getattr__`, `__repr__` (P1) | the old `_ValidatingDataset` wrapper — and why deleting it fixed repr |
| `__getstate__`/pickling (P2) | catalog survives `ParallelRunner`; resolved validators dropped, specs kept |
| `typing.Protocol` + `runtime_checkable` (P2) | the `Validator` protocol and the resolution-order footgun |
| frozen `dataclass` (P2) | `ValidatorSpec`, `CheckFailure`, `ValidationResult` |
| `importlib.util.find_spec` (P2) | the pre-flight check; precedent in `kedro/framework/project` |
| sentinel `object()` (P2) | the `data=_UNSET` parameter in the validation API |
| threads + `setdefault` (P2) | validator resolution under `ThreadRunner`; GE adapter lock |
| dtype coercion (P3) | `coerce=True` validators transform the data nodes/disk receive |
| YAML 1.1 booleans (P3) | the `on:` → `True` normalisation in `ValidatorSpec.from_config` |
| Pandera backends/lazy (P3) | the per-backend adapter branches; pyspark's non-raising behaviour |
| catalog `_add_from_config` (P5) | the single funnel where the `validator:` key is captured |
| factories / lazy datasets (P5) | why specs are captured at materialisation, not build |
| `Task` + hook firing (P5) | the why-not-hooks argument |
| `_ProjectSettings` (P5/P6) | the `DATASET_VALIDATION` setting |
| KEP-1 parameter validation (P6) | the precedent KEP-10 mirrors and diverges from |
