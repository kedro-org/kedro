# Dataset Validation — issue tracking plan (paste-ready)

How to set this up on `kedro-org/kedro`:

1. Create the **parent** issue below → set its issue **type = Parent**.
2. Create each **sub-issue** → set type **Task** (or **Spike** for the tech design one).
3. On the parent, use the **Sub-issues** panel to link all of them (GitHub tracks completion automatically).
4. Add parent + children to the **Kedro 🔶** project board, the **Validation of data & parameters** milestone, and the **H2 2026** roadmap — same as #5390.
5. Link back to the accepted KEP (#5562) and the parent initiative (#5390) from the parent.

A working prototype already exists on branch `prototype/kep7-v2-catalog-validation` (green tests, runnable demo in `examples/demo_catalog_validation.py`). Most core sub-issues are "productionise + review + test-coverage," not greenfield — noted per issue.

---

## PARENT — [Implementation] Dataset Validation (KEP accepted)

**Type:** Parent · **Milestone:** Validation of data & parameters · **Roadmap:** H2 2026

### Goal
Implement native, catalog-declared dataset validation in Kedro, per the accepted KEP (#5562). A dataset entry may declare a `validator:` pointing at a schema/validator; the catalog enforces it on `load` and `save` through a pluggable `Validator` protocol, with Pandera as the reference backend.

### Design (accepted)
- Schema-on-dataset via a first-class `validator:` catalog key — one dataset, one validator.
- Enforcement in the `DataCatalog` load/save path (no wrapper dataset).
- Pluggable `Validator` protocol (`validate(data) -> data`); Pandera is the reference implementation.
- Validate on load **and** save; opt-out via `DATASET_VALIDATION` setting + `KEDRO_DATASET_VALIDATION` env var.
- Public `validate_dataset()` / `validate_catalog()` API + `kedro catalog validate` CLI for IDEs/CI.

Full design: KEP discussion #5562. Prototype: branch `prototype/kep7-v2-catalog-validation`.

### Sub-issues
- [ ] Tech design session & lock open decisions
- [ ] Core: `kedro.validation` package + Pandera adapter
- [ ] Core: `DataCatalog` validator funnel + framework wiring
- [ ] Public API + `kedro catalog validate` CLI
- [ ] Documentation
- [ ] kedro-starters: `schemas/` scaffold (sibling repo)
- [ ] Community / Pandera outreach

### Out of scope for v1
Automatic YAML-schema loader, GX/Pydantic reference adapters (protocol only), pyspark promotion to supported, `ContextAwareValidator` (unless decided at tech design).

---

## SUB-ISSUE 1 — Tech design session & lock open decisions

**Type:** Spike · **Blocks:** all core sub-issues

Run the (updated) tech design for the accepted KEP and lock the decisions the implementation depends on. The architecture pivoted since the April session (type-hints → `validator:` key, wrapper → catalog funnel, Pandera-only → pluggable protocol), so walk the team through the current design + demo.

**Agenda / decisions to lock:**
- [ ] Extras naming — single `kedro[validation]` vs per-backend `kedro[pandera-pandas]` / `kedro[pandera-polars]` (recommend per-backend, mirrors kedro-datasets’ Ibis extras).
- [ ] Public API name — `validate_dataset` vs `validate_catalog_dataset`.
- [ ] pyspark — ship experimental or leave out of the advertised matrix.
- [ ] Pandera version floor (`>=0.24`) and `SchemaErrors.failure_cases` stability.
- [ ] `ContextAwareValidator` — reserve the name now or defer.
- [ ] `kedro catalog validate` — resolve-only by default vs full-data.
- [ ] `kedro.validators` entry-point group — v1 or v1.x.

**Deliverable:** updated tech-design notes + a "decisions locked / still open" summary posted to #5390.

---

## SUB-ISSUE 2 — Core: `kedro.validation` package + Pandera adapter

**Type:** Task · **Depends on:** Sub-issue 1

The backend-agnostic core plus the Pandera reference adapter. *(Prototype exists — productionise, review, harden.)*

**Scope:**
- [ ] `Validator` protocol (`validate(data) -> data`; any raise == failure), `CheckFailure`, `DataValidationError`, `ValidationConfigurationError`.
- [ ] `ValidatorSpec` (`from_config`/`to_config`; shorthand + long form; strict key validation; YAML 1.1 `on:` normalisation).
- [ ] `resolve_validator` (adapters → class-instantiate → instance → callable; the `runtime_checkable` ordering guard) + `CallableValidator`.
- [ ] `preflight_check` (`find_spec`, top-level package only).
- [ ] Pandera adapter: multi-namespace detection (`pandera.pandas/polars/pyspark`), grouped `failure_cases` → `CheckFailure` (capped examples), `coerce`, options forwarding; pyspark accessor-error branch behind an experimental flag.
- [ ] No module-level pandera import; graceful degradation when pandera absent.

**Acceptance:** unit tests for spec parsing, resolution ordering (incl. the footgun), and Pandera failure grouping/coercion; `pandera` optional.

---

## SUB-ISSUE 3 — Core: `DataCatalog` validator funnel + framework wiring

**Type:** Task · **Depends on:** Sub-issue 2

Wire validation into the catalog load/save path and the framework. *(Prototype exists — productionise, review, harden.)*

**Scope:**
- [ ] Reserve `VALIDATOR_KEY`; capture the spec in `_add_from_config` (cleaned config copy, resolver store not mutated); defensive pop in `parse_dataset_definition`.
- [ ] `_maybe_validate` on `load`/`save` (fast-path dict miss; lazy import; cached resolution; enrichment with dataset name + mode; `severity: warn`; `skip_load_after_save`).
- [ ] Lifecycle: `__setitem__` replacement clears spec; `release()`; `to_config()` re-injection; `__getstate__` drops resolved cache (ParallelRunner).
- [ ] `validators` property; `validation_enabled` default True on `DataCatalog`.
- [ ] `DATASET_VALIDATION` project setting + `KEDRO_DATASET_VALIDATION` env var (env wins both ways, read in `kedro.io`); context integration; custom-`DATA_CATALOG_CLASS` `hasattr` warning.

**Acceptance:** integration tests for load/save, factories, versioning/transcoding, ParallelRunner pickling, telemetry-shaped rebuild idempotence, kill-switch precedence; no regression in `tests/io/`.

---

## SUB-ISSUE 4 — Public API + `kedro catalog validate` CLI

**Type:** Task · **Depends on:** Sub-issue 3

The programmatic surface for IDEs/notebooks/CI. *(Prototype has the API; CLI is new.)*

**Scope:**
- [ ] `validate_dataset(catalog, name, ...)` and `validate_catalog(catalog, ...)` → `ValidationResult` (never raises for outcomes; explicit calls always validate; `error_type` discriminator; `raise_if_failed`; JSON-safe `to_dict`).
- [ ] `kedro catalog validate [--resolve-only] [--pipeline] [dataset ...]` (non-zero exit on failed/errored; pattern entries resolved against pipelines).

**Acceptance:** status-taxonomy tests (passed/failed/skipped/errored), factory-pattern coverage, CLI exit codes; `to_dict` round-trips through `json.dumps`.

---

## SUB-ISSUE 5 — Documentation

**Type:** Task · **Depends on:** Sub-issues 3–4

**Scope:**
- [ ] New "Data validation" page (quick-start, long form, `schemas/` convention, per-backend eager/lazy notes).
- [ ] Rewrite `docs/integrations-and-plugins/pandera.md` to lead with `validator:`; demote the hook recipe.
- [ ] Catalog reference: reserve `validator:` alongside `versioned`/`credentials`.
- [ ] Coercion-changes-data callout + release notes; raw-access bypass contract.

---

## SUB-ISSUE 6 — kedro-starters: `schemas/` scaffold (sibling repo)

**Type:** Task · **Repo:** `kedro-org/kedro-starters` · **Release-coupled**

**Scope:**
- [ ] Add `src/<pkg>/schemas/` with one example schema to spaceflights-pandas (+ viz variant); a commented-out `validator:` line in `catalog.yml`.
- [ ] Coordinate release timing with the core PRs.

---

## SUB-ISSUE 7 — Community / Pandera outreach

**Type:** Task

**Scope:**
- [ ] Loop in @deepyaman on the implementation PRs (he asked to be included).
- [ ] Reach out to Niels/Neeraj (Pandera) for a review of the adapter contract (public API only: `DataFrameModel`, `validate(lazy=)`, `SchemaErrors.failure_cases`).
- [ ] Credit kedro-pandera as inspiration in the launch announcement; capture any design lessons.
