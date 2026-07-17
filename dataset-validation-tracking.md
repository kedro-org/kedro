# Dataset Validation — sub-issue bodies, copy-paste ready

Each sub-issue below is pre-formatted for the kedro-org feature request template
(Description / Context / Possible Implementation / Possible Alternatives).
Copy everything under a sub-issue heading straight into the GitHub form.

All links are filled in: prototype PR #5666, parent issue #5677, tech design
summary, recording and Miro board (in the parent's Context).

Setup reminders:
1. Parent issue type: Parent. Sub-issues: Task (Sub 5 suits Spike/discussion).
2. Link each via the Sub-issues panel on the parent.
3. Board backlog + "Validation of data & parameters" milestone on all.
4. Comment on #5390 linking the parent once created.
5. Grooming is for sizing and assignment only; scoping is already decided.

---

## PARENT — [Implementation] Dataset Validation (KEP-10)

## Description
Implement catalog-native dataset validation per the accepted KEP-10 (#5602): a
`validator:` key on catalog entries enforced in the DataCatalog load/save path,
with a pluggable Validator protocol and Pandera as the reference backend.

## Context
Follows the exploration initiative #5390 and spike #5391. KEP-10 accepted with +3
TSC votes. Tech design held 15 Jul: [summary](https://github.com/kedro-org/kedro/issues/5390#issuecomment-5001293477) ·
[recording](https://zoom.us/rec/play/mTxLoJQNvMHAj2BfBhKYlwI-i_xxY2vyo9GMsopYMH2id6AZqH2sEO3U7zUeHCLgj0pZDLlHVFnNkVwz.4H1PpBBHxCjs_IrH?accessLevel=meeting&canPlayFromShare=true&from=share_recording_detail&continueMode=true&oldStyle=true&componentName=rec-play&originRequestUrl=https%3A%2F%2Fzoom.us%2Frec%2Fshare%2F7IQpcMkcoVSHNLM8rdkDXc6mX-iGPCSJlIRZgrRcBKSSdZr4QahVNi8P7HX9BWt-.YIxNpBXPdmOxtYTv) ·
[Miro board](https://miro.com/app/board/uXjVH7zKmY4=/)
Working prototype:
PR #5666 / branch `feat/kep10-dataset-validation`, plus a public runnable demo
at https://github.com/SajidAlamQB/spaceflights-validation-demo

Decisions locked at tech design:
- Per-backend extras: `kedro[pandera-pandas]`, `kedro[pandera-polars]`, `kedro[pandera-pyspark]`
- Public API name: `validate_dataset`
- Entry-point group deferred until a second backend exists (name reserved in docs)
- CLI split out into its own decision issue (naming/semantics/existence still open)

## Possible Implementation
Sub-issues, in rough order:
- [ ] 1. `kedro.validation` core package + Pandera adapter
- [ ] 2. DataCatalog validation funnel + settings wiring
- [ ] 3. Programmatic API (`validate_dataset` / `validate_catalog`)
- [ ] 4. Test coverage: integration matrix
- [ ] 5. CLI: decide naming, semantics, and whether it ships
- [ ] 6. Documentation
- [ ] 7. Starter example
- [ ] 8. User-validation outreach

## Possible Alternatives
Design alternatives (type-hint discovery, wrapper dataset, hooks-based enforcement,
Pandera-only coupling) were evaluated and rejected in KEP-10; see #5602.

---

## SUB 1 — kedro.validation core package + Pandera adapter

## Description
Add the `kedro.validation` core package for catalog-native dataset validation: the
`Validator` protocol, validator spec parsing, resolution, structured errors, and the
Pandera reference adapter. Purely additive, no existing kedro modules touched. This
is deliberately split from the catalog funnel work so the `kedro/io` diff can be
reviewed separately (smaller-PRs ask from tech design).

## Context
Part of [Implementation] Dataset Validation (KEP-10), parent issue #5677.
Design: #5602 · Tech design summary: https://github.com/kedro-org/kedro/issues/5390#issuecomment-5001293477 · Prototype: PR #5666 /
branch `feat/kep10-dataset-validation` (working implementation, reviewed and green) ·
Runnable demo: https://github.com/SajidAlamQB/spaceflights-validation-demo
Implements the locked decisions on per-backend extras and install-hint strings.
The prototype is the base to work from, not a reference to rewrite.

## Possible Implementation
Productionise from the prototype branch:
- [ ] `Validator` protocol, `ValidatorSpec` (shorthand + long form, strict key
      validation, YAML 1.1 `on:` key normalisation), `CheckFailure`,
      `DataValidationError` (bounded grouped rendering), `ValidationConfigurationError`
- [ ] `resolve_validator` (adapters -> class instantiation -> instance -> callable;
      never protocol-check a class object) + `CallableValidator` + `preflight_check`
- [ ] Pandera adapter: modern namespace detection (`pandera.pandas/polars/pyspark`),
      grouped `failure_cases` -> `CheckFailure` with capped examples, coercion,
      options forwarding; pyspark accessor branch kept but not advertised
- [ ] Decision sweep: per-backend extras in pyproject, install-hint strings updated
- [ ] Unit tests: spec parsing, resolution ordering, adapter behaviour
- [ ] Tech design action item: verify `SchemaErrors.failure_cases` shape stability
      from pandera 0.24 to current

## Possible Alternatives
Design alternatives were settled in KEP-10 and the 15 Jul tech design; see Context.

---

## SUB 2 — DataCatalog validation funnel + settings wiring

## Description
Wire dataset validation into `DataCatalog.load()`/`save()` (roughly 25 lines on the
hot path plus lifecycle handling) and add the framework opt-out. This is the PR that
touches `kedro/io`, flagged at tech design as needing the most review scrutiny.

## Context
Part of [Implementation] Dataset Validation (KEP-10), parent issue #5677. Depends on
the core package sub-issue.
Design: #5602 · Tech design summary: https://github.com/kedro-org/kedro/issues/5390#issuecomment-5001293477 · Prototype: PR #5666 /
branch `feat/kep10-dataset-validation` · Demo:
https://github.com/SajidAlamQB/spaceflights-validation-demo
A catalog-side reviewer is explicitly requested for this one.

## Possible Implementation
Productionise from the prototype branch:
- [ ] `VALIDATOR_KEY` reservation + defensive strip in `parse_dataset_definition`
- [ ] Spec capture in `_add_from_config` (cleaned copy, resolver store not mutated)
- [ ] `_maybe_validate` guard ladder in `load`/`save`; error enrichment with dataset
      name and mode; `severity: warn`; `skip_load_after_save`
- [ ] Lifecycle: `__setitem__` replacement clears specs while materialisation keeps
      them; `release()`; `to_config()` re-injection; pickling drops resolved cache
- [ ] `DATASET_VALIDATION` setting + `KEDRO_DATASET_VALIDATION` env var (env wins,
      read inside kedro.io); context propagation + custom-catalog warning
- [ ] Wire `preflight_check` at catalog build (exists in prototype, currently unwired)
- [ ] No-op-path micro-benchmark in kedro_benchmarks (defends the hot-path cost)
- [ ] Funnel, lifecycle and kill-switch tests

## Possible Alternatives
Hooks-based enforcement and a wrapper dataset were evaluated and rejected in KEP-10
(see #5602); the funnel placement was reconfirmed at tech design.

---

## SUB 3 — Programmatic API (validate_dataset / validate_catalog)

## Description
Public functions to validate catalog datasets on demand: `validate_dataset(catalog,
name, ...)` and `validate_catalog(...)`, returning a structured `ValidationResult`
rather than raising. Built for machine consumers (the VSCode extension, CI scripts).
No CLI in this issue; that is a separate decision issue.

## Context
Part of [Implementation] Dataset Validation (KEP-10), parent issue #5677. Depends on
the funnel sub-issue.
Design: #5602 · Tech design summary: https://github.com/kedro-org/kedro/issues/5390#issuecomment-5001293477 · Prototype: PR #5666 /
branch `feat/kep10-dataset-validation` · Demo:
https://github.com/SajidAlamQB/spaceflights-validation-demo
Implements the locked rename to `validate_dataset`. Requested reviewer: @noklam,
since `ValidationResult` is the VSCode extension's integration contract.

## Possible Implementation
- [ ] Rename `validate_catalog_dataset` -> `validate_dataset` across code and docs
- [ ] `ValidationResult` statuses (passed/failed/skipped/errored) with the
      `error_type` discriminator; JSON-safe `to_dict`
- [ ] Explicit calls always validate (ignore global and per-dataset disable flags)
- [ ] Factory-pattern enumeration for `validate_catalog` (open TODO in prototype)
- [ ] API status-taxonomy tests

## Possible Alternatives
A raising API was rejected in KEP-10: IDE and CI consumers need structured results
without exception handling; `raise_if_failed()` restores raising behaviour on demand.

---

## SUB 4 — Test coverage: integration matrix

## Description
Build out the test suite for dataset validation, covering both the core behaviour
and the integration surfaces the KEP commits to. This is greenfield work: tests are
written from scratch against the implemented behaviour by whoever picks this up,
using the KEP's testing strategy section as the specification.

## Context
Part of [Implementation] Dataset Validation (KEP-10), parent issue #5677. Depends on
sub-issues 1 to 3.
Design: #5602 · Tech design summary: https://github.com/kedro-org/kedro/issues/5390#issuecomment-5001293477

## Possible Implementation
- [ ] ParallelRunner: specs survive pickling, workers re-resolve and raise
- [ ] ThreadRunner: concurrent first-use resolution
- [ ] Factory patterns incl. `{placeholder}` interpolation in validator strings
- [ ] Generator nodes: per-chunk save semantics pinned as documented contract
- [ ] Transcoded entries, versioned loads, CachedDataset top-level entries
- [ ] Plugin-rebuilt catalog idempotence (kedro-telemetry pattern)

## Possible Alternatives
N/A, test work.

---

## SUB 5 — CLI: decide naming, semantics, and whether it ships

## Description
`kedro catalog validate` was proposed in KEP-10 but reopened at the 15 Jul tech
design. The name reads as validating the catalog structure rather than running data
validation; a resolve-only default then feels like a mislabelled dry run; and it is
not established that bulk validate-everything is a real user workflow. Decide what,
if anything, ships.

## Context
Part of [Implementation] Dataset Validation (KEP-10), parent issue #5677.
Design: #5602 · Tech design summary: https://github.com/kedro-org/kedro/issues/5390#issuecomment-5001293477
Session positions: the command name is ambiguous (deepyaman); the CLI is a
nice-to-have since the primary flow is `kedro run`, and if it exists it should be a
deliberate separate step such as a pre-merge data quality gate, in its own PR
(merelcht); interactive single-dataset validation may need nothing new beyond
documented pandera usage, `Schema.validate(catalog.load(...))` (deepyaman).
The programmatic API is unaffected either way. User outreach (separate sub-issue)
should feed demand evidence into this decision.

## Possible Implementation
Deliverable is a decision comment on this issue (options + recommendation), then
either an implementation issue or a close as not planned.

## Possible Alternatives
- Ship `kedro catalog validate` with full data validation as the default and a
  `--resolve-only` dry-run style flag
- Rename to remove the ambiguity (for example `kedro catalog validate-data`) or
  split resolve checking into a separate lint-style command
- Ship resolve-only checking as part of an existing command instead of a new one
- Ship no CLI: document the interactive pandera path and rely on the programmatic
  API for CI, revisit on demand evidence

---

## SUB 6 — Documentation

## Description
User-facing documentation for dataset validation: a new docs page, a rewrite of the
pandera integration page, and release notes.

## Context
Part of [Implementation] Dataset Validation (KEP-10), parent issue #5677. Depends on
sub-issues 1 to 3.
Design: #5602 · Tech design summary: https://github.com/kedro-org/kedro/issues/5390#issuecomment-5001293477 · Demo:
https://github.com/SajidAlamQB/spaceflights-validation-demo
Includes the explicit ask from tech design (ravi-kumar-pilla) to document how node
signatures differ from parameter validation.

## Possible Implementation
- [ ] New data validation page: quick start, `validator:` long form, `schemas/`
      convention (convention, not enforcement), per-backend install matrix
      (pandas + Polars advertised; pyspark experimental)
- [ ] Rewrite `docs/integrations-and-plugins/pandera.md` to lead with `validator:`;
      demote the hook recipe; credit kedro-pandera as inspiration
- [ ] Signature note: node signatures stay `pd.DataFrame`; annotations are
      documentation; `pd.DataFrame[Schema]` is the recommended visible form; unlike
      parameter validation no model instance is injected, and why (datasets are
      data, not config)
- [ ] Release notes: coercion changes data identity; `validator` documented as a
      reserved catalog key
- [ ] Interactive validation recipe (the documented pandera path from tech design)

## Possible Alternatives
N/A, documentation work.

---

## SUB 7 — Starter example

## Description
Add a starter example showing the `validator:` key, either as a small new starter or
a modification to an existing spaceflights starter (decide with the starters owners).

## Context
Part of [Implementation] Dataset Validation (KEP-10), parent issue #5677. Lives in the
kedro-starters repo and is release-coupled with the kedro release that ships
validation.
Design: #5602 · Tech design summary: https://github.com/kedro-org/kedro/issues/5390#issuecomment-5001293477 · Reference implementation:
https://github.com/SajidAlamQB/spaceflights-validation-demo

## Possible Implementation
- [ ] One example schema in `src/<pkg>/schemas/`
- [ ] One commented-out `validator:` line in `catalog.yml`
- [ ] Keep it inert: no runtime effect until the user uncomments

## Possible Alternatives
A dedicated validation starter versus modifying spaceflights; decide with the
starters owners based on maintenance cost.

---

## SUB 8 — User-validation outreach

## Description
Validate the feature with real users during implementation rather than after
release (explicit ask from tech design).

## Context
Part of [Implementation] Dataset Validation (KEP-10), parent issue #5677. Runs in
parallel with sub-issues 1 to 3.
Design: #5602 · Tech design summary: https://github.com/kedro-org/kedro/issues/5390#issuecomment-5001293477 · Demo to share:
https://github.com/SajidAlamQB/spaceflights-validation-demo
Candidates: parameter-validation early users; Adeikalam's team (they run the
schemas-folder pattern in production and asked for this feature); Pandera
maintainers for the adapter contract review (deepyaman asked to be included;
Niels/Neeraj). Feedback on CLI demand feeds the CLI decision sub-issue.

## Possible Implementation
- [ ] Identify and contact candidate users; share the demo repo and branch install
      instructions
- [ ] Collect structured feedback: does `validator:` fit their workflow, is
      severity warn the right adoption path, is there real CLI demand
- [ ] Pandera-side review of the adapter contract; the surface is three public
      APIs: `DataFrameModel`, `validate(lazy=)`, `SchemaErrors.failure_cases`
