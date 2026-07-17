# Dataset Validation — issue tracking plan (post tech design, 15 Jul)

Updated to reflect the tech design outcomes: extras and API name locked, CLI split out
as its own decision issue, tests folded alongside the implementation PRs plus one
integration matrix issue, outreach added (Merel), docs signature note added (Ravi).
PR 1 split in two per Merel's smaller-PRs ask.

How to set up on kedro-org/kedro:

1. Create the PARENT below, type Parent. Do NOT reuse #5390 (it is the exploration
   spike and Elena retyped it deliberately); link back to it instead.
2. Create each sub-issue (type Task, except the CLI one which suits a discussion or
   spike type) and link them via the Sub-issues panel on the parent.
3. Add everything to the Kedro board backlog + the Validation of data & parameters
   milestone. Bring to next grooming for sizing and assignment only.
4. After the parent exists, comment on #5390 linking it (its closing chapter).

Shared context block to paste at the top of EVERY sub-issue:

> Part of [Implementation] Dataset Validation (KEP-10) — see parent issue.
> Design: kedro-org/kedro discussion #5602 · Tech design summary: [link to the
> 15 Jul comment] · Prototype: PR [#XXXX] / branch `feat/kep10-dataset-validation`
> (working implementation, reviewed and green) · Runnable demo:
> https://github.com/SajidAlamQB/spaceflights-validation-demo
> The prototype is the base to work from, not a reference to rewrite.

---

## PARENT — [Implementation] Dataset Validation (KEP-10)

**Type:** Parent · **Milestone:** Validation of data & parameters

### Goal
Implement catalog-native dataset validation per the accepted KEP-10 (#5602): a
`validator:` key on catalog entries enforced in the DataCatalog load/save path,
with a pluggable Validator protocol and Pandera as the reference backend.

### State
Working prototype on `feat/kep10-dataset-validation` (PR #XXXX): full implementation,
reviewed, demo project public. Tech design held 15 Jul — summary comment: [link].

### Decisions locked at tech design
- Per-backend extras: `kedro[pandera-pandas]`, `kedro[pandera-polars]`, `kedro[pandera-pyspark]`
- Public API name: `validate_dataset`
- Entry-point group deferred until a second backend exists (name reserved in docs)
- CLI split out into its own decision issue (naming/semantics/existence open)

### Sub-issues
- [ ] 1. `kedro.validation` core package + Pandera adapter
- [ ] 2. DataCatalog validation funnel + settings wiring
- [ ] 3. Programmatic API (`validate_dataset` / `validate_catalog`)
- [ ] 4. Test coverage: integration matrix
- [ ] 5. CLI: decide naming, semantics, and whether it ships
- [ ] 6. Documentation
- [ ] 7. Starter example
- [ ] 8. User-validation outreach

---

## SUB 1 — `kedro.validation` core package + Pandera adapter

**Type:** Task · [shared context block]

Purely additive PR, no existing kedro modules touched — split from the funnel PR so
the risky `kedro/io` diff reviews separately (smaller-PRs ask from tech design).

Scope (productionise from the prototype):
- [ ] `Validator` protocol, `ValidatorSpec` (shorthand + long form, strict key
      validation, YAML 1.1 `on:` normalisation), `CheckFailure`,
      `DataValidationError` (bounded grouped rendering), `ValidationConfigurationError`
- [ ] `resolve_validator` (adapters -> class instantiation -> instance -> callable;
      never protocol-check a class object) + `CallableValidator` + `preflight_check`
- [ ] Pandera adapter: modern namespace detection (`pandera.pandas/polars/pyspark`),
      grouped `failure_cases` -> `CheckFailure` (capped examples), coercion,
      options forwarding; pyspark accessor branch kept but NOT advertised
- [ ] Decision sweep: per-backend extras in pyproject; install-hint strings updated
- [ ] Unit tests: spec parsing, resolution ordering, adapter behaviour
- [ ] Action item from tech design: verify `SchemaErrors.failure_cases` shape
      stability pandera 0.24 -> current

## SUB 2 — DataCatalog validation funnel + settings wiring

**Type:** Task · Depends on Sub 1 · [shared context block]

The `kedro/io` + `kedro/framework` diff (~25 lines on the load/save path plus
lifecycle). Flagged at tech design as the PR needing the most eyes — request a
catalog-side reviewer (Elena).

Scope:
- [ ] `VALIDATOR_KEY` reservation + defensive strip in `parse_dataset_definition`
- [ ] Spec capture in `_add_from_config` (cleaned copy; resolver store not mutated)
- [ ] `_maybe_validate` guard ladder in `load`/`save`; error enrichment
      (dataset name + mode); `severity: warn`; `skip_load_after_save`
- [ ] Lifecycle: `__setitem__` replacement clears specs, materialisation keeps them;
      `release()`; `to_config()` re-injection; pickling drops resolved cache
- [ ] `DATASET_VALIDATION` setting + `KEDRO_DATASET_VALIDATION` env var (env wins,
      read inside kedro.io); context propagation + custom-catalog warning
- [ ] Wire `preflight_check` at catalog build (exists in prototype, unwired)
- [ ] No-op-path micro-benchmark in kedro_benchmarks (defends the hot-path cost)
- [ ] Funnel + lifecycle + kill-switch tests

## SUB 3 — Programmatic API

**Type:** Task · Depends on Sub 2 · [shared context block]

`validate_dataset(catalog, name, ...)` (renamed per tech design) and
`validate_catalog(...)` returning `ValidationResult`. Machine consumers only
(VSCode extension, CI scripts) — never raises for outcomes, explicit calls always
validate. NO CLI in this issue (see Sub 5).

Scope:
- [ ] Rename `validate_catalog_dataset` -> `validate_dataset` across code and docs
- [ ] `ValidationResult` statuses + `error_type` discriminator; JSON-safe `to_dict`
- [ ] Factory-pattern enumeration for `validate_catalog` (prototype TODO)
- [ ] API status-taxonomy tests

## SUB 4 — Test coverage: integration matrix

**Type:** Task · Depends on Subs 1–3 · [shared context block]

The prototype's ~750-line suite lives on the prototype branch and was deliberately
kept out of the implementation PR; reintroduce it incrementally with Subs 1–3, then
extend to the matrix the KEP commits to:
- [ ] ParallelRunner (specs survive pickling, workers re-resolve and raise)
- [ ] ThreadRunner concurrent first-use resolution
- [ ] Factory patterns incl. `{placeholder}` interpolation in validator strings
- [ ] Generator nodes (per-chunk save semantics pinned as contract)
- [ ] Transcoded entries, versioned loads, CachedDataset top-level entries
- [ ] Plugin-rebuilt catalog idempotence (kedro-telemetry pattern)

## SUB 5 — CLI: decide naming, semantics, and whether it ships

**Type:** Spike / needs-discussion · [shared context block]

Reopened at tech design (deliberately unresolved — do not implement until decided):
- `kedro catalog validate` reads as validating catalog STRUCTURE, not data
  (deepyaman); resolve-only-as-default then feels like a mislabelled dry run
- Is bulk validate-everything a real workflow? Needs evidence, not a default
- Merel: CLI is a nice-to-have; the primary flow is `kedro run`; if it exists it is
  a deliberate separate step (e.g. pre-merge data-quality gate), and it must be a
  separate PR from the API
- Interactive single-dataset validation may just be documented pandera usage
  (`Schema.validate(catalog.load(...))`)

Deliverable: a decision comment (options + recommendation) on this issue, then
either an implementation issue or a wontfix-for-now close.

## SUB 6 — Documentation

**Type:** Task · Depends on Subs 1–3 · [shared context block]

- [ ] New data validation page: quick start, `validator:` long form, `schemas/`
      convention (convention NOT enforcement), per-backend install matrix
      (pandas + Polars advertised; pyspark experimental)
- [ ] Rewrite `docs/integrations-and-plugins/pandera.md` to lead with `validator:`;
      demote the hook recipe; credit kedro-pandera as inspiration
- [ ] Signature note (Ravi, tech design): node signatures stay `pd.DataFrame`;
      annotations are documentation; `pd.DataFrame[Schema]` is the recommended
      visible form; unlike parameter validation no model instance is injected —
      explain why (datasets are data, not config)
- [ ] Release notes: coercion changes data identity; `validator` reserved key
- [ ] Interactive validation recipe (the documented pandera path from tech design)

## SUB 7 — Starter example

**Type:** Task · Repo: kedro-starters · Release-coupled · [shared context block]

New starter example (or modify an existing spaceflights starter — decide with the
starters owners) showing the `validator:` key: one example schema in
`src/<pkg>/schemas/`, one commented-out catalog line. Public demo repo is the
reference: https://github.com/SajidAlamQB/spaceflights-validation-demo

## SUB 8 — User-validation outreach

**Type:** Task · Runs in parallel with Subs 1–3 (Merel: start now, not after)

- [ ] Identify parameter-validation early users + Adeikalam's team (they run the
      schemas-folder pattern in production and asked for this feature)
- [ ] Share the demo repo + branch install instructions; collect structured feedback
      (does `validator:` fit their workflow? severity/warn adoption path? CLI demand
      — feeds Sub 5)
- [ ] Pandera-side review of the adapter contract (deepyaman asked to be included;
      Niels/Neeraj) — surface is three public APIs: `DataFrameModel`,
      `validate(lazy=)`, `SchemaErrors.failure_cases`
