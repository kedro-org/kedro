---
name: kedro-babysit
description: >-
  Get a Kedro PR merge-ready by fixing CI / test failures, resolving clear
  merge conflicts, and ensuring RELEASE.md and DCO compliance. Use when the
  user asks to babysit a PR, fix CI, or get this PR green.
---
# Babysit Kedro PR

Drive a Kedro PR to a merge-ready state. Fix mechanical CI failures, resolve clear merge conflicts, ensure `RELEASE.md` and DCO compliance. Use a conservative posture: stop and ask the user before every commit, push, force-push, and merge-conflict resolution.

This skill complements `review-kedro-pr` (judgment-based code review). It does **not** triage PR review comments.

## Workflow

### 1. Identify the PR + preflight

Detect the PR from the current branch, or accept a PR URL/number from the user:

```bash
gh auth status
gh pr view --json number,title,baseRefName,headRefName
```

Preflight checks:
- `gh` is installed and authenticated. If not, stop and ask the user to install/authenticate.
- The working tree is clean enough to operate on. Run `git status --porcelain`; if there are uncommitted changes unrelated to the planned fixes, warn the user and ask whether to stash or proceed.
- A PR exists for the current branch. **If no PR exists**, stop with: "Open a PR first (e.g. `gh pr create`); creating PRs is out of scope for this skill."

### 2. Set up the Python environment

Run `scripts/bootstrap_env.sh`. The script:

- Detects an active isolated env: `$VIRTUAL_ENV` set, OR (`$CONDA_PREFIX` set AND `$CONDA_DEFAULT_ENV != "base"`).
- If no isolated env active: ask the user "venv or conda?" + name. Pass to `bootstrap_env.sh --type {venv|conda} --name <name>`. The script creates the env and prints the activation command. **The skill cannot activate the env from a child shell** — instruct the user to activate and re-invoke the skill.
- If active but dependencies missing: the script runs `make install-test-requirements` + `make install-pre-commit` (and `make install-docs-requirements` if the PR touches `docs/` or `**.md`).
- Probes for system tools `vale`, `lychee`, `gh`. Prints platform-specific install hints if missing; does not install them.

Read [reference.md](reference.md) section "Environment setup" for manual recipes and cross-platform install hints.

### 3. Snapshot the PR state

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
- Whether `kedro/` files changed without a corresponding entry in `# Upcoming Release` of `RELEASE.md`.

### 4. Fix in this fixed order

Each sub-step ends with **stop and ask before staging / committing / pushing / amending**.

**Merge conflicts.** If `mergeStateStatus` is `DIRTY` or `BEHIND`, sync with the base branch. Resolve conflicts only when the intent is unambiguous; otherwise stop and ask the user.

**CI failures.** For each failing check:
1. Look up the local invocation in [reference.md](reference.md) section "CI-to-local mapping".
2. Pull failed-job logs via `bash scripts/watch_ci.sh` (don't re-watch if already complete; just dump the latest failed logs).
3. Propose the smallest scoped fix using [reference.md](reference.md) section "Common CI failures and fixes".
4. Apply the fix to the working tree only (no `git add` / `git commit`).
5. Re-run the corresponding Make target locally to verify.
6. Move to the next finding.

**RELEASE.md.** If any `kedro/` file changed but `RELEASE.md` is not in the diff, draft a bullet:

```bash
bash scripts/add_release_entry.sh --section {major|fix|docs|community} "Description."
```

The script prints `git diff RELEASE.md` for review. Ask the user to confirm the section and wording before staging. See [reference.md](reference.md) section "RELEASE.md structure and rules".

**DCO sign-off.** List commits without `Signed-off-by:`. Apply one of the recipes from [reference.md](reference.md) section "DCO sign-off recipes" (typically `git rebase <base> --signoff` for older commits). Ask the user before amending; **explicitly warn that amend requires a force-push** (`git push --force-with-lease`).

### 5. Verify locally, then commit + push, then watch CI

Run the local checks:

```bash
bash scripts/run_local_checks.sh
```

The script auto-detects scope (`--code` / `--docs`) from the changed files. It refuses to run if no isolated env is active. Show the user the per-check pass/fail/skip summary.

On user confirmation:
- `git add` only the touched files.
- `git commit` with a message you propose (or the user provides).
- `git push` (or `git push --force-with-lease` for the DCO rebase case — warn explicitly).

Then watch CI:

```bash
bash scripts/watch_ci.sh
```

The script polls `gh pr checks --watch` until all checks complete and dumps `--log-failed` for any failures, annotated with their Make targets. See [reference.md](reference.md) section "gh CLI cheatsheet" for the underlying commands.

**Loop back to step 4** with any new failures. Only re-snapshot (step 3) if the base branch has moved further while CI was running.

## Out of scope

- **Comments triage** — PR review comments, reviewer asks, and bot-generated review feedback (such as Bugbot, the Cursor-style review bot that posts inline comments). The author handles reviewer feedback directly.
- **Judgment-based code review** — defers to `review-kedro-pr`.
- **Security review** — defers to a future `kedro-security-review` skill.
- **Authoring features / large refactors** — out of scope; this skill only applies the smallest scoped fix to make a check pass.
- **Performance regressions** — `pipeline-performance-test` (label-triggered on PRs with the `performance` label) reports timing, not pass/fail. The skill surfaces the timing delta and asks the user to investigate manually.
- **Installing system tools** — the skill prints install hints for `vale`, `lychee`, `gh` but never invokes `brew`/`apt`/`cargo` on the user's behalf.
