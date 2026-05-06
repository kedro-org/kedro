---
name: kedro-babysit skill
overview: Add a contributor-facing `kedro-babysit` skill that drives Kedro changes toward a mergeable state — locally before push or on an open PR — by resolving clear merge conflicts, fixing CI / test failures, and ensuring DCO sign-off. Conservative "ask before commit/push" posture, isolated Python env handling (venv or conda), and three helper scripts that wrap existing Make targets. **The skill exposes four explicit invocation tracks** (A: Local-only, B: Targeted CI fix, C: Full PR sweep, D: Watch CI) so the agent can skip irrelevant steps and keep iteration fast — rather than running the full sweep every time. RELEASE.md compliance is intentionally OUT OF SCOPE — it is a reviewer convention (not a CI check) and is handled by the sibling `review-kedro-pr` skill, which flags missing entries as Critical.
todos:
  - id: skill-md
    content: Write .agents/skills/kedro-babysit/SKILL.md (frontmatter + 5-step workflow with preflight + env-bootstrap + out-of-scope, conservative posture, no comments triage)
    status: completed
  - id: reference-md
    content: Write .agents/skills/kedro-babysit/reference.md (env setup with cross-platform tool hints, CI-to-Make mapping table, DCO recipes, CI failure cookbook, gh cheatsheet)
    status: completed
  - id: bootstrap-env
    content: Write scripts/bootstrap_env.sh (preflight gh check, detect active venv/conda, optionally create venv-or-conda with uv->python -m venv fallback, install kedro[test]+pre-commit hooks, conditional docs deps, cross-platform tool hints)
    status: completed
  - id: run-local-checks
    content: Write scripts/run_local_checks.sh (env-isolation guard then thin wrapper around make lint / make test / detect-secrets-hook + opt-in make e2e-tests / make linkcheck / make language-lint, --code/--docs/--all/--with-e2e/--skip-slow flags, per-check pass/fail summary)
    status: completed
  - id: watch-ci
    content: Write scripts/watch_ci.sh (gh preflight + gh pr checks --watch + dump failed job logs annotated with Make targets)
    status: completed
  - id: add-release-entry
    content: "Write scripts/add_release_entry.sh (insert bullet under the right H2 in # Upcoming Release, print diff, no commit)"
    status: cancelled
  - id: smoke-test
    content: Smoke-test the three scripts locally (bootstrap_env into a throwaway venv, --code subset of run_local_checks, dry watch_ci on an existing PR)
    status: completed
  - id: invocation-tracks
    content: "Add explicit invocation tracks to SKILL.md (A: local-only, B: targeted CI fix, C: full sweep, D: watch CI) so the agent skips irrelevant steps; restructure step 5 into 5a/5b/5c; annotate each step with applicable tracks; add --no-wait flag to watch_ci.sh for Track B's snapshot-mode log fetch."
    status: completed
  - id: fast-lint-iteration
    content: "Add 'Fast lint iteration' section to reference.md with per-hook targeted recipes (pre-commit run <hook> --files X, ruff/mypy direct, lint-imports direct) and update SKILL.md so the agent verifies per-failure with targeted commands (seconds), not `make lint` (3–5 min full sweep) — fixes the 'agent runs all checks one by one' loop the user observed during testing."
    status: completed
isProject: false
---

## Goal

Implement the skill described in [issue #5526](https://github.com/kedro-org/kedro/issues/5526) at `.agents/skills/kedro-babysit/`, mirroring the structure of [.agents/skills/review-kedro-pr/SKILL.md](.agents/skills/review-kedro-pr/SKILL.md) (frontmatter + workflow + reference.md + scripts).

The skill complements `review-kedro-pr` by handling the mechanical CI-surfaced things that skill explicitly defers: lint, tests, e2e, import-linter, detect-secrets, docs link/language checks, DCO, merge conflicts, and the CI loop. `RELEASE.md` compliance is *not* a CI check and stays with `review-kedro-pr` (which flags it as Critical at review time).

## Design decisions (confirmed)

- **Conservative autonomy**: stop and ask before every commit, push, DCO amend (force-push), and merge-conflict resolution. Working-tree-only fixes (e.g. `ruff --fix`) are auto-applied; staging/committing is not.
- **Reuse existing automation, but iterate granularly**: every check has a Make target (e.g. `make lint`, `make test`) and the **final** verification before push runs the full sweep via `scripts/run_local_checks.sh` → `make lint`. **For per-failure iteration, the agent uses targeted commands** — `pre-commit run <hook-id> --files <changed>`, `ruff check --fix <file>`, `mypy <file> --strict ...`, `lint-imports --config pyproject.toml`, `pytest <specific-test>` — because `make lint` runs *every* hook on *every* file plus mypy on the entire `kedro/` package (3–5 min per iteration, vs. seconds for the targeted recipes). Documented in `reference.md` section "Fast lint iteration". The only Make-target-only invocation is `detect-secrets-hook` on all tracked files (no Make target, and CI's full-tree scan differs from the pre-commit hook's changed-files-only scan).
- **No comments triage**: out of scope. The skill focuses on CI / test failures, conflicts, and DCO.
- **No `RELEASE.md` editing**: out of scope — `RELEASE.md` is a reviewer convention, not a CI check (`gh pr checks` does not surface it). The sibling `review-kedro-pr` skill flags missing entries as Critical at review time.
- **Never pollute base/system Python**: every local invocation runs inside an isolated venv or conda env. Detection rules and bootstrap details live in the SKILL.md step 2 spec and the `bootstrap_env.sh` script spec below; `run_local_checks.sh` enforces this with a hard env guard.
- **e2e tests are opt-in locally**: `make e2e-tests` (`behave --tags=-skip`) takes 10+ min on one config. Default `--code` scope runs lint + unit tests + detect-secrets only; e2e is gated behind `--with-e2e`.
- **Full scripts**: ship `bootstrap_env.sh`, `run_local_checks.sh`, `watch_ci.sh`.
- **Cross-tool compatible by location**: per [GitHub Copilot agent skills docs](https://docs.github.com/copilot/how-tos/use-copilot-agents/coding-agent/create-skills), Copilot discovers project skills at `.github/skills/`, `.claude/skills/`, **and `.agents/skills/`** — the same path Cursor reads. So the existing `.agents/skills/review-kedro-pr/` layout is already cross-tool, and we keep `kedro-babysit` at `.agents/skills/kedro-babysit/` for the same reason. No separate `.github/prompts/` or `AGENTS.md` stub is required.

## Cross-tool compatibility constraints

The SKILL.md frontmatter must satisfy both Cursor's parser and Copilot's spec ([reference](https://docs.github.com/copilot/how-tos/use-copilot-agents/coding-agent/create-skills)):

- **`name`** (required, both): lowercase, hyphenated. `kedro-babysit` ✓.
- **`description`** (required, both): 10–1024 characters; should describe **what** the skill does and **when** Copilot/Cursor should use it. Planned description (~200 chars, includes "Use when ...") ✓.
- **`license`** (optional, Copilot only): SPDX identifier or LICENSE reference. Skip — repo's Apache-2.0 license applies by default.
- **YAML folded scalar `>-` syntax** for the `description` field: matches the existing [review-kedro-pr SKILL.md](.agents/skills/review-kedro-pr/SKILL.md), confirmed parseable by both tools.
- **Bundled resources** (`reference.md`, `scripts/`): per the Copilot docs, all files in the skill directory are auto-loaded when the skill activates. Same behaviour Cursor already exhibits.

## Precise CI-to-local mapping

Canonical table the skill operates against. Always prefer the Make target.

- **`lint` ([.github/workflows/lint.yml](.github/workflows/lint.yml))** — `make lint` = `pre-commit run -a --hook-stage manual` (ruff, ruff-format, file hygiene, `lint-imports`, `detect-secrets` on changed files) + `mypy kedro --strict --allow-any-generics --no-warn-unused-ignores`. Fired on both code and docs PRs ([docs-only-checks.yml](.github/workflows/docs-only-checks.yml) reuses [lint.yml](.github/workflows/lint.yml)).
- **`unit-tests` ([.github/workflows/unit-tests.yml](.github/workflows/unit-tests.yml))** — `make test` = `pytest --numprocesses 4 --dist loadfile`, coverage `fail_under = 100` ([pyproject.toml line 129](pyproject.toml)).
- **`e2e-tests` ([.github/workflows/e2e-tests.yml](.github/workflows/e2e-tests.yml))** — `make e2e-tests` = `behave --tags=-skip`. Slow; opt-in.
- **`detect-secrets` ([.github/workflows/detect-secrets.yml](.github/workflows/detect-secrets.yml))** — no Make target. CI runs `git ls-files -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline` (full tree). The pre-commit hook in `make lint` only checks changed files; this can fail in CI even when `make lint` is green. Run the full-tree command explicitly.
- **`docs-linkcheck` ([.github/workflows/docs-linkcheck.yml](.github/workflows/docs-linkcheck.yml))** — `make linkcheck` = `mkdocs build --strict` + `lychee --max-concurrency 32 --exclude "@.lycheeignore" site/`. Slow + needs network. **System tool prereq:** `lychee`.
- **`docs-language-linter` / vale ([.github/workflows/docs-language-linter.yml](.github/workflows/docs-language-linter.yml))** — `make language-lint dir=docs` = `vale docs`. **Non-blocking**: [merge-gatekeeper.yml line 27](.github/workflows/merge-gatekeeper.yml) ignores `runner / vale`. Vale failures are informational. **System tool prereq:** `vale`.
- **`merge-gatekeeper` ([.github/workflows/merge-gatekeeper.yml](.github/workflows/merge-gatekeeper.yml))** — n/a. Aggregator; turns green when other required checks pass.
- **`pipeline-performance-test` ([.github/workflows/pipeline-performance-test.yml](.github/workflows/pipeline-performance-test.yml))** — label-triggered (only fires when a maintainer adds the `performance` label). Runs `kedro run` 10x on the `pipeline-performance-test` repo against both the latest release and the PR branch, printing average wall-clock time. **Not a pass/fail check** — it's a perf comparison. The skill reports timing if present in the snapshot but does not attempt to "fix" it; significant regressions are flagged for the human author.
- **DCO sign-off** (GitHub App `dco`, not a workflow file) — `git log <base>..HEAD --format='%H %(trailers:key=Signed-off-by)'` to detect missing trailers.

All other workflows in [.github/workflows/](.github/workflows/) (`benchmark-performance`, `check-release`, `nightly-build`, `release-starters`, `auto-merge-prs`, `sync`, `label-community-issues`, `no-response`) are scheduled, release-triggered, or issue-only — out of scope for the babysit skill.

## Typical user flow (turn-by-turn)

What the user actually sees when they invoke the skill (e.g. "babysit this PR" or "fix CI"). Happy path; each turn ends with a confirm-or-stop checkpoint.

### Turn 1 — Identify, preflight, env bootstrap

- **Preflight**: `gh` installed + `gh auth status` ok; current working tree status (warn if dirty with unrelated changes); auto-detect PR via `gh pr view --json number,title,baseRefName,headRefName`. Confirm with user.
- **Env probe**: one of:
  - **Already set up**: "Active env: `.venv/` (Python 3.11). Deps: ready. System tools: `vale` ok, `lychee` MISSING (linkcheck will be SKIPped). Proceed?"
  - **Env active, deps missing**: "Active env: `.venv/`. Missing `pytest`, `pre_commit`. Run `make install-test-requirements && make install-pre-commit`?" -> on yes, installs.
  - **No isolated env**: "No venv/conda env active (refusing to use system Python). Create one? (a) venv at `.venv/`, (b) conda env named `kedro-babysit`, (c) I'll activate one myself." -> on (a)/(b), creates and prints activation command, then asks user to activate and re-invoke.

### Turn 2 — Snapshot

Read-only pass: `gh pr view`, `gh pr checks`, DCO trailers, file diff. One-screen summary, e.g.:

```
Status:
  Mergeable: BEHIND (8 commits behind develop)
  CI: 2 failing (lint, unit-tests), 7 passing
  DCO: 2 of 4 commits missing Signed-off-by
Plan: (1) sync with develop, (2) fix lint, (3) fix unit-tests, (4) sign-off missing
      commits, (5) verify locally, (6) commit + push, (7) watch CI.
Proceed?
```

### Turn 3..N — Per-issue fix loop (fixed order)

For each finding, the micro-flow is:

1. Explain the issue + proposed fix; cite file/line and failed CI log snippet.
2. Ask the user to confirm.
3. Apply to the working tree only (no `git add`/`commit`).
4. Re-run the corresponding Make target locally to verify.
5. Move on.

Examples:

- Lint: "lint failure: `ruff format` wants to reformat `kedro/io/foo.py`. Apply?" -> user yes -> apply, `make lint` -> PASS.
- DCO: "Commits `abc123`, `def456` missing Signed-off-by. Fixing requires `git rebase develop --signoff` and a force-push. Proceed?" -> user yes -> rebases, defers actual push to Turn N+2.

### Turn N+1 — Verify locally

`scripts/run_local_checks.sh` with auto-detected scope. Final summary, e.g.:

```
Local check results:
  [PASS] make lint            (CI: lint)
  [PASS] make test            (CI: unit-tests)
  [PASS] detect-secrets-hook  (CI: detect-secrets)
  [SKIP] make linkcheck       (lychee not installed)
  [SKIP] make e2e-tests       (--with-e2e not set)
All required checks pass. Ready to commit + push?
```

### Turn N+2 — Commit + push

Skill proposes a commit message based on the changes (or asks the user). Confirms target branch. `git add` only the touched files, `git commit`, `git push` (or `git push --force-with-lease` for the DCO rebase case, with explicit warning).

### Turn N+3 — Monitor CI

`scripts/watch_ci.sh` polls `gh pr checks --watch` until all complete (~10–40 min). On green: "All CI green. Mergeable: CLEAN. Done." On red: dumps `--log-failed` annotated with Make targets, then **returns to Turn 3** with the new findings.

### Invocation tracks (entry points)

The 5-step workflow above is the **full sweep**. The agent picks one of four tracks based on the user's stated goal, then runs only the steps that track requires. The four tracks split along **two axes**: *what the user wants* (verify locally / fix CI / pre-merge gate / just watch) and *how much time they want to spend* (**fast** = single targeted iteration, **thorough** = full local sweep + blocking CI watch).

| Track | Mode | When the user says... | What runs | Skips |
|---|---|---|---|---|
| **A. Local-only** | **fast** (~2–10 min) | "babysit my local changes", "verify before push", "lint my diff" | Step 2 (env), Step 5a (`run_local_checks.sh`), per-fail fix loop. **No PR required.** | Steps 1, 3, 5b/c (no GitHub fetch, no watch CI) |
| **B. Targeted CI fix** | **fast** (~5–15 min) | "CI is failing", "fix the lint job", "what's failing on CI?", "fix the X check on this PR" | Steps 1, 2, 3 (snapshot), 4 (per-failing-check fix; verify each via the most targeted command — `pre-commit run <hook> --files <changed>`, `mypy <file>`, etc., not `make lint`). Use `bash scripts/watch_ci.sh --no-wait` to fetch logs without blocking on still-running CI. | Step 5a (full sweep — redundant: per-check verify already done in step 4) |
| **C. Full PR sweep** | **thorough** (~30–60+ min) | "do a full sweep", "run everything locally", "is this PR ready to merge?", "thorough check before merge" | All steps 1–5, **including Step 5a** (full local sweep — catches side-effects in files the per-check fixes didn't touch) **and Step 5c blocking `--watch`** (10–40 min). | Nothing. |
| **D. Watch CI** | **passive** (CI duration, 10–40 min) | "watch CI", "did my push pass?" | Step 1 (PR detection), Step 5c (`watch_ci.sh`). On red checks, fall through to Track B. | Steps 2, 3, 4, 5a, 5b |

**Picking the right track** (the agent's decision rules, mirrored in SKILL.md):
- Default to the fast tracks (A or B). Most invocations are iterative.
- Pick C only when the user explicitly signals thoroughness ("do a full sweep", "before merge", "everything"). C is ~5× slower than B.
- If "babysit this PR" is the only signal, treat it as ambiguous between B and C — **default to B** and offer to escalate.
- If intent is unclear, ask once: "Verify local changes, fix failing CI, full pre-merge sweep, or just watch CI?"

Conservative posture (ask before commit / push / force-push / conflict resolution) is preserved in every track. Full SKILL.md spec for this section is in §1 below.

## Files to create

### 1. `.agents/skills/kedro-babysit/SKILL.md`

Frontmatter (broadened to cover Track A's local-only use):

```markdown
---
name: kedro-babysit
description: >-
  Babysit Kedro changes — verify locally before pushing, fix failing CI checks
  (lint, tests, detect-secrets, docs), resolve clear merge conflicts, ensure DCO
  sign-off, or watch CI. Use when the user asks to babysit a PR or local changes,
  fix CI, get this PR green, or watch CI.
---
```

**Section ordering**: frontmatter → 1-paragraph intro → `## How to invoke this skill` (track routing table; see "Invocation tracks" above for the canonical version) → `## Workflow` (the 5 steps) → `## Out of scope`.

Each step header carries an inline `_Tracks: A, C_` annotation so the agent can read the header and decide whether to run the step. Workflow:

1. **Identify the PR + preflight** _(Tracks: B, C, D)_ — `gh auth status` check; warn if working tree is dirty with unrelated changes; auto-detect PR via `gh pr view --json number,title,baseRefName,headRefName`, or accept a PR URL/number from the user. **If no PR exists** for the current branch: stop with "Open a PR first (e.g. `gh pr create`); creating PRs is out of scope for this skill." (Track A skips this preflight entirely — it works on uncommitted/unpushed changes.)
2. **Set up the Python environment** _(Tracks: A, B, C; D only if `make`/`gh` are needed)_ — run `scripts/bootstrap_env.sh`. Detection logic: `$VIRTUAL_ENV` set OR (`$CONDA_PREFIX` set AND `$CONDA_DEFAULT_ENV != "base"`). If neither, ask "venv or conda?" + name; on confirmation, create and instruct activation. If active but deps missing, run `make install-test-requirements` + `make install-pre-commit` (and `make install-docs-requirements` if PR touches docs). Probe `vale`/`lychee`; print install hints if missing.
3. **Snapshot the PR state** _(Tracks: B, C)_ — `gh pr view --json mergeable,mergeStateStatus,headRefOid,files`, `gh pr checks`, `git log <base>..HEAD --format='%H %(trailers:key=Signed-off-by)'`. One-screen summary annotated with Make targets per failing check.
4. **Fix in this fixed order** _(Tracks: A, B, C — sub-steps gate on track too)_ — each sub-step ends with "stop and ask before staging / committing / pushing / amending":
   - **Merge conflicts** _(B, C)_ — if `mergeStateStatus` is `DIRTY` or `BEHIND`, sync with base. Resolve only when intent is unambiguous; otherwise stop and ask.
   - **CI failures** _(B, C)_ — for each failing check: look up the local invocation in [reference.md](reference.md); pull failed-job logs via `bash scripts/watch_ci.sh --no-wait` (snapshot mode — does not block on still-running checks); propose smallest scoped fix; apply to working tree; **verify via the specific Make target only** (`make lint`, `make test`, etc. — *not* the full `run_local_checks.sh` sweep, which would be slow and redundant).
   - **Local-only failures** _(A)_ — same micro-flow, but the trigger is the per-check FAIL output from `run_local_checks.sh` in step 5a, not a CI log. Verify by re-running the same single Make target.
   - **DCO sign-off** _(B, C)_ — list commits without `Signed-off-by:`; ask before amending; warn that amend requires force-push.
5. **Verify locally → commit + push → watch CI** — restructured into three sub-steps so each track can run only what it needs:
   - **5a. Verify locally (full sweep)** _(Tracks: A, C)_ — `scripts/run_local_checks.sh` with auto-detected scope. On Track A this is the entry point; FAILs feed back into step 4's local-fix loop, then re-run 5a until all PASS or SKIP. **Track B skips 5a** (per-check verify already done in step 4).
   - **5b. Commit + push** _(Tracks: A optional, B, C)_ — `git add` only touched files; `git commit -s` (with sign-off); `git push` or `git push --force-with-lease` for DCO rebase. Track A may skip if the user just wants a clean working tree.
   - **5c. Watch CI** _(Tracks: B optional, C, D)_ — `scripts/watch_ci.sh` (or `--no-wait` for one-shot snapshot). On red, **loop back to step 4**; only re-snapshot (step 3) if base branch moved further.

Out of scope:

- **Comments triage** (PR review comments, reviewer asks, and bot-generated review feedback such as Bugbot, the Cursor-style review bot that posts inline comments) — author handles reviewer feedback directly. The skill does not read, summarise, or act on review comments even when CI is otherwise green.
- **Judgment-based code review** — defers to `review-kedro-pr`.
- **`RELEASE.md` compliance** — `RELEASE.md` is a reviewer convention, not a CI check (`gh pr checks` does not surface it). Defers to `review-kedro-pr`, which flags missing entries as Critical.
- **Security review** — defers to future `kedro-security-review`.
- **Authoring features / large refactors** — out of scope.
- **Performance regressions** (`pipeline-performance-test` on PRs with the `performance` label) — the skill reports the timing comparison but does not attempt to fix perf regressions; that's a human-judgement task.
- **Installing system tools** (`vale`, `lychee`, `gh`) — skill prints install hints but never invokes `brew`/`apt`/`cargo`.

Cross-references: each step of SKILL.md must use **inline section-specific links** to `reference.md`, matching the [review-kedro-pr SKILL.md line 160 pattern](.agents/skills/review-kedro-pr/SKILL.md) (`read [reference.md](reference.md) section "<Section name>"`). Concretely:
- Step 2 -> `reference.md` section "Environment setup"
- Step 3 / Step 4 (CI failures) -> `reference.md` section "CI-to-local mapping" + "Common CI failures and fixes"
- Step 4 (DCO) -> `reference.md` section "DCO sign-off recipes"
- Anywhere `gh` is used -> `reference.md` section "gh CLI cheatsheet"

### 2. `.agents/skills/kedro-babysit/reference.md`

Sectioned reference (read selectively, same convention as [review-kedro-pr/reference.md](.agents/skills/review-kedro-pr/reference.md)):

- **Environment setup** — detection rules; manual venv recipe (`uv venv .venv && source .venv/bin/activate`, fallback `python -m venv .venv`); manual conda recipe (`conda create -n kedro-babysit python=3.11 && conda activate kedro-babysit`); install steps (`make install-test-requirements`, `make install-pre-commit`, optional `make install-docs-requirements`); note that e2e workflow also runs `uv pip install pip` per [e2e-tests.yml line 37](.github/workflows/e2e-tests.yml); cross-platform system-tool install hints — macOS: `brew install vale lychee gh`; Linux (Debian/Ubuntu): `sudo apt install vale && cargo install lychee && sudo apt install gh` (or follow each tool's docs); Windows: link to vale/lychee/gh release pages.
- **CI-to-local mapping** — same content as the "Precise CI-to-local mapping" section above, rendered as a markdown table for quick lookup. The `lint` row explicitly cross-links to "Fast lint iteration" with the timing note (3–5 min full sweep vs. seconds for targeted).
- **Fast lint iteration** — per-hook targeting strategy + recipe table for iteration (vs. `make lint` for final verify). Hooks covered: `ruff` (direct: `ruff check --fix <file>`), `ruff-format` (direct: `ruff format <file>`), file hygiene hooks (`pre-commit run <hook-id> --files <file>`), `imports` / Import Linter (direct: `lint-imports --config pyproject.toml` — `pass_filenames: false` means it always scans the whole project regardless), `detect-secrets` pre-commit hook (changed-files only), `mypy` (direct: `mypy <file> --strict --allow-any-generics --no-warn-unused-ignores`). Includes the `make lint hook=<id>` convenience target ([Makefile line 11](Makefile)) and explicit "when to fall back to `make lint`" guidance.
- **DCO sign-off recipes** — `git commit --signoff` for new commits; `git commit --amend --no-edit --signoff` for the last commit (force-push required); `git rebase <base> --signoff` to add sign-off to all commits since base (force-push required); `make sign-off` from [Makefile lines 70-74](Makefile) to install a local hook that auto-signs.
- **Common CI failures and fixes** — short cookbook keyed by CI check:
  - `lint` ruff lint failure -> `ruff check --fix` (or rerun `make lint`, the pre-commit hook auto-fixes).
  - `lint` ruff format failure -> `ruff format` (or rerun `make lint`).
  - `lint` `lint-imports` failure -> read the violated contract from [pyproject.toml lines 166-226](pyproject.toml); fix the import or, only if the architectural change is intentional, propose adjusting `ignore_imports`.
  - `lint` mypy failure -> add type annotations or stubs; `make lint` re-runs mypy after pre-commit.
  - `unit-tests` failure -> `make test`; if coverage drops (`fail_under = 100`), add unit tests for the new lines.
  - `e2e-tests` failure -> `make e2e-tests`; consider `make e2e-tests-fast` for local iteration.
  - `detect-secrets` failure -> rerun the full-tree scan locally; if it's a real secret, remove it; if it's a false positive, regenerate the baseline with `detect-secrets scan --baseline .secrets.baseline`.
  - `docs-linkcheck` failure -> `make linkcheck`; fix broken links in `docs/` or add to `.lycheeignore`.
  - `docs-language-linter` (vale) failure -> informational only (merge-gatekeeper ignores it). `make language-lint dir=docs` to reproduce.
  - `pipeline-performance-test` regression -> not auto-fixed; the skill reports the timing delta and asks the user to investigate manually. Only fires when a maintainer adds the `performance` label.
  - `merge-gatekeeper` red -> nothing to fix directly; turns green when all required checks pass.
- **gh CLI cheatsheet** — `gh auth status`, `gh pr view --json mergeable,mergeStateStatus,headRefOid`, `gh pr checks`, `gh run list --branch <branch> --limit 5`, `gh run view <id> --log-failed`.

### 3. `.agents/skills/kedro-babysit/scripts/bootstrap_env.sh`

`#!/usr/bin/env bash` with `set -euo pipefail`.

- **Preflight**: verify `gh` installed and `gh auth status` ok (warn but don't fail — it's only needed by `watch_ci.sh`).
- **Detect**: print active env summary using `$VIRTUAL_ENV`, `$CONDA_PREFIX`, `$CONDA_DEFAULT_ENV`, `which python`, `python -c "import sys; print(sys.prefix)"`.
- **Refuse on system Python**: if no `$VIRTUAL_ENV` and no `$CONDA_PREFIX` (or `$CONDA_DEFAULT_ENV == "base"`), call the create flow.
- **Create flow** (only when no isolated env active):
  - Args: `--type {venv|conda}` (required), `--name <name>` (default `.venv` for venv, `kedro-babysit` for conda), `--python <version>` (optional). Python version resolution order: (1) `--python` if explicit; (2) the current `python --version` on PATH if it's in Kedro's supported range 3.10-3.14 (from [pyproject.toml `requires-python`](pyproject.toml)); (3) fallback to `3.11` (the version the lint job uses on CI).
  - Install flow additionally prints a soft warning if the active env's Python is outside 3.10-3.14 (does not refuse — user already chose).
  - For venv: prefer `uv venv "$NAME" --python "$PYTHON"`; fall back to `python -m venv "$NAME"` if `uv` not on PATH. Print `source $NAME/bin/activate`.
  - For conda: `conda create -y -n "$NAME" python="$PYTHON"`. Print `conda activate $NAME`.
  - Exit 0 with instruction to activate and re-run (cannot source from child shell).
- **Install flow** (only when env IS active):
  - Args: `--with-docs` (optional).
  - Verify deps: `python -c "import pytest, pre_commit" 2>/dev/null` -> if missing, `make install-test-requirements && make install-pre-commit`.
  - If `--with-docs`: `python -c "import mkdocs" 2>/dev/null` -> if missing, `make install-docs-requirements`.
  - Probe system tools: `command -v vale`, `command -v lychee`, `command -v gh`. Print platform-specific install hints (detect via `uname`); do not exit non-zero on missing tools.
- Print final summary: env path, Python version, deps + system tools status.

### 4. `.agents/skills/kedro-babysit/scripts/run_local_checks.sh`

Thin orchestrator around Make targets. `#!/usr/bin/env bash` with `set -uo pipefail` (not `-e` — every check must run even if an earlier one fails).

- **Env guard (first action)**: refuse to run unless `$VIRTUAL_ENV` is set OR (`$CONDA_PREFIX` is set AND `$CONDA_DEFAULT_ENV != "base"`). On refusal: print "Run `scripts/bootstrap_env.sh` first" and exit **64** (sysexits `EX_USAGE`).
- **Flags**:
  - `--code` (default if only `kedro/`, `tests/`, or `features/` changed): runs `make lint`, `make test`, plus the full-tree `detect-secrets-hook` scan. Does **not** run `make e2e-tests` by default.
  - `--docs` (default if only `docs/` or `**.md` changed): runs `make lint`, `make linkcheck`, `make language-lint dir=docs`.
  - `--all`: code + docs + e2e.
  - `--with-e2e`: explicitly include `make e2e-tests` (otherwise SKIPped).
  - `--skip-slow`: omits `make test`, `make e2e-tests`, `make linkcheck` (fast iteration; runs `make lint` + detect-secrets only).
  - `--base <branch>`: explicit base ref for the auto-detect diff (default: `gh pr view --json baseRefName` if `gh` is available, else `origin/main`).
- Auto-detect scope from `git diff --name-only $BASE...HEAD` if no flag is given. Three cases: code only -> `code`; docs only -> `docs`; mixed -> `code+docs` (lint + test + detect-secrets + linkcheck + language-lint, no e2e). The mixed case mirrors CI behaviour: [all-checks.yml](.github/workflows/all-checks.yml) uses `paths-ignore: ["docs/**", "**.md"]` so it triggers on any non-docs change, while [docs-only-checks.yml](.github/workflows/docs-only-checks.yml) uses `paths: ["docs/**", "**.md"]` so it triggers on any docs change — both fire on mixed PRs.
- Skip docs commands with `[SKIP missing tool]` if `vale`/`lychee` not installed.
- Capture per-check pass/fail. Prefix each section with `>>> [check name] (CI equivalent: <workflow>)` so the output cross-references CI.
- Final summary table: `[PASS] make lint`, `[FAIL] make test`, `[SKIP] make e2e-tests`, etc.
- Exit code = number of failed (non-skipped) checks, capped at 63 (the env-guard reserves 64).

### 5. `.agents/skills/kedro-babysit/scripts/watch_ci.sh`

- **Args**: `--pr <number-or-url>` (default: detect from current branch), `--interval <s>` (default 30), `--tail <n>` (default 200, log lines per failed run), `--no-wait` (snapshot mode: skip the blocking `gh pr checks --watch` and go straight to fetching the current state + dumping logs for any already-failed checks; used by Track B when CI is still running but the user wants to see what's failed *now*).
- **Preflight**: `gh` installed AND `gh auth status` ok (exit 64 if either missing).
- Resolve PR via `gh pr view --json number,headRefName,baseRefName,url`. Exit 64 if no PR found.
- Default mode: run `gh pr checks <pr> --watch --interval <s>` until all checks complete (block, but do not propagate its exit yet — we want to dump logs first). With `--no-wait`: skip this call entirely; the final-state fetch reflects whatever's there now (pending + pass + fail + skipping + cancel buckets are all reported).
- Fetch final structured state via `gh pr checks <pr> --json name,bucket,workflow,link` and tally by `bucket` (`pass | fail | pending | skipping | cancel`). The `bucket` field is the official categorisation from the gh CLI — more reliable than parsing `state` strings.
- For each `bucket == "fail"` check: extract the run ID directly from `.link` (format `https://github.com/.../actions/runs/<run_id>/job/<job_id>`) — cleaner than a separate `gh run list` lookup. Dedupe per run ID (a single workflow run can produce many failed checks). Dump `gh run view <id> --log-failed | tail -n <tail>` so the skill has compact failure logs without flooding context. Gracefully handle the no-logs case (vale, DCO, etc. fail outside a step and have no per-step logs).
- Annotate each failed check with its corresponding Make target from the [CI-to-local mapping](.agents/skills/kedro-babysit/reference.md). Mapping covers `lint`, `unit-tests`, `e2e-tests`, `detect-secrets`, `docs-linkcheck`, `docs-language-linter` (vale), `merge-gatekeeper` (n/a), `pipeline-performance-test` (n/a), `DCO` (rebase --signoff recipe), plus a fallback "(no local mapping — see reference.md)" for unknown checks.
- Use `gh -q` (gh CLI's bundled jq) — no external `jq` dependency required.
- Bash 3.2 compatible (macOS default): no `declare -A` (use a space-padded string for dedup).
- Exit code = number of failed checks (capped at 63 — preflight reserves 64).

## Files NOT changed

- [.agents/skills/review-kedro-pr/SKILL.md "Out of scope" section (lines 166-179)](.agents/skills/review-kedro-pr/SKILL.md) already references `kedro-babysit` by name with the right scope. No change needed.

## Verification (after implementation)

- `bash scripts/bootstrap_env.sh --type venv --name /tmp/kedro-babysit-test` creates a fresh venv (via `uv venv` or `python -m venv` fallback) and prints the activation command without polluting any existing env.
- After activating the test venv and re-running `bash scripts/bootstrap_env.sh`, deps install via `make install-test-requirements` + `make install-pre-commit`; final summary shows everything ready, with cross-platform tool hints if `vale`/`lychee` are missing.
- `bash scripts/run_local_checks.sh` from outside any venv exits 64 with the "run bootstrap_env.sh first" message.
- `bash scripts/run_local_checks.sh --skip-slow` from inside the test venv runs `make lint` + detect-secrets and returns 0 on a clean tree.
- `bash scripts/watch_ci.sh` works against a real open PR (default blocking mode).
- `bash scripts/watch_ci.sh --no-wait` against the same PR returns within seconds in snapshot mode (banner: `Mode   : snapshot (--no-wait)`); reports current state with pending checks counted, not blocked on.
- The skill is discoverable in **Cursor**: appears in the `available_skills` list with the correct description on next session start.
- The skill is discoverable in **Copilot**: per the [Copilot agent skills docs](https://docs.github.com/copilot/how-tos/use-copilot-agents/coding-agent/create-skills), `.agents/skills/` is one of the supported project-skill locations, so Copilot loads `SKILL.md` automatically. Manual smoke test: open the repo in VS Code with Copilot Chat and confirm the skill is listed (no separate Copilot stub file required).

## Manual testing scenarios (end-to-end)

After the script-level smoke tests above pass, run these end-to-end scenarios in a real chat session (in both Cursor and Copilot, ideally) to validate the skill's user-facing behaviour. Each scenario's title is tagged with the track(s) it primarily exercises.

### Scenario 0 — Track routing from user phrasing (meta-test, all tracks)

This validates that the agent picks the right track from the user's words *before* invoking any script. Run each prompt in a fresh session (no prior turn-state) and check the agent's first action.

| User prompt                                                | Expected track | Expected first action                                                                                  |
|------------------------------------------------------------|----------------|--------------------------------------------------------------------------------------------------------|
| "babysit my local changes"                                 | **A**          | Skip Step 1 (no PR fetch). Go to Step 2 (env probe).                                                   |
| "verify before push" / "lint my diff" / "run checks locally" | **A**          | Same as above.                                                                                         |
| "CI is failing" / "fix the lint job" / "what's failing on CI?" | **B**       | Step 1 (PR detect) → Step 2 (env). No mention of full local sweep.                                     |
| "do a full sweep" / "is this PR ready to merge?" / "thorough check before merge" | **C** | Step 1 → Step 2; explicitly says it will run all 5 steps including 5a + blocking 5c.            |
| "watch CI" / "did my push pass?" / "monitor this PR"       | **D**          | Step 1 → Step 5c (`watch_ci.sh`). No env bootstrap, no fix loop.                                       |
| "babysit this PR" *(alone, ambiguous)*                     | **B (default)** | Picks B and **explicitly offers to escalate**: "I'll do a targeted CI fix (~5–15 min). If you want the full pre-merge sweep instead (~30–60 min), say so." |
| "help me with this PR" *(unclear intent)*                  | **ASK once**   | Asks the disambiguation question: "Verify local changes (fast, no PR), fix failing CI (fast, targeted), full pre-merge sweep (thorough, slow), or just watch CI?" |

- **Pass criteria**: agent picks the expected track in every clear case; for "babysit this PR" alone, defaults to B AND mentions the escalation path; for unclear phrases, asks before doing anything. Crucially, **Track C is never picked silently** — only when the user explicitly signals thoroughness or accepts the escalation offer.

### Scenario 1 — Env bootstrap (cold start, Track B default)

- **Setup**: open the repo in a new shell with no venv/conda env active (`unset VIRTUAL_ENV CONDA_PREFIX CONDA_DEFAULT_ENV`). Be on a branch with an open PR.
- **Trigger**: "babysit this PR".
- **Expected**: skill detects PR, then refuses to use system Python and asks "venv or conda?". Choose venv. Skill calls `bootstrap_env.sh --type venv --name .venv-babysit` (explicit `--name` to avoid colliding with any pre-existing `.venv/` in the repo), prints the activation command, and stops with "activate and re-invoke me".
- **Pass criteria**:
  - `.venv-babysit/bin/python` exists.
  - System Python is unchanged: in a fresh shell after the script exits, `which python` and `python -c "import sys; print(sys.prefix)"` still point to the original system / pyenv interpreter (not `.venv-babysit`).
  - No packages were installed system-wide: `python -c "import pytest" 2>&1` still fails outside the venv (assuming it wasn't already installed).
  - Skill did not proceed to the fix loop.

### Scenario 2 — Happy path on a clean PR (Track B vs Track C)

Two variants — both should pass, but differ in what the skill runs locally.

**2a. Default ambiguous → Track B (fast)**
- **Setup**: open a PR with no failing CI and no DCO issues, mergeable. Activate the test venv from Scenario 1; install deps once.
- **Trigger**: "babysit this PR".
- **Expected**: Step 1 (preflight + env ok), Step 3 (snapshot shows all green, no DCO issues, no merge conflict). Skill says: "All CI green, no DCO issues, mergeable. **I'll do a targeted CI fix by default** — but there's nothing to fix here. If you want the full pre-merge sweep with local belt-and-suspenders verification (~30–60 min) instead, say so. Otherwise, you're done."
- **Pass criteria**: skill **does NOT run Step 5a** (`run_local_checks.sh`). No commits, no force-pushes. Exits within ~30s after Step 3.

**2b. Explicit thoroughness → Track C (full sweep)**
- **Setup**: same as 2a.
- **Trigger**: "do a full pre-merge sweep on this PR".
- **Expected**: Step 1 → Step 2 → Step 3 (green) → **Step 5a runs `bash scripts/run_local_checks.sh`** with auto-detected scope; passes. Step 5b prompts (no changes, so nothing to commit). Step 5c (optional here since CI is already green) — agent may skip or ask.
- **Pass criteria**: `run_local_checks.sh` was invoked; per-check summary shown to user; no commits without explicit confirmation.

### Scenario 3 — Lint failure fix loop (Track B, targeted commands)

This is **the** scenario for validating the fast-iteration model. The agent must verify per-check fixes with targeted commands (seconds), never with `make lint` (3–5 min).

- **Setup**: introduce a deliberate lint error in a single `kedro/` file (e.g. add an unused import to `kedro/io/foo.py`) and push. Wait for `lint` CI to fail.
- **Trigger**: "babysit this PR — CI is failing" *(unambiguous Track B trigger)*.
- **Expected**:
  - **Step 1+2**: preflight + env ok.
  - **Step 3 snapshot**: lists `lint` as failing, annotated with the local Make target.
  - **Step 4 (CI failures sub-bullet)**: agent runs `bash scripts/watch_ci.sh --no-wait` (snapshot mode, NOT blocking) to fetch the failed-step log. Identifies the failing hook (`ruff` or `ruff-format`). Proposes the targeted fix: `pre-commit run ruff --files kedro/io/foo.py` *or* `ruff check --fix kedro/io/foo.py` — **explicitly NOT `make lint`** — and asks for confirmation. On user "yes": applies fix to working tree (no `git add`/`commit`); re-runs the **same targeted command** to verify (sub-second).
  - **Step 5a SKIPPED** — Track B does not run the full sweep.
  - **Step 5b**: asks before staging + committing + pushing.
  - **Step 5c**: agent may use blocking `watch_ci.sh` or `--no-wait` per user preference.
- **Pass criteria**:
  - Agent **never invokes `make lint`** during the fix loop. Confirm by checking the chat transcript for the literal string `make lint` — should not appear in any tool call (only in narration referring to it as the slow alternative).
  - Agent **uses `watch_ci.sh --no-wait`** for the initial log fetch (snapshot mode), not the blocking default.
  - Per-iteration time is **seconds**, not minutes (verify by timing or by looking at the agent's tool-call durations).
  - Skill stops and asks before commit + push.
  - Final CI is green; only the lint-fix commit was made (no unrelated changes).

### Scenario 4 — Missing DCO sign-off (force-push gate, Track B)

- **Setup**: branch with at least one commit missing `Signed-off-by:` (use `git commit --no-edit -m "test"` without `--signoff`). Push.
- **Trigger**: "babysit this PR".
- **Expected**: snapshot lists the commits missing sign-off. Fix loop proposes `git rebase <base> --signoff` and **explicitly warns** that a force-push (`--force-with-lease`) is required. Asks for confirmation BEFORE rebasing AND BEFORE pushing.
- **Pass criteria**: skill never force-pushes without an explicit user "yes"; after user confirms both gates, all commits have `Signed-off-by:` trailers (`git log --format='%(trailers)'`); DCO check passes on next CI run.

### Scenario 5 — Merge conflict (conservative gating, Track B or C)

- **Setup**: branch behind `develop` with a real conflict (e.g. both branches modify the same line in `kedro/io/core.py`).
- **Trigger**: "babysit this PR".
- **Expected**: snapshot shows `mergeStateStatus: DIRTY`. Fix loop offers to sync with `develop`. For each conflict: skill stops and asks the user to resolve (does NOT pick a side automatically because intent is ambiguous). After user resolves, skill continues.
- **Pass criteria**: no auto-resolution occurred; the user manually resolved the conflict; skill correctly proceeds to the next step after resolution.

### Scenario 6 — Missing system tools (skip not fail, Track A)

- **Setup**: uninstall `lychee` (or rename it temporarily). Branch with a docs-only change. PR may or may not exist (Track A doesn't require one).
- **Trigger**: "verify my local docs changes" *(unambiguous Track A trigger)*.
- **Expected**: Step 2 (env) → Step 5a runs `bash scripts/run_local_checks.sh` (auto-detects `docs` scope). Output shows `[SKIP] make linkcheck  (missing tool: lychee)` (exact wording from the script). Other docs checks (`make lint`, `make language-lint`) still run. The skill itself narrates the install hint by referring the user to [reference.md](.agents/skills/kedro-babysit/reference.md) "Environment setup" — or offers to re-run `bootstrap_env.sh`, which probes for missing tools and prints platform-specific hints (`brew install lychee` on macOS, `cargo install lychee` on Linux, link to release page on Windows).
- **Pass criteria**: exit code is 0 (skips don't count as failures); the `[SKIP]` line uses the script's actual format; the skill surfaces a platform-appropriate install hint (from its own narration of `reference.md` or by re-running `bootstrap_env.sh`) rather than letting the SKIP go unexplained; **no GitHub fetch attempted** (Track A skips Step 1 + Step 3).

### Scenario 6b — Mixed code+docs PR auto-detection (Track A)

- **Setup**: branch with both a code change (e.g. `kedro/io/foo.py`) and a docs change (e.g. `docs/source/bar.md`). Test venv active.
- **Trigger**: "just verify locally" (no scope flag).
- **Expected**: `run_local_checks.sh` (no flag) prints `Auto-detected scope: code+docs` and runs `make lint` + `make test` + detect-secrets + `make linkcheck` + `make language-lint`, with `make e2e-tests` SKIPped (opt-in only). Mirrors CI behaviour: both [all-checks.yml](.github/workflows/all-checks.yml) and [docs-only-checks.yml](.github/workflows/docs-only-checks.yml) fire on mixed PRs.
- **Pass criteria**: scope line shows `code+docs`; all five non-e2e checks attempted; e2e SKIPped with the "opt-in only" reason.

### Scenario 7 — No PR for current branch (graceful early exit + Track A escape hatch, Track B → A)

- **Setup**: a local branch with commits but no open PR (`gh pr view` exits non-zero).
- **Trigger**: "babysit this PR" *(implies a PR exists — but doesn't)*.
- **Expected**: skill detects (Step 1) that no PR exists. Instead of silently exiting, it offers the **Track A escape hatch**: "No PR found for this branch. Want to (a) verify your local changes anyway (Track A — no PR needed, ~2–10 min), or (b) open a PR first (`gh pr create`) and re-invoke me?" If user picks (a) → fall through to Track A flow (Step 2 + 5a). If (b) → exit.
- **Pass criteria**: skill **does not silently exit** — it surfaces the Track A option. No env created until the user confirms; no commits or pushes. Track A path, if chosen, runs Step 2 + 5a correctly without any GitHub fetch.

### Scenario 9 — `watch_ci.sh --no-wait` snapshot mode (Track B / D)

Validates the snapshot-mode flag end-to-end so Track B can fetch failed logs without blocking on still-running checks.

- **Setup**: open PR with at least one already-failed check AND at least one still-pending check (e.g. lint failed in 30s, but unit-tests still running). Easiest reproduction: push a commit with a lint error during peak CI hours.
- **Trigger**: "fix the lint job — what's failing?" *(unambiguous Track B trigger)*.
- **Expected**: in Step 4, agent runs `bash scripts/watch_ci.sh --no-wait` (NOT the default blocking mode). Output starts with `Mode   : snapshot (--no-wait)` and `Snapshot mode: skipping --watch; reading current CI state.` (verbatim from the script). Returns within seconds with the current tally (e.g. `pass=2 fail=1 pending=5`) and dumps `--log-failed` for the lint failure. Agent does NOT wait for the pending checks to complete before proposing a fix.
- **Pass criteria**:
  - Total wall-clock time of the `watch_ci.sh` call is **under 10s** (vs. minutes for blocking mode with pending checks).
  - The snapshot-mode banner lines appear in output.
  - Pending checks are reported as `pending=N`, not blocking.
  - Agent proceeds to propose a targeted fix immediately, without waiting for unit-tests to finish.

### Scenario 8 (optional) — Cross-tool parity (Cursor vs Copilot)

Skip this scenario if you don't have Copilot Chat available — the mandatory cross-tool check is already covered by the Verification section above (skill appears in Cursor's `available_skills` on session start; loading from `.agents/skills/` is documented as supported by both tools).

- **Setup**: same repo, same branch, same PR. Both Cursor and VS Code with Copilot Chat installed.
- **Trigger**: in Cursor: "babysit this PR". In VS Code with Copilot Chat: same prompt (or `/kedro-babysit` if Copilot uses slash invocation).
- **Expected**: both tools discover and load the skill from `.agents/skills/kedro-babysit/SKILL.md`; both produce structurally similar fix proposals (exact wording may differ); both call the same `scripts/*.sh` and `make` targets.
- **Pass criteria**: skill is listed in both tools' available-skills surface; both can read `reference.md` when needed; both can execute the three scripts.
