# Review — Exclude benchmark tests from packaging

## Status

- Disposition: approved
- Satisfied: yes
- Last round: 1
- Last reviewed: 2026-06-24

## Open blockers

## History

### Round 1 — 2026-06-24

**Deterministic checks**

- `pdlc plan validate --require-complete` — passed
- `pdlc backlog validate github:ravi-kumar-pilla/kedro-forked#1` — passed
- `pdlc plan review checks` — passed
  - `kedro-packaging-exclude` — passed
  - `kedro-packaging-wheel` — passed (no `kedro_benchmarks` paths in built wheel)
  - `pdlc-plan` — passed

**Agent review**

- [note] `pyproject.toml` adds `exclude = ["kedro_benchmarks*"]` under `[tool.setuptools.packages.find]`; matches upstream kedro-org/kedro#5604.
- [note] `kedro_benchmarks/` remains in the repository; `asv.conf.json` still references `benchmark_dir: kedro_benchmarks`.
- [note] All tasks and verification items in `tasks.md` are checked complete.
- [note] Spec delta R0001 (packaging theme) is satisfied by the implementation: wheel excludes benchmark package; source tree unchanged for ASV.
- [note] No `kedro/` Python code changed; mypy on `kedro/` reports no issues.
- [note] Full-suite `pytest tests/ -x` was run during implement (738 passed before an unrelated pre-existing failure in `test_run_logs_package_name_when_outside_project` on Python 3.13). Not a regression from this packaging change.

**Disposition:** approved — ready for `/pdlc-merge`.
