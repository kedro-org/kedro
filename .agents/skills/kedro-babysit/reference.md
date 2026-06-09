# Kedro Babysit — Reference

Detailed reference for the `kedro-babysit` skill. Read sections selectively — use the section headers to find what you need.

For the **invocation tracks** (L = Local dev / C = CI diagnosis & fix) and which workflow steps each track requires, see [SKILL.md](SKILL.md) section "How to invoke this skill". This reference does not duplicate that routing — it just provides the underlying recipes each step calls into.

---

## Environment setup

The skill must run inside an isolated Python environment. It refuses to use system Python or the conda `base` env to avoid polluting the user's system packages.

> Several recipes below reference [`uv`](https://github.com/astral-sh/uv) — Astral's fast Python installer / venv manager. Where present, the scripts and Make targets use it; if not installed, they fall back to `python -m venv` and stdlib `pip`.

### Detection rules

An env is considered "active and isolated" when:

- `$VIRTUAL_ENV` is set (any venv, including `uv venv`-created), **or**
- `$CONDA_PREFIX` is set **and** `$CONDA_DEFAULT_ENV != "base"`.

`scripts/bootstrap_env.sh` checks both and prints the active env's path + Python version. `scripts/run_local_checks.sh` enforces the same rule with a hard guard (exit 64 if neither condition holds).

### Python version

Kedro supports **Python 3.10–3.14** (see [pyproject.toml `requires-python`](../../../pyproject.toml) and the [CI matrix in all-checks.yml](../../../.github/workflows/all-checks.yml)).

`bootstrap_env.sh` resolves the env's Python version as follows, in order:

1. `--python <version>` if explicitly passed (no validation; user's choice).
2. Else, the version of the current `python` interpreter on PATH, **if** it's in 3.10–3.14.
3. Else, falls back to **3.11** (the version the lint job uses on CI).

For the install flow (env already active), the script prints a soft warning if the active env's Python is outside 3.10–3.14 — it does not refuse, since the user has already chosen.

### Create a venv (manual recipe)

```bash
uv venv .venv --python 3.11    # or any version in 3.10–3.14; omit --python to use the current
source .venv/bin/activate
```

Fallback if `uv` is not installed:

```bash
python3.11 -m venv .venv       # or python3.10 / python3.12 / python3.13 / python3.14
source .venv/bin/activate
```

### Create a conda env (manual recipe)

```bash
conda create -n kedro-babysit python=3.11    # or any version in 3.10–3.14
conda activate kedro-babysit
```

### Install dependencies

After activating the env, run:

```bash
make install-test-requirements   # uv pip install -e ".[test]"
make install-pre-commit          # pre-commit install --install-hooks
```

If the PR touches `docs/` or `**.md`, also run:

```bash
make install-docs-requirements   # uv pip install -e ".[docs]"
```

### System tools

Three external tools may be required depending on what checks run:

| Tool     | Used by                          | Required for             |
| -------- | -------------------------------- | ------------------------ |
| `gh`     | `watch_ci.sh`, `bootstrap_env.sh`| All CI interactions      |
| `vale`   | `make language-lint`             | Docs language linter     |
| `lychee` | `make linkcheck`                 | Docs link check          |

Install hints (skill prints these if missing; never installs them itself):

- **macOS**: `brew install gh vale lychee`
- **Linux (Debian/Ubuntu)**: `sudo apt install gh`, `brew install vale` (via Linuxbrew) or download from [vale releases](https://github.com/errata-ai/vale/releases), `cargo install lychee` (or download from [lychee releases](https://github.com/lycheeverse/lychee/releases))
- **Windows**: download from each tool's GitHub releases page: [gh](https://github.com/cli/cli/releases), [vale](https://github.com/errata-ai/vale/releases), [lychee](https://github.com/lycheeverse/lychee/releases)

Docs checks that depend on missing system tools are reported as `[SKIP missing tool]` rather than `[FAIL]`.

---

## Sandbox & permissions

When invoking the commands below through a sandboxed shell tool, **request the listed permissions upfront** — guessing wrong wastes a run.

| Command | Permissions |
|---|---|
| `make test`, `pytest …` (any path) | **`all`** |
| `make linkcheck`, `bash scripts/watch_ci.sh`, `bash scripts/bootstrap_env.sh` (install flow) | **`network`** |
| `make lint`, per-hook recipes (`pre-commit run …`, `ruff …`, `mypy …`, `lint-imports`), `make language-lint` | default |
| `bash scripts/run_local_checks.sh` | union of the above based on the plan it prints |

**Rule for `pytest`**: always `all`, regardless of which path or test method you're targeting. Kedro's shared CLI test fixtures invoke `cookiecutter` during fixture setup, which writes `~/.cookiecutter_replay/<template>.json` outside the workspace. Some narrow paths (`tests/io/...`, `tests/runner/...`) don't strictly need it, but the cost of an unnecessary approval click is trivial vs. wasting a 6-min test run on a sandbox block.

---

## CI-to-local mapping

Canonical mapping of CI check name -> local invocation. The skill always prefers the Make target.

| CI check                     | Workflow file                                                          | Local command                                              | Notes                                                                                                              |
| ---------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `lint`                       | [lint.yml](../../../.github/workflows/lint.yml)                        | `make lint` (full sweep, 3–5 min) **or** targeted recipes  | See "Fast lint iteration" below. Fires on both code and docs PRs.                                                  |
| `unit-tests`                 | [unit-tests.yml](../../../.github/workflows/unit-tests.yml)            | `make test` (~6 min)                                       | See cookbook entry "`unit-tests` failure" below. Coverage `fail_under = 100` enforced via `pyproject.toml`.        |
| `e2e-tests`                  | [e2e-tests.yml](../../../.github/workflows/e2e-tests.yml)              | **Out of scope locally** (would be `make e2e-tests`)       | See cookbook entry "`e2e-tests` failure" below.                                                                    |
| `detect-secrets`             | [detect-secrets.yml](../../../.github/workflows/detect-secrets.yml)    | `git ls-files -z \| xargs -0 detect-secrets-hook --baseline .secrets.baseline` | **No Make target.** Full-tree scan. Differs from the pre-commit hook in `make lint` (which only checks changed files) and can fail in CI even when `make lint` is green. |
| `docs-linkcheck`             | [docs-linkcheck.yml](../../../.github/workflows/docs-linkcheck.yml)    | `make linkcheck`                                           | `mkdocs build --strict` + `lychee --max-concurrency 32 --exclude "@.lycheeignore" site/`. Slow + needs network. Requires `lychee`. **CI fires on any `**.md` change; `run_local_checks.sh` auto-detect only fires on `docs/**`** — for `*.md` files outside docs/ (`RELEASE.md` etc.), invoke `make linkcheck` directly if you want to pre-check, or rely on Track C after push. |
| `docs-language-linter`       | [docs-language-linter.yml](../../../.github/workflows/docs-language-linter.yml) | `make language-lint dir=docs`                              | `vale docs`. **Non-blocking** — `merge-gatekeeper` ignores `runner / vale` (see the `ignored:` setting in [merge-gatekeeper.yml](../../../.github/workflows/merge-gatekeeper.yml)). Requires `vale`. Same auto-detect divergence as `docs-linkcheck` above. |
| `merge-gatekeeper`           | [merge-gatekeeper.yml](../../../.github/workflows/merge-gatekeeper.yml) | n/a                                                        | Aggregator. Turns green when all required checks pass. Nothing to fix directly.                                    |
| `pipeline-performance-test`  | [pipeline-performance-test.yml](../../../.github/workflows/pipeline-performance-test.yml) | n/a                                                        | Label-triggered (only fires when a maintainer adds the `performance` label). Reports timing, not pass/fail. The skill surfaces the timing delta but does not auto-fix perf regressions. |
| DCO sign-off                 | GitHub App `dco` (not a workflow file)                                 | `git log <base>..HEAD --format='%H %(trailers:key=Signed-off-by)'` | Detects missing `Signed-off-by:` trailers. See "DCO sign-off recipes" below.                                       |

All other workflows in [.github/workflows/](../../../.github/workflows/) (`benchmark-performance`, `check-release`, `nightly-build`, `release-starters`, `auto-merge-prs`, `sync`, `label-community-issues`, `no-response`) are scheduled, release-triggered, or issue-only — out of scope for this skill.

---

## DCO sign-off recipes

Every commit must have a `Signed-off-by: Name <email>` trailer. The DCO GitHub App rejects PRs with unsigned commits.

### Detect missing sign-offs

```bash
git log <base>..HEAD --format='%H %(trailers:key=Signed-off-by)'
```

Any line without a `Signed-off-by:` trailer is a missing sign-off.

### Fix the last commit

```bash
git commit --amend --no-edit --signoff
git push --force-with-lease
```

### Fix all commits since base

```bash
git rebase <base> --signoff
git push --force-with-lease
```

This is the typical case the skill handles. **Always warn the user before force-push** — it rewrites shared history.

### Sign new commits going forward

```bash
git commit --signoff -m "Your message"
```

### Install a local hook to auto-sign all commits

```bash
make sign-off
```

This installs `.git/hooks/commit-msg` to append `Signed-off-by:` automatically (see the `sign-off` target in [Makefile](../../../Makefile)). One-time setup per clone.

---

## Fast lint iteration

`make lint` runs `pre-commit run -a --hook-stage manual` (every hook on every tracked file) **plus** `mypy kedro --strict ...` on the whole package. On a clean run that's typically 3–5 minutes. **For per-failure iteration, use the targeted commands below instead — most complete in seconds.** Reserve `make lint` for the final pre-push check (it's what `scripts/run_local_checks.sh` calls in Step 5a of the workflow).

### Targeting strategy

1. **Identify which hook is failing** from the CI log or local output (the hook name appears in `make lint` output as `>>>>>>>> <hook name>`).
2. **Run only that hook on only the changed files**: `pre-commit run <hook-id> --files <file1> <file2> ...`. If you don't know the changed file list, derive it relative to the PR's base branch:
   ```bash
   BASE="$(gh pr view --json baseRefName -q .baseRefName 2>/dev/null || echo main)"
   git diff --name-only "origin/$BASE"...HEAD
   ```
   This mirrors the auto-detect logic in `scripts/run_local_checks.sh`. Don't hardcode `origin/main` — Kedro PRs may target `develop` or other branches.
3. **For tools that can be invoked directly**, skip pre-commit altogether (faster, no hook overhead): see the per-tool recipes below.
4. **Re-run `make lint`** only as a final belt-and-suspenders check before commit/push.

### Per-hook recipes

| Failing CI / local check | Targeted command (fast) | Notes |
|---|---|---|
| `ruff` (lint) | `ruff check --fix <file>` or `pre-commit run ruff --files <file>` | The hook is configured with `--fix --exit-non-zero-on-fix`, so it auto-fixes and reports. Direct `ruff check --fix` is fastest. |
| `ruff-format` | `ruff format <file>` or `pre-commit run ruff-format --files <file>` | Reformats in place. |
| `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-json`, `debug-statements`, `requirements-txt-fixer`, `check-added-large-files`, `check-case-conflict`, `check-merge-conflict` | `pre-commit run <hook-id> --files <file>` | Auto-fixers (whitespace, EOF) modify in place; checkers report violations. |
| `imports` (Import Linter) | `lint-imports --config pyproject.toml` | The hook has `pass_filenames: false`, so `--files` is ignored — it always scans the whole project. Direct invocation is the same speed but skips pre-commit's setup overhead. Contracts live in the `[[tool.importlinter.contracts]]` blocks of [pyproject.toml](../../../pyproject.toml). |
| `detect-secrets` (pre-commit hook on changed files) | `pre-commit run detect-secrets --files <file>` | Different from the CI's full-tree scan. To reproduce CI's check, see the cookbook entry below. |
| `mypy` | `mypy <file> --strict --allow-any-generics --no-warn-unused-ignores` or `mypy <subpackage>/ --strict --allow-any-generics --no-warn-unused-ignores` | Single file: ~5–10s (vs. 1–2 min for the whole `kedro/` package). Mypy config in the `[tool.mypy]` section of [pyproject.toml](../../../pyproject.toml). |

### Convenience: `make lint hook=<id>`

The Makefile already supports `make lint hook=<hook-id>` (see the `lint` target in [Makefile](../../../Makefile)) — runs only the named pre-commit hook (still on `-a` all files), then unconditionally runs mypy after. Useful when you don't have a changed-file list, but slower than the per-hook recipes above because it always re-runs mypy.

### When to fall back to `make lint`

Run the full sweep when:
- Final verification before commit/push (or just call `bash scripts/run_local_checks.sh` which wraps it).
- You've changed something cross-cutting (renamed a public API, edited many files) and want the whole-tree confidence.
- The targeted recipes pass but you suspect side effects in untouched files.

---

## Common CI failures and fixes

Short cookbook keyed by CI check. Fast-verify commands for all `lint` sub-cases (ruff, ruff-format, lint-imports, mypy) live in the [Per-hook recipes](#per-hook-recipes) table above — the entries below cover non-lint failures plus the lint cases that need extra context (contracts, config, baselines).

### `lint` — `lint-imports` (Import Linter) failure

Fast verify is in the per-hook recipes table. Read the violated contract from the `[[tool.importlinter.contracts]]` blocks in [pyproject.toml](../../../pyproject.toml):

1. **Layered**: `framework.cli > framework.session > framework.context > framework.project > runner > io > pipeline > config`. Higher layers may import lower layers, never the reverse.
2. **Independence**: `kedro.pipeline` and `kedro.io` cannot import each other.
3. **Forbidden**: `kedro.config` cannot import `kedro.runner`/`io`/`pipeline` (and vice versa, with explicit exceptions for `framework.context.context` and `framework.session.session`).

Fix the import. Only if the architectural change is intentional (rare), propose adjusting `ignore_imports` in the relevant contract — but stop and ask the user first.

### `lint` — mypy failure

Fast verify is in the per-hook recipes table. Add type annotations or stubs. The repo's mypy config (the `[tool.mypy]` section of [pyproject.toml](../../../pyproject.toml)) sets `ignore_missing_imports = true` and `disable_error_code = ["misc", "untyped-decorator"]` — relevant when error messages reference these codes.

### `unit-tests` failure

Fast verify: `pytest --no-cov tests/path/to/test_thing.py::TestClass::test_method` (single test, sub-second to seconds), or `pytest --no-cov tests/path/to/test_module.py` (single file).

Pass `--no-cov` for targeted iteration — pytest's `addopts` in [pyproject.toml](../../../pyproject.toml) always applies `--cov ...` with `fail_under = 100`, so even a passing single-test run will exit non-zero on the coverage gate without it. (`--no-cov-on-fail` only suppresses the report when tests *fail*, not when they pass with sub-100% coverage.)

If the failure is real, fix it. If coverage drops below `fail_under = 100` (set in the `[tool.coverage.report]` section of [pyproject.toml](../../../pyproject.toml)), add unit tests for the new lines — coverage is enforced strictly. The full coverage check is only meaningful via the final `make test` run after targeted iteration (~6 min wall-clock — pre-warn the user).

### `e2e-tests` failure

**Out of scope for local repro.** The skill does not run e2e tests locally. Use `bash scripts/watch_ci.sh` to dump the failed-job logs from CI and share them with the user; ask whether they want to investigate locally (which is outside this skill's scope) or address the failure directly from the CI output.

### `detect-secrets` failure

Rerun the full-tree scan locally:

```bash
git ls-files -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline
```

If it's a real secret, **remove it from the file** (and rotate it). If it's a false positive, regenerate the baseline:

```bash
detect-secrets scan --baseline .secrets.baseline
```

Then commit the updated `.secrets.baseline`.

### `docs-linkcheck` failure

Run `make linkcheck` locally. Fix broken links in `docs/`, or add allowed-broken patterns to `.lycheeignore`. The linkcheck builds with `--strict`, so MkDocs nav errors and broken cross-references also fail.

### `docs-language-linter` (vale) failure

Informational only — `merge-gatekeeper` ignores `runner / vale`, so this never blocks merge. Reproduce with `make language-lint dir=docs`. Fix if the suggestion is reasonable; otherwise ignore.

### `pipeline-performance-test` regression

Not auto-fixed. The skill reports the timing delta and asks the user to investigate manually. This check only fires when a maintainer adds the `performance` label to the PR.

### `merge-gatekeeper` red

Nothing to fix directly. Turns green when all required checks pass.

---

## gh CLI cheatsheet

Commands the skill uses, in roughly the order they appear in the workflow.

```bash
# Preflight
gh auth status                                       # verify authenticated

# Identify the PR
gh pr view --json number,title,baseRefName,headRefName

# Snapshot
gh pr view --json mergeable,mergeStateStatus,headRefOid,files
gh pr checks                                         # current CI status

# Snapshot CI (used by watch_ci.sh)
gh pr checks --json name,bucket,workflow,link        # current state, non-blocking
                                                     # bucket ∈ {pass, fail, pending, skipping, cancel}
gh run list --branch <branch> --limit 20 --json databaseId,name,conclusion
gh run view <id> --log-failed                        # dump only failed steps

# After a fix
gh pr checks                                         # re-check status
```

### `watch_ci.sh` behavior

`bash scripts/watch_ci.sh` is **snapshot-only** by design — it fetches the current CI state for the PR, dumps failed-step logs (last `--tail` lines, default 200) for any check already in `bucket=fail`, and exits. It does **not** block waiting for in-flight checks. To re-check later, just run it again.

Flags:

- `--pr <number-or-url>`: override PR detection from the current branch.
- `--tail <N>`: lines of log to dump per failed run (default 200).

This avoids long blocking sessions where the agent is idle waiting on CI. If the user wants to know when CI finishes, they re-invoke the skill.
