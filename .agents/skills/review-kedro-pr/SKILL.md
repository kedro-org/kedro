---
name: review-kedro-pr
description: >-
  Review a Kedro PR for checklist compliance, architecture, correctness, and
  clarity. Optionally post findings as a GitHub PR comment. Use when the user
  asks to review a PR, review this PR, or do a PR review.
---
# Review Kedro PR

Review a Kedro pull request. Start with general review guidelines (any project), then apply Kedro-specific checks. Output findings to chat by default, or post to GitHub when asked.

## Workflow

### 1. Identify the PR

Detect the PR from the current branch or accept a PR URL/number from the user:

```bash
gh pr view --json number,title,body,baseRefName,headRefName
```

If the user provides a PR URL or number, use that instead.

### 2. Gather the diff and existing comments

```bash
gh pr diff <number>
gh pr view <number> --comments
gh api repos/{owner}/{repo}/pulls/{number}/comments
```

Read existing review comments and discussion. Don't repeat what's already been said — skip issues that are already covered by existing comments. If you agree with an existing comment, you can reference it. If you disagree, explain why.

### 3. Analyze

Work through the general review guidelines first, then the Kedro-specific review areas. Focus only on changes introduced by this PR. Only flag issues not already raised in existing comments.

### 4. Verify findings

Before delivering, go through every finding one by one and check:
- Is this actually a problem, or a false positive?
- Is the file path and line number correct?
- Is the severity (Critical vs Suggestion) appropriate?
- Is the change in scope? `gh pr diff` includes cherry-picked or rebased-in commits from other branches. Cross-check with `gh pr view <number> --json commits --jq '.commits[].messageHeadline'` — if a commit clearly belongs to a different PR (e.g. references a different `#NNNN`), drop findings on those changes.

Drop anything you're not confident about. Fewer accurate findings are better than many noisy ones.

### 5. Format and deliver

Format findings using the "Output format" section at the end of this file. Two modes:

- **Review only (default):** Output all findings as chat messages. The user can read, edit, or discard before deciding whether to post.
- **Review and post:** When the user explicitly says "post", "submit", or "review and post", post findings directly to the PR on GitHub. See "Output format" for the exact commands.

---

## General review guidelines

These apply to any project. Work through them in order.

### 1. Understand context and scope

- Understand what problem the PR is solving.
- Read the PR description thoroughly, including:
  - Dev notes
  - Linked issues
  - Any prior discussions or comments

### 2. Evaluate PR scope

- Check if the PR is focused on a single purpose.
- If there are too many changes or unrelated updates, suggest splitting into smaller PRs.
- Verify the changes actually align with the stated goal.

### 3. QA and validation

- Check if QA/testing steps are mentioned in the PR description.
- If not, ask the author to add clear steps to validate the changes.
- Mentally walk through the described QA steps and verify:
  - Expected functionality
  - Edge cases and failure scenarios
- Watch out for regressions or unintended side effects.

### 4. Code review and readability

- Go through the file changes and understand the logic.
- Suggest improvements where needed:
  - Better variable/function names
  - Cleaner structure or readability

### 5. Code design and modularity

- Look for opportunities to improve structure:
  - Can large functions be split?
  - Can logic be broken into smaller, reusable pieces?
- Suggest helper/utility functions if the same logic is repeated.
- Aim for simple, maintainable code.

### 6. Docstrings and inline documentation

- Check if docstrings are present on new/changed classes, functions, and methods.
- Docstrings must use Google style (`Args:`, `Returns:`, `Raises:`) to avoid rendering issues in the API docs.
- For public APIs:
  - Ensure inputs/outputs are clearly documented.
  - Suggest adding examples if helpful.

### 7. Testing and coverage

- Check if there are enough unit tests.
- Make sure tests cover:
  - Core logic
  - Edge cases
- Tests should be meaningful and easy to follow, not just for coverage.

---

## Kedro-specific: PR checklist compliance

Check the PR against the Kedro PR template requirements.

### RELEASE.md entry

Any change to code under `kedro/` must have a corresponding bullet in `RELEASE.md` under `# Upcoming Release`, in the correct H2 section:

- `## Major features and improvements` — new features, significant enhancements
- `## Bug fixes and other changes` — bug fixes, minor changes, dependency updates
- `## Documentation changes` — docs-only changes
- `## Community contributions` — added by maintainers for external contributors

Format: `* Description of the change.`

If the PR modifies `kedro/` files but `RELEASE.md` is not in the diff, flag as Critical.

### Project documentation

If the PR changes public API behavior or adds new features, check whether the Kedro project docs (`docs/`) are updated. Docs use MkDocs with standard markdown — check for correct formatting to avoid rendering issues.

### Backward compatibility

- Public API changes must not break existing callers without a migration path.
- Check for: removed/renamed parameters, changed return types, changed default values, removed public classes/functions.
- If breaking, there should be a deprecation warning or a migration note in `RELEASE.md`.

### Kedro-Viz impact

If the change affects pipeline structure, metadata, catalog behavior, or dataset output, flag for Viz team coordination.

---

## Kedro-specific: API usage

Check that the PR uses Kedro abstractions correctly.

- **Datasets** must subclass `AbstractDataset` and implement `load`, `save`, `_describe`. Versioned datasets subclass `AbstractVersionedDataset`.
- **Runners** must subclass `AbstractRunner` and implement `_run` and `_get_executor`.
- **Hooks** must use the `@hook_impl` marker from `kedro.framework.hooks`.
- **Config loaders** must subclass `AbstractConfigLoader`.
- **Naming conventions** should match existing patterns in the same module (method names, parameter names, class names).

For full API signatures and the complete list of base classes, read [reference.md](reference.md) section "Kedro public API surface".

**Non-obvious patterns:** Some files use complex patterns on purpose (e.g. `__getattr__`, `__init_subclass__` wrapping). If the PR touches `kedro/io/core.py`, `kedro/framework/hooks/manager.py`, or `kedro/io/shared_memory_dataset.py`, read [reference.md](reference.md) section "Non-obvious patterns" before flagging anything — those patterns are intentional.

---

## Out of scope

Do NOT flag:

- **Pre-existing issues** — only review changes in the diff.
- **Security issues** — handled by the separate `kedro-security-review` skill.
- **Anything CI already checks mechanically** — the following are handled by the `kedro-babysit` skill, which runs and fixes them automatically:
  - Linting and formatting (ruff)
  - Running unit tests (pytest)
  - Import-linter contract execution (architecture compliance)
  - DCO sign-off verification
  - Any other CI check with a pass/fail outcome

This skill is about reviewing code, not running checks.

---

## Output format

Each finding gets an **inline comment** on the specific line, plus there's a **summary** of all findings. Delivery depends on the mode.

### Review only (default) — output to chat

Present all findings as chat messages. For each finding, include:
- The file path and line number.
- **Critical:** or **Suggestion:** prefix.
- A concise explanation and suggested fix.

After all findings, output the summary using the template below.

### Review and post — output to GitHub PR

Write a JSON file with the full review payload and post it via the script:

```json
{
  "event": "COMMENT",
  "body": "## Kedro PR Review\n...(summary)...",
  "comments": [
    { "path": "file.py", "line": 42, "side": "RIGHT", "body": "**Critical:** ..." },
    { "path": "other.py", "line": 15, "side": "RIGHT", "body": "**Suggestion:** ..." }
  ]
}
```

Then post:

```bash
bash .agents/skills/review-kedro-pr/scripts/post_review.sh <review_json_file>
```

This creates one review with the summary as the main message and inline comments on specific lines. Delete the JSON file after posting.

### Summary template

Used in both modes:

```markdown
## Kedro PR Review
> Generated with `review-kedro-pr` skill.

### Overview
- **Critical:** <count> | **Suggestions:** <count>

### Critical (must fix before merge)
- [ ] `file/path.py:L42` — brief description

### Suggestions (consider improving)
- [ ] `file/path.py:L15` — brief description

### Notes
- General review: <summary or "no issues">
- PR checklist: <summary or "no issues">
- API usage: <summary or "no issues">
```

### Classification

- **Critical** = must fix before merge (violations, missing requirements, bugs).
- **Suggestion** = worth improving but not blocking.
- If a section has no findings, write "No issues found."
- If a section has multiple points, use bullet points for clarity.

### Communication guidelines

- Keep feedback clear and constructive.
- Ask questions instead of assuming.
- Be respectful of the author's approach while suggesting improvements.
