---
name: implement
description: >-
  Guidance for implementing a validated plan: execute tasks.md in order, tick
  off checkbox lines, and verify against acceptance criteria or spec checks.
  Use when shipping code for a plan under pdlc/spec/changes/. Does not merge
  spec_delta into spec.md.
---

# Plan implementation

A **plan** under `pdlc/spec/changes/` has a **spec delta** (product changes) and
an ordered **task list** (engineering steps). Backlog-linked plans (slug-only
directory with `plan.yaml`) link to a backlog item; direct plans (`plan-{NNNN}-*`)
do not. Implementation
executes the task list; spec merge into `pdlc/spec/spec.md` happens in a later
workflow.

## Upstream extension skills

Do **not** discover new extension skills (`pdlc skill list` is not for this
phase).

Auto-apply skills already selected upstream:

1. For **backlog-linked** plans, read backlog item **Links** for skill references
2. Read `tasks.md` and every other file in the plan directory
3. For each skill `id` referenced, run `pdlc skill show <id>` and follow its
   guidance

Resolve skills by canonical index `id` with `pdlc skill show <id>`.

## Before you implement

Read `spec_delta.md` and `tasks.md`. The plan directory must pass
`pdlc plan validate`.

Resolve metadata when needed:

```bash
pdlc plan resolve --backlog-id "<id>"   # backlog-linked plan
pdlc plan resolve --number NNNN       # direct plan
```

For **backlog-linked** plans, read the item with `pdlc backlog show <backlog_id>`.
The item must be concrete enough that tasks are actionable.

For **direct** plans, use the plan directory name and `tasks.md` for intent; do
not read backlog items unless tasks require it. Verification maps to spec delta
**Checks**, not item acceptance criteria.

If validation fails or tasks are placeholders, stop and improve the plan with
`/pdlc-plan` before implementing—do not
guess missing scope.

## Hard constraints

- Execute **every** unchecked task under `## Tasks` in file order (group order,
  then line order within each group).
- Each task is **one line**: `- [ ] …` or `- [x] …`. No sub-bullets or
  continuation lines. If work needs more steps, the plan should have more tasks.
- Mark each line `- [x]` on disk **immediately** after that task is done, before
  starting the next.
- Do **not** edit `spec_delta.md` during implementation (scope changes → re-plan).
- Do **not** merge the delta into `pdlc/spec/spec.md` in this workflow.
- Complete all `## Tasks` work before checking items under `## Verification`.

## tasks.md sections

| Section | Role during implement |
|---------|------------------------|
| `## Preconditions` | Confirm gates (plan validated; backlog item validated when linked); tick when true |
| `## Tasks` | Ordered implementation; one checkbox = one focused pass |
| `## Verification` | After all task groups; map to **Acceptance criteria** (backlog-linked) or spec delta **Checks** (direct) |

Treat `spec_delta.md` as read-only context for *what* the product must do; tasks
say *how* to build it.

## Executing a task line

Each line should name what to do, where (path, endpoint, command), and how to
verify on that same line. If a line is too vague to execute, stop and re-plan
rather than splitting it informally.

Prefer existing project conventions. Run project checks when tasks or
verification call for them.

## Quality bar

Before calling implementation done for this plan:

- Every precondition that applies is checked
- Every task under `## Tasks` is `- [x]`
- Every `## Verification` item is checked after the work it validates
- Backlog item **Acceptance criteria** are satisfied (backlog-linked plans), or spec delta **Checks** are satisfied (direct plans)

## Anti-patterns

- Skipping tasks or reordering groups without user agreement
- Leaving tasks unchecked while moving to verification
- Editing `spec_delta.md` to match what was built
- Merging into `spec.md` during implement
- Nested bullets or multi-line tasks under a single checkbox
- Implementing without a validated plan
- One giant task that should have been several single-line tasks
