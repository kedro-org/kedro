---
name: split
description: >-
  Guidance for splitting a parent backlog item into child items. Use when
  decomposing scope before planning; respects provider breakdown rules.
---

# Backlog breakdown

Decompose a **parent backlog item** into children that together cover its scope.
Use `pdlc backlog` commands and backlog ids—do not invent file paths under
`pdlc/epics/` unless the active provider is local filesystem.

## External skills

Discover extension skills using keywords from the parent scope:

```bash
pdlc skill list --phase split --include-unscoped --query "<topic>"
pdlc skill show <id>
```

**Skill references** use the canonical index `id` from list JSON. Resolve any
skill with `pdlc skill show <id>` (works for filesystem, cursor, and git-hosted
providers). Filesystem skills may also cite the optional `path` field from list
output.

If a returned skill looks relevant, briefly say why and **ask the user** whether
to use it before calling `pdlc skill show <id>` or following its guidance. Do
not silently adopt extension skills.

## Before you split

Read the parent item (`pdlc backlog show <id>`). Confirm breakdown is allowed;
if the provider refuses, stop and adjust scope or parent choice.

Pull out:

- **Outcome** the parent promises
- **In** and **Out** boundaries
- **Done** signals at parent level

## How to slice children

Each child should be:

- **Deliverable** — profile with **Acceptance criteria** when it will be planned
- **Coherent** — one main capability or risk area
- **Right-sized** — plannable and reviewable in one pass

Create children with:

```bash
pdlc backlog create --parent <parent-id> --profile deliverable --title "..."
```

## Coverage map

| Parent element | Child backlog id(s) | Notes |
|----------------|---------------------|-------|
| …            | …                   | …     |

Every **In** item and parent **Done** signal maps to at least one child.

## Provider rules

- **`epics`**: parent **feature** item → **deliverable** children; no third level
- **`issues`**: flat deliverable items only (no parent ids; no breakdown)
- **`github`**: follows `[backlog.github]` hierarchy settings in `pdlc.toml`

When breakdown is disallowed, do not force file-based workarounds—change the parent
or tooling configuration.

## Hand off

When children exist and acceptance criteria are filled, plan with
`/pdlc-plan` or `pdlc plan template --backlog-id` for each implementable child.
