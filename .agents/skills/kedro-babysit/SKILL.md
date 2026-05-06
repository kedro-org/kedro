---
name: kedro-babysit
description: >-
  Babysit Kedro changes — verify locally before pushing, fix failing CI checks
  (lint, tests, detect-secrets, docs), resolve clear merge conflicts, ensure DCO
  sign-off, or watch CI. Use when the user asks to babysit a PR or local changes,
  fix CI, get this PR green, or watch CI.
---
# Babysit Kedro PR

Drive Kedro changes toward a mergeable state — locally before push, or on an open PR. Fix mechanical CI failures, resolve clear merge conflicts, ensure DCO sign-off. Use a conservative posture: stop and ask the user before every commit, push, force-push, and merge-conflict resolution.

This skill complements `review-kedro-pr` (judgment-based code review). It does **not** triage PR review comments.

## How to invoke this skill

**Pick a track first**, then run only the steps that track requires. The four tracks split along **two axes**: *what the user wants* (verify locally / fix CI / pre-merge gate / just watch) and *how much time they want to spend* (**fast** = single targeted iteration, **thorough** = full local sweep + blocking CI watch).

| Track | Mode | When the user says... | What to do |
|---|---|---|---|
| **A. Local-only** | **fast** (~2–10 min) | "babysit my local changes", "verify before push", "lint my diff", "run checks locally" | Step 2 (env) → Step 5a (`scripts/run_local_checks.sh`) → per-fail fix loop using targeted commands. **Skip** GitHub fetch, snapshot, watch CI. **No PR required.** |
| **B. Targeted CI fix** | **fast** (~5–15 min) | "CI is failing", "fix the lint job", "what's failing on CI?", "fix the X check on this PR" | Step 1 → Step 2 → Step 3 (snapshot) → Step 4 (fix **only** the failing checks; verify each with the most targeted command — e.g. `pre-commit run ruff --files <changed>` or `mypy <file>`, **not** `make lint` — see [reference.md](reference.md) "Fast lint iteration") → optional Step 5b/5c. Use `bash scripts/watch_ci.sh --no-wait` for snapshot-mode log fetch. **Skip Step 5a** — per-check verify already happened in Step 4. |
| **C. Full PR sweep** | **thorough** (~30–60+ min) | "do a full sweep", "run everything locally", "is this PR ready to merge?", "get this PR green end-to-end", "thorough check before merge" | All steps 1–5, **including Step 5a's full local sweep** (lint + tests + detect-secrets + linkcheck + language-lint, depending on scope) **and Step 5c's blocking `gh pr checks --watch`** (10–40 min). Use this when the user wants belt-and-suspenders verification — the full sweep catches side-effects in files the per-check fixes didn't touch. |
| **D. Watch CI** | **passive** (CI duration, 10–40 min) | "watch CI", "did my push pass?", "monitor this PR" | Step 1 (PR detection only) → Step 5c (`scripts/watch_ci.sh`). On red checks, fall through to Track B. |

### Picking the right track

- **Default to the fast tracks (A or B).** Most invocations are iterative and the user wants quick feedback. C is the exception, not the default.
- **Pick C only when the user explicitly signals thoroughness** ("do a full sweep", "before merge", "everything", "thorough"). C is ~5× slower than B for the same starting state.
- **If "babysit this PR" is the only signal**, treat it as ambiguous between B and C — **default to B** (fast) and offer to escalate: *"I'll do a targeted CI fix (~5–15 min). If you want the full pre-merge sweep with local belt-and-suspenders verification (~30–60 min) instead, say so."*
- **If intent is unclear at all**, ask once: *"Verify local changes (fast, no PR), fix failing CI (fast, targeted), full pre-merge sweep (thorough, slow), or just watch CI?"* Pick a track **before** invoking any script.

Each step header below is annotated with the tracks that need it (e.g. `Tracks: A, C`). Skip a step if your track is not listed.

## Workflow

### 1. Identify the PR + preflight   _Tracks: B, C, D_

Detect the PR from the current branch, or accept a PR URL/number from the user:

```bash
gh auth status
gh pr view --json number,title,baseRefName,headRefName
```

Preflight checks:
- `gh` is installed and authenticated. If not, stop and ask the user to install/authenticate.
- The working tree is clean enough to operate on. Run `git status --porcelain`; if there are uncommitted changes unrelated to the planned fixes, warn the user and ask whether to stash or proceed.
- A PR exists for the current branch. **If no PR exists**, stop with: "Open a PR first (e.g. `gh pr create`); creating PRs is out of scope for this skill." (Track A skips this preflight entirely — it works on uncommitted/unpushed changes.)

### 2. Set up the Python environment   _Tracks: A, B, C_

Track D skips this step — `watch_ci.sh` only needs `gh` (already verified by Step 1's preflight) and does not require a Python env.

Run `scripts/bootstrap_env.sh`. The script:

- Detects an active isolated env: `$VIRTUAL_ENV` set, OR (`$CONDA_PREFIX` set AND `$CONDA_DEFAULT_ENV != "base"`).
- If no isolated env active: ask the user "venv or conda?" + name. Pass to `bootstrap_env.sh --type {venv|conda} --name <name>`. The script creates the env and prints the activation command. **The skill cannot activate the env from a child shell** — instruct the user to activate and re-invoke the skill.
- If active but dependencies missing: the script runs `make install-test-requirements` + `make install-pre-commit` (and `make install-docs-requirements` if the PR touches `docs/` or `**.md`).
- Probes for system tools `vale`, `lychee`, `gh`. Prints platform-specific install hints if missing; does not install them.

Read [reference.md](reference.md) section "Environment setup" for manual recipes and cross-platform install hints.

### 3. Snapshot the PR state   _Tracks: B, C_

Single read-only pass:

```bash
gh pr view --json mergeable,mergeStateStatus,headRefOid,files
gh pr checks
git log <base>..HEAD --format='%H %(trailers:key=Signed-off-by)'
```

Show the user a one-screen summary:
- Mergeable status (`CLEAN` / `BEHIND` / `DIRTY` / `BLOCKED`).
- Failing CI checks, each annotated with the local Make target from [reference.md](reference.md) section "CI-to-local mapping".
- Commits missing DCO `Signed-off-by:` trailer.

### 4. Fix in this fixed order   _Tracks: A, B, C — sub-bullets gate per track too_

Each sub-step ends with **stop and ask before staging / committing / pushing / amending**. Track A only triggers the "Local-only failures" sub-bullet (the others assume an open PR and CI logs).

**Merge conflicts** (Tracks B, C). If `mergeStateStatus` is `DIRTY` or `BEHIND`, sync with the base branch. Resolve conflicts only when the intent is unambiguous; otherwise stop and ask the user.

**CI failures** (Tracks B, C). For each failing check:
1. Look up the local invocation in [reference.md](reference.md) section "CI-to-local mapping".
2. Pull failed-job logs via `bash scripts/watch_ci.sh --no-wait` (snapshot mode — does not block on still-running checks). If the run already finished, omit `--no-wait`.
3. Propose the smallest scoped fix using [reference.md](reference.md) section "Common CI failures and fixes".
4. Apply the fix to the working tree only (no `git add` / `git commit`).
5. **Verify with the most targeted command available** — almost never `make lint`, which runs *every* pre-commit hook on *every* file plus mypy on the whole `kedro/` package (typically 3–5 min per iteration). Instead:
   - For a single failing pre-commit hook: `pre-commit run <hook-id> --files <changed-files>` (seconds).
   - For ruff/format: `ruff check --fix <file>` or `ruff format <file>` (sub-second).
   - For mypy: `mypy <file> --strict --allow-any-generics --no-warn-unused-ignores` (5–10s vs. 1–2 min).
   - For Import Linter: `lint-imports --config pyproject.toml` (it scans the whole project regardless — but skips pre-commit overhead).
   - For unit tests: `pytest <specific-test>` or `make test` for the full suite.

   Full per-hook recipes in [reference.md](reference.md) section "Fast lint iteration". Do **not** run the full `scripts/run_local_checks.sh` sweep here; that's for Step 5a as a final pre-push check.
6. Move to the next finding.

**Local-only failures** (Track A). Same micro-flow as CI failures: when `run_local_checks.sh` (Step 5a) reports a FAIL, identify the failing hook from its output and verify the fix with the targeted command above — *not* by re-running the full `run_local_checks.sh` sweep after every iteration. Re-run the full sweep only as the final check before commit.

**DCO sign-off** (Tracks B, C). List commits without `Signed-off-by:`. Apply one of the recipes from [reference.md](reference.md) section "DCO sign-off recipes" (typically `git rebase <base> --signoff` for older commits). Ask the user before amending; **explicitly warn that amend requires a force-push** (`git push --force-with-lease`).

### 5. Verify locally → commit + push → watch CI

Three sub-steps. Run the ones your track requires.

#### 5a. Verify locally (full sweep)   _Tracks: A, C_

```bash
bash scripts/run_local_checks.sh
```

The script auto-detects scope from the changed files (`code`, `docs`, or `code+docs`). It refuses to run if no isolated env is active. Show the user the per-check pass/fail/skip summary. On Track A, this is the entry point: any FAILs feed back into Step 4's local-fix loop.

**Important — iterate with targeted commands, not the full sweep.** `run_local_checks.sh` calls `make lint` which runs every pre-commit hook on every file plus mypy on the entire `kedro/` package (3–5 min). For each FAIL, identify the failing hook and use the targeted recipe from [reference.md](reference.md) section "Fast lint iteration" (seconds, not minutes). Re-run `run_local_checks.sh` only as the **final** belt-and-suspenders check once all targeted recipes pass.

**Track B skips 5a entirely** — per-check verification already happened in Step 4 for the specific failing checks; running the full sweep would be redundant.

#### 5b. Commit + push   _Tracks: A (optional), B, C_

On user confirmation:
- `git add` only the touched files.
- `git commit` with a message you propose (or the user provides). Use `-s` for DCO sign-off.
- `git push` (or `git push --force-with-lease` for the DCO rebase case — warn explicitly).

On Track A, commit + push is **optional**: the user may just want a clean local working tree before continuing to iterate. Always confirm intent.

#### 5c. Watch CI   _Tracks: B (optional), C, D_

```bash
bash scripts/watch_ci.sh
```

Polls `gh pr checks --watch` until all checks complete (10-40 min) and dumps `--log-failed` for any failures, annotated with their Make targets. **For a one-shot snapshot without waiting**, use `--no-wait`. See [reference.md](reference.md) section "gh CLI cheatsheet" for the underlying commands.

**Loop back to Step 4** with any new failures. Only re-snapshot (Step 3) if the base branch has moved further while CI was running.

## Out of scope

- **Comments triage** — PR review comments, reviewer asks, and bot-generated review feedback (such as Bugbot, the Cursor-style review bot that posts inline comments). The author handles reviewer feedback directly.
- **Judgment-based code review** — defers to `review-kedro-pr`.
- **`RELEASE.md` compliance** — adding or editing `RELEASE.md` entries is a reviewer convention, not a CI check (`gh pr checks` does not surface it). Defers to `review-kedro-pr`, which flags missing entries as Critical.
- **Security review** — defers to a future `kedro-security-review` skill.
- **Authoring features / large refactors** — out of scope; this skill only applies the smallest scoped fix to make a check pass.
- **Performance regressions** — `pipeline-performance-test` (label-triggered on PRs with the `performance` label) reports timing, not pass/fail. The skill surfaces the timing delta and asks the user to investigate manually.
- **Installing system tools** — the skill prints install hints for `vale`, `lychee`, `gh` but never invokes `brew`/`apt`/`cargo` on the user's behalf.
