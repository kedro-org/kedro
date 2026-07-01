---
name: merge
description: >-
  Orchestrate CLI merge after review: resolve plan, optional dry-run, then
  pdlc plan merge. Does not edit live spec files by hand.
---

# Plan merge

Merge closes the PDLC loop after `/pdlc-review`: the CLI applies the plan spec
delta to the themed product spec, writes history, archives the plan (including
`review.md`), and for **backlog-linked** plans archives the linked backlog item
through the active provider (and may archive a parent when the provider reports
no remaining active children).

## External skills

Discover extension skills using keywords from the merge topic:

```bash
pdlc skill list --phase merge --include-unscoped --query "<topic>"
pdlc skill show <id>
```

**Skill references** use the canonical index `id` from list JSON. Resolve any
skill with `pdlc skill show <id>` (works for filesystem, cursor, and git-hosted
providers). Filesystem skills may also cite the optional `path` field from list
output.

If a returned skill looks relevant, briefly say why and **ask the user** whether
to use it before calling `pdlc skill show <id>` or following its guidance. Do
not silently adopt extension skills.

## Preconditions

- Review disposition is `approved` with `Satisfied: yes` in `review.md`.
- `pdlc plan validate <dir> --require-complete` exits 0.
- `pdlc plan validate <dir> --require-review-satisfied` exits 0.
- Themed spec is initialized (`pdlc/spec/themes.toml` and `pdlc/spec/themes/`).

## Workflow

1. Resolve the plan (`pdlc plan resolve`, or path given by the user).
2. Optional dry-run: `pdlc plan merge <dir> --dry-run` and summarize actions.
3. Apply: `pdlc plan merge <dir>`.
4. Summarize: requirement ids touched, archived plan path, and for backlog-linked
   plans any backlog archive paths returned in dry-run `archive` actions.

## Archive paths

| Artifact | Active | After merge |
|----------|--------|-------------|
| Plan | `pdlc/spec/changes/<plan-id>/` | `pdlc/spec/archive/plans/<plan-id>/` |
| Linked backlog item (backlog-linked plans) | Provider-specific active path | Provider archive location |
| Local filesystem deliverable child | `pdlc/epics/<NNNN>-<slug>/stories/<file>.md` | `pdlc/epics/archive/<NNNN>-<slug>/stories/` |
| Local filesystem parent feature (when no active children remain) | `pdlc/epics/<NNNN>-<slug>/` | `pdlc/epics/archive/<NNNN>-<slug>/` |

Direct plans (`plan-{NNNN}-*`) do not archive backlog items.

## Hard constraints

- Do **not** hand-edit files under `pdlc/spec/themes/` or `spec_delta.md` during merge.
- Do **not** skip `pdlc plan merge` in favour of manual spec edits.
- Use global topic themes from `pdlc spec theme list`, not backlog ids or plan ids.

## Anti-patterns

- Merging before review or with incomplete tasks
- Merging when `review.md` is missing or not satisfied
- Editing live requirement files instead of running the CLI
- Inventing theme ids not in `themes.toml`
