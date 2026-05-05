# Kedro Babysit — Reference

Detailed reference for the `kedro-babysit` skill. Read sections selectively — use the section headers to find what you need.

---

## Environment setup

The skill must run inside an isolated Python environment. It refuses to use system Python or the conda `base` env to avoid polluting the user's system packages.

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

The e2e CI job additionally runs `uv pip install pip` (see [.github/workflows/e2e-tests.yml line 37](../../../.github/workflows/e2e-tests.yml)). Add this if you plan to run `make e2e-tests` locally.

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

## CI-to-local mapping

Canonical mapping of CI check name -> local invocation. The skill always prefers the Make target.

| CI check                     | Workflow file                                                          | Local command                                              | Notes                                                                                                              |
| ---------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `lint`                       | [lint.yml](../../../.github/workflows/lint.yml)                        | `make lint`                                                | Runs `pre-commit run -a --hook-stage manual` (ruff, ruff-format, file hygiene, `lint-imports`, `detect-secrets` on changed files) + `mypy kedro --strict --allow-any-generics --no-warn-unused-ignores`. Fires on both code and docs PRs. |
| `unit-tests`                 | [unit-tests.yml](../../../.github/workflows/unit-tests.yml)            | `make test`                                                | `pytest --numprocesses 4 --dist loadfile`. Coverage `fail_under = 100` enforced via `pyproject.toml`.              |
| `e2e-tests`                  | [e2e-tests.yml](../../../.github/workflows/e2e-tests.yml)              | `make e2e-tests`                                           | `behave --tags=-skip`. Slow (~10+ min on one config). Opt-in locally via `run_local_checks.sh --with-e2e`.         |
| `detect-secrets`             | [detect-secrets.yml](../../../.github/workflows/detect-secrets.yml)    | `git ls-files -z \| xargs -0 detect-secrets-hook --baseline .secrets.baseline` | **No Make target.** Full-tree scan. Differs from the pre-commit hook in `make lint` (which only checks changed files) and can fail in CI even when `make lint` is green. |
| `docs-linkcheck`             | [docs-linkcheck.yml](../../../.github/workflows/docs-linkcheck.yml)    | `make linkcheck`                                           | `mkdocs build --strict` + `lychee --max-concurrency 32 --exclude "@.lycheeignore" site/`. Slow + needs network. Requires `lychee`. |
| `docs-language-linter`       | [docs-language-linter.yml](../../../.github/workflows/docs-language-linter.yml) | `make language-lint dir=docs`                              | `vale docs`. **Non-blocking** — `merge-gatekeeper` ignores `runner / vale` (see [merge-gatekeeper.yml line 27](../../../.github/workflows/merge-gatekeeper.yml)). Requires `vale`. |
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

This installs `.git/hooks/commit-msg` to append `Signed-off-by:` automatically (see [Makefile lines 70-74](../../../Makefile)). One-time setup per clone.

---

## Common CI failures and fixes

Short cookbook keyed by CI check.

### `lint` — ruff lint failure

`ruff check --fix` (or rerun `make lint` — the pre-commit hook auto-fixes when invoked via `--hook-stage manual`).

### `lint` — ruff format failure

`ruff format` (or rerun `make lint`).

### `lint` — `lint-imports` (Import Linter) failure

Read the violated contract from [pyproject.toml lines 166-226](../../../pyproject.toml). The contracts are:

1. **Layered**: `framework.cli > framework.session > framework.context > framework.project > runner > io > pipeline > config`. Higher layers may import lower layers, never the reverse.
2. **Independence**: `kedro.pipeline` and `kedro.io` cannot import each other.
3. **Forbidden**: `kedro.config` cannot import `kedro.runner`/`io`/`pipeline` (and vice versa, with explicit exceptions for `framework.context.context` and `framework.session.session`).

Fix the import. Only if the architectural change is intentional (rare), propose adjusting `ignore_imports` in the relevant contract — but stop and ask the user first.

### `lint` — mypy failure

Add type annotations or stubs. `make lint` re-runs `mypy kedro --strict --allow-any-generics --no-warn-unused-ignores` after pre-commit. The repo's mypy config (in [pyproject.toml lines 252-256](../../../pyproject.toml)) has `ignore_missing_imports = true` and `disable_error_code = ["misc", "untyped-decorator"]`.

### `unit-tests` failure

Run `make test` locally. If the failure is real, fix it. If coverage drops below `fail_under = 100` (set in [pyproject.toml line 129](../../../pyproject.toml)), add unit tests for the new lines — coverage is enforced strictly.

### `e2e-tests` failure

Run `make e2e-tests` locally. For faster iteration, `make e2e-tests-fast` runs with `BEHAVE_LOCAL_ENV=TRUE` and no output capture (see [Makefile lines 24-26](../../../Makefile)).

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

# Watch CI (used by watch_ci.sh)
gh pr checks --watch --interval 30                   # poll until all complete
gh run list --branch <branch> --limit 20 --json databaseId,name,conclusion
gh run view <id> --log-failed                        # dump only failed steps

# After a fix
gh pr checks                                         # re-check status
```
