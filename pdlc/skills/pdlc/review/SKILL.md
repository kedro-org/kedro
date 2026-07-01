---
name: review
description: >-
  Guidance for reviewing a completed plan with deterministic checks first, then
  agent review. Use when validating task completion, acceptance or spec-check
  coverage, spec-delta truth, and code quality before sign-off. Writes review.md
  in the plan directory.
---

# Review

Review verifies that implementation is complete, correct, and consistent with
the plan and product spec. Each review persists results to `review.md` in the
plan directory.

## Upstream extension skills

Do **not** discover new extension skills (`pdlc skill list` is not for this
phase).

Auto-apply skills already selected upstream:

1. For **backlog-linked** plans, read backlog item **Links** for skill references
2. Read `tasks.md` and every other file in the plan directory
3. For each skill `id` referenced, run `pdlc skill show <id>` and follow its
   guidance during review

Resolve skills by canonical index `id` with `pdlc skill show <id>`.

## Deterministic checks first

Before subjective review, run hard checks and stop on failure.

1. Resolve plan dir (`pdlc plan resolve`, `pdlc plan resolve --number NNNN`, or explicit path).
2. Validate plan structure and completion:
   - `pdlc plan validate <dir> --require-complete`
3. For **backlog-linked** plans (slug-only directory with `plan.yaml` `backlog_id`), validate the linked item:
   - `pdlc backlog validate <backlog_id>` (from `plan.yaml` or `pdlc plan resolve --backlog-id`)
   Skip this step for **direct** plans (`plan-{NNNN}-*`).
4. Run repository quality checks declared in `pdlc.toml`:
   - `pdlc plan review checks --json`

Check selection uses changed paths from the branch delta (`base_ref...HEAD`) plus
staged, unstaged, and non-ignored untracked working-tree paths. Unconfigured
repos, empty changed paths, and zero matching checks fail. Record check `id`
values from JSON output in `review.md`.

If any deterministic step fails, record blockers in `review.md` and do not approve.

## review.md lifecycle

Create `review.md` on the **first** review only:

```bash
pdlc plan review template <plan-dir>
```

Write the returned `content` to `<plan-dir>/review.md`. On later reviews, update the
top sections and append a new history round — do not recreate the file from scratch.

Scaffold blocker lines with:

```bash
pdlc plan review blocker template --title "[check:R0004] Fix …; path; verify"
```

### File structure

| Section | Updated each round? | Purpose |
|---------|---------------------|---------|
| `## Status` | Yes | Disposition, satisfied flag, round metadata |
| `## Open blockers` | Yes | Unchecked items that must clear before approval |
| `## History` | Append only | Immutable audit of each full review round |

**Status** must contain exactly four lines:

- `Disposition: approved` or `Disposition: changes_requested`
- `Satisfied: yes` or `Satisfied: no`
- `Last round: N`
- `Last reviewed: YYYY-MM-DD`

**Open blockers** use single-line checkboxes:

`- [ ] [category:ref] Imperative fix; path or command; how to verify`

Categories: `[task:…]`, `[check:R…]`, `[acceptance:…]`, `[deterministic]`,
`[quality]`, `[spec-delta]`.

History findings use narrative prefixes (`[blocker]`, `[resolved]`, `[note]`) — not
actionable checkboxes.

Do **not** promote blockers into `tasks.md`. Fix code, then re-run a full review.

## Agent review checks

After deterministic checks pass, run a **full** review every time:

- Confirm all `tasks.md` intent is reflected in code and tests.
- Confirm backlog item acceptance criteria are met (backlog-linked plans) or spec delta checks are met (direct plans).
- Confirm each `spec_delta.md` Add/Modify/Remove item is true in the delivered product behavior.
- Confirm each requirement in the delta is **one testable outcome**—flag plans that
  **Modify** to append scope when they should **Add**, or blocks with too many checks
  (see the plan skill check-count heuristic).
- Review code quality against project conventions (design, readability, test quality, risk of regressions).

Append a history section for the round:

```markdown
### Round N — YYYY-MM-DD

#### Deterministic checks

- [x] plan validate --require-complete
- [x] backlog validate
- [x] review checks: backend

#### Findings

- [blocker] [check:R0004] …
- [note] [quality] …

#### Disposition

changes_requested
```

Rewrite `## Status` and `## Open blockers` to reflect the current state.

## Disposition

| Disposition | Open blockers | Satisfied | Merge? |
|-------------|---------------|-----------|--------|
| `changes_requested` | ≥1 unchecked | no | No |
| `approved` | none unchecked | yes | Yes |

Validate before merge:

```bash
pdlc plan validate <dir> --require-review-satisfied
```

## Anti-patterns

- Skipping deterministic checks and jumping straight to subjective review
- Approving while unchecked tasks, verification items, or open blockers remain
- Treating "tests green" as equivalent to spec/acceptance coverage
- Ignoring spec delta requirements because code looks "reasonable"
- Approving spec deltas that bundle multiple independent outcomes in one requirement
- Hand-authoring `review.md` structure instead of using `pdlc plan review template`
- Adding review fixes to `tasks.md` instead of fixing code and re-reviewing
