---
name: kedro-babysit
description: >-
  Babysit Kedro changes — verify locally before pushing, or diagnose and fix
  failing CI checks (lint, tests, detect-secrets, docs) on an open PR. Resolves
  clear merge conflicts and ensures DCO sign-off. Use when the user asks to
  babysit local changes, fix CI, or get this PR green.
---
# Babysit Kedro PR

Drive Kedro changes toward a mergeable state — locally before push, or on an open PR with failing CI. Fix mechanical CI failures, resolve clear merge conflicts, ensure DCO sign-off. Use a conservative posture: stop and ask the user before every commit, push, force-push, and merge-conflict resolution.

This skill complements `review-kedro-pr` (judgment-based code review). It does **not** triage PR review comments.

## How to invoke this skill

**Pick a track first**, then run only the steps that track requires. There are two tracks, mapped to the two real situations users hit:

| Track | When the user says... | What to do |
|---|---|---|
| **L. Local dev** | "babysit my local changes", "verify before push", "run checks locally", "are my changes ready?", "lint my diff" | Step 2 (env) → Step 5a (full sweep to surface FAILs) → Step 4 (per-failure fix loop with targeted commands) → Step 5a (final re-verify) → optional Step 5b (commit + push). **No PR required.** Skips GitHub fetch entirely. |
| **C. CI diagnosis & fix** | "CI is failing", "fix the lint job", "what's failing on CI?", "fix the X check on this PR", "babysit this PR" | Step 1 (PR detection) → Step 2 (env) → Step 3 (snapshot via `scripts/watch_ci.sh`) → Step 4 (fix only the failing checks; verify each with the most targeted command — see [reference.md](reference.md) section "Fast lint iteration") → Step 5b (commit + push). **Skip Step 5a** — per-check verify already happened in Step 4. |

### Picking the right track

- **Track L** = user is iterating on uncommitted/unpushed changes and wants to know if they pass before pushing. No PR involvement.
- **Track C** = a PR exists and CI is red (or the user wants to diagnose what CI thinks). Always starts by snapshotting CI state via `scripts/watch_ci.sh`.
- **If "babysit this PR" is the only signal**, default to Track C (a PR is implied).
- **If intent is unclear**, ask once: *"Verify your local changes before pushing (no PR), or diagnose and fix failing CI on an open PR?"* Pick a track **before** invoking any script.
- **For very narrow Track L asks** ("just lint my diff", "just run ruff on my changes"), skip Step 5a and run the targeted command from Step 4 directly — there's no need for a full-sweep discovery pass.

Each step header below is annotated with the tracks that need it (e.g. `Tracks: L, C`). Skip a step if your track is not listed.

## Workflow

### 1. Identify the PR + preflight   _Track: C_

Detect the PR from the current branch, or accept a PR URL/number from the user:

```bash
gh auth status
gh pr view --json number,title,baseRefName,headRefName
```

Preflight checks:
- `gh` is installed and authenticated. If not, stop and ask the user to install/authenticate.
- The working tree is clean enough to operate on. Run `git status --porcelain`; if there are uncommitted changes unrelated to the planned fixes, warn the user and ask whether to stash or proceed.
- A PR exists for the current branch. **If no PR exists**, ask the user whether to switch to Track L (local-only) or stop and open a PR first (`gh pr create`); creating PRs is out of scope for this skill.

### 2. Set up the Python environment   _Tracks: L, C_

Run `scripts/bootstrap_env.sh`. The script:

- Detects an active isolated env: `$VIRTUAL_ENV` set, OR (`$CONDA_PREFIX` set AND `$CONDA_DEFAULT_ENV != "base"`).
- If no isolated env active: ask the user "venv or conda?" + name. Pass to `bootstrap_env.sh --type {venv|conda} --name <name>`. The script creates the env and prints the activation command. **The skill cannot activate the env from a child shell** — instruct the user to activate and re-invoke the skill.
- If active but dependencies missing: the script runs `make install-test-requirements` + `make install-pre-commit` (and `make install-docs-requirements` if the PR touches `docs/` or `**.md`).
- Probes for system tools `vale`, `lychee`, `gh`. Prints platform-specific install hints if missing; does not install them.

Read [reference.md](reference.md) section "Environment setup" for manual recipes and cross-platform install hints.

### 3. Snapshot the PR state   _Track: C_

Single read-only pass:

```bash
gh pr view --json mergeable,mergeStateStatus,headRefOid,files
bash scripts/watch_ci.sh                              # snapshot CI + dump failed-job logs
git log <base>..HEAD --format='%H %(trailers:key=Signed-off-by)'
```

Show the user a one-screen summary:
- Mergeable status (`CLEAN` / `BEHIND` / `DIRTY` / `BLOCKED`).
- Failing CI checks, each annotated with the local Make target from [reference.md](reference.md) section "CI-to-local mapping".
- Commits missing DCO `Signed-off-by:` trailer.

`scripts/watch_ci.sh` is snapshot-only: it fetches the current state and exits without blocking on still-running checks. Re-run it later for a refreshed snapshot.

### 4. Fix in this fixed order   _Tracks: L, C — sub-bullets gate per track too_

Each sub-step ends with **stop and ask before staging / committing / pushing / amending**.

**Merge conflicts** (Track C). If `mergeStateStatus` is `DIRTY` or `BEHIND`, sync with the base branch. Resolve conflicts only when the intent is unambiguous; otherwise stop and ask the user.

**CI failures** (Track C). For each failing check:
1. Look up the local invocation in [reference.md](reference.md) section "CI-to-local mapping". **Note:** `e2e-tests` are intentionally not runnable locally through this skill — if e2e is failing, share the CI logs from `watch_ci.sh` and ask the user how to proceed.
2. The failed-job logs were already dumped by `watch_ci.sh` in Step 3. If the run finished after Step 3, re-run `bash scripts/watch_ci.sh` for an updated snapshot.
3. Propose the smallest scoped fix using [reference.md](reference.md) section "Common CI failures and fixes".
4. Apply the fix to the working tree only (no `git add` / `git commit`).
5. **Verify with the most targeted command available** — almost never `make lint`, which runs *every* pre-commit hook on *every* file plus mypy on the whole `kedro/` package (typically 3–5 min per iteration). Instead:
   - For a single failing pre-commit hook: `pre-commit run <hook-id> --files <changed-files>` (seconds).
   - For ruff/format: `ruff check --fix <file>` or `ruff format <file>` (sub-second).
   - For mypy: `mypy <file> --strict --allow-any-generics --no-warn-unused-ignores` (5–10s vs. 1–2 min).
   - For Import Linter: `lint-imports --config pyproject.toml` (it scans the whole project regardless — but skips pre-commit overhead).
   - For unit tests: `pytest tests/path/to/test_thing.py::TestClass::test_method` (sub-second per test) instead of `make test` (full suite, several min).

   Full per-hook recipes in [reference.md](reference.md) section "Fast lint iteration". Track C does **not** run `scripts/run_local_checks.sh` here.
6. Move to the next finding.

**Local-only failures** (Track L). Track L drives this loop from the output of Step 5a's full sweep. When `run_local_checks.sh` reports a FAIL, identify the failing hook from its output and verify the fix with the targeted command above — *not* by re-running the full `run_local_checks.sh` sweep after every iteration. Re-run the full sweep only as the final check before commit (Step 5a).

**DCO sign-off** (Track C). List commits without `Signed-off-by:`. Apply one of the recipes from [reference.md](reference.md) section "DCO sign-off recipes" (typically `git rebase <base> --signoff` for older commits). Ask the user before amending; **explicitly warn that amend requires a force-push** (`git push --force-with-lease`).

### 5. Verify locally → commit + push

Two sub-steps. Run the ones your track requires.

#### 5a. Verify locally (full sweep)   _Track: L_

```bash
bash scripts/run_local_checks.sh
```

The script auto-detects scope from the changed files (`code`, `docs`, or `code+docs`). It refuses to run if no isolated env is active. Show the user the per-check pass/fail/skip summary. Any FAILs feed back into Step 4's local-fix loop.

**Important — iterate with targeted commands, not the full sweep.** `run_local_checks.sh` calls `make lint` which runs every pre-commit hook on every file plus mypy on the entire `kedro/` package (3–5 min). For each FAIL, identify the failing hook and use the targeted recipe from [reference.md](reference.md) section "Fast lint iteration" (seconds, not minutes). Re-run `run_local_checks.sh` only as the **final** belt-and-suspenders check once all targeted recipes pass.

**Track C skips 5a entirely** — per-check verification already happened in Step 4 for the specific failing checks; running the full sweep would be redundant and slow.

#### 5b. Commit + push   _Tracks: L (optional), C_

On user confirmation:
- `git add` only the touched files.
- `git commit` with a message you propose (or the user provides). Use `-s` for DCO sign-off.
- `git push` (or `git push --force-with-lease` for the DCO rebase case — warn explicitly).

On Track L, commit + push is **optional**: the user may just want a clean local working tree before continuing to iterate. Always confirm intent.

After push on Track C, **do not block waiting for CI**. If the user wants to see the new CI state, they can re-run `bash scripts/watch_ci.sh` later for a fresh snapshot.

## Out of scope

- **Watching CI to completion (blocking)** — `watch_ci.sh` is snapshot-only by design. The skill surfaces current state and exits; the user re-runs it later if they want a refreshed view. This avoids long blocking sessions where the agent is idle waiting on CI.
- **Running e2e tests locally** — slow, requires packaging the wheel, and rarely needed during the babysit loop. If `e2e-tests` is the failing check, the skill surfaces the CI logs and stops — no local reproduction.
- **Comments triage** — PR review comments, reviewer asks, and bot-generated review feedback (such as Bugbot, the Cursor-style review bot that posts inline comments). The author handles reviewer feedback directly.
- **Judgment-based code review** — defers to `review-kedro-pr`.
- **`RELEASE.md` compliance** — adding or editing `RELEASE.md` entries is a reviewer convention, not a CI check (`gh pr checks` does not surface it). Defers to `review-kedro-pr`, which flags missing entries as Critical.
- **Security review** — defers to a future `kedro-security-review` skill.
- **Authoring features / large refactors** — out of scope; this skill only applies the smallest scoped fix to make a check pass.
- **Performance regressions** — `pipeline-performance-test` (label-triggered on PRs with the `performance` label) reports timing, not pass/fail. The skill surfaces the timing delta and asks the user to investigate manually.
- **Installing system tools** — the skill prints install hints for `vale`, `lychee`, `gh` but never invokes `brew`/`apt`/`cargo` on the user's behalf.
