# Tasks — Exclude benchmark tests from packaging

## Preconditions

- [x] Backlog item `github:ravi-kumar-pilla/kedro-forked#1` validated
- [x] Plan validated with `pdlc plan validate`

## Tasks

### 1. Configure setuptools package discovery

- [x] Add `exclude = ["kedro_benchmarks*"]` under `[tool.setuptools.packages.find]` in `pyproject.toml`; verify with `grep -A2 'packages.find' pyproject.toml`

### 2. Verify packaging and tests

- [x] Build wheel with `pip wheel . -w /tmp/kedro-wheel-test --no-deps`; confirm `unzip -l /tmp/kedro-wheel-test/*.whl | grep kedro_benchmarks` produces no matches
- [x] Run `pytest tests/ -x -q`; confirm exit code 0
- [x] Confirm `kedro_benchmarks/` exists and `grep benchmark_dir asv.conf.json` shows `kedro_benchmarks`

## Verification

- [x] `pyproject.toml` adds `exclude = ["kedro_benchmarks*"]` under `[tool.setuptools.packages.find]`
- [x] A local wheel build (`pip wheel .`) does not install `kedro_benchmarks` into site-packages
- [x] `pytest tests/` passes with no regressions
- [x] `kedro_benchmarks/` remains in the repo and `asv.conf.json` still points `benchmark_dir` at it
