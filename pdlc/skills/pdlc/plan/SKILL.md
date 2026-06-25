---
name: plan
description: >-
  Guidance for planning work into a spec delta and agent task list. Covers
  backlog-linked and direct plans. Use when writing spec_delta.md and tasks.md.
---

# Planning

A **plan** states how implementation changes the global product spec and which
engineering tasks an agent should run. Plans live under `pdlc/spec/changes/`,
not under `pdlc/epics/`.

Use **`/pdlc-plan`**. Step 1 chooses the path:

- **Backlog-linked** — plan a validated deliverable backlog item
- **Direct** — plan without backlog tracking

Shared rules for `spec_delta.md`, `tasks.md`, and validation apply to both paths.

## External skills

Discover extension skills using keywords from the plan topic:

```bash
pdlc skill list --phase plan --include-unscoped --query "<topic>"
pdlc skill show <id>
```

**Skill references** use the canonical index `id` from list JSON. Resolve any
skill with `pdlc skill show <id>` (works for filesystem, cursor, and git-hosted
providers). Filesystem skills may also cite the optional `path` field from list
output.

If a returned skill looks relevant, briefly say why and **ask the user** whether
to use it before calling `pdlc skill show <id>` or following its guidance. Do
not silently adopt extension skills.

When the user selects extension skills:

- Record each skill `id` in `tasks.md` (task lines or notes) so implement/review
  can load them with `pdlc skill show <id>`
- Add any skill-derived artifacts as extra files in the plan directory (any
  filename beyond `plan.yaml`, `spec_delta.md`, and `tasks.md`)
- Pull skill references from backlog **Links** when backlog-linked

## JSON template output

`pdlc plan template` prints JSON. Treat it as a write contract:

| Field shape | Agent action |
|-------------|--------------|
| Objects with `path` and `content` (`manifest`, `spec_delta`, `tasks`) | Write `content` to `path` on disk |
| Top-level metadata (`kind`, `number`, `backlog_id`, `plan_id`, `dir`) | Read-only context — do not invent values |

**Backlog-linked** templates include writable `manifest`, `spec_delta`, and `tasks`.

**Direct** templates include writable `manifest`, `spec_delta`, and `tasks` (direct
manifest records `kind: direct`, `title`, and `plan_number`).

## Plan directory names

| Plan type | Directory under `pdlc/spec/changes/` | `plan_id` in JSON |
|-----------|----------------------------------------|-------------------|
| Backlog-linked | Slug-only (for example `welcome-and-device-pairing/`) | Same slug-only name |
| Direct | `plan-{NNNN}-{slug}/` | Same `plan-{NNNN}-{slug}/` name |

The global direct plan number lives in `plan.yaml` (`plan_number`) and JSON
`number`, not only in the directory prefix.

## Backlog-linked

A **deliverable** backlog item states what to deliver and how to verify it.

### Before you plan

Read the deliverable item and parent feature item (when present) end to end. The
item must pass `pdlc backlog validate` and be concrete: no placeholder title, no
empty **Acceptance criteria**, no vague scope copied from the parent without a
slice-specific angle.

If the parent is unclear or the item depends on unresolved scope, stop and
improve the parent or confirm assumptions with the user before writing a plan.

Pull from the deliverable item:

- **Description** — the deliverable in one coherent slice
- **Acceptance criteria** — observable checks you must satisfy
- **Links** — designs, APIs, or constraints that bound implementation

The parent's **Description** and **Links** remain the source of truth for overall
intent; the plan refines and delivers this item, not the whole parent scope.

### Artifacts

Each plan directory holds `plan.yaml`, `spec_delta.md`, and `tasks.md`.
**Backlog-linked** plans use a slug-only directory name under `pdlc/spec/changes/`.
The manifest records the external backlog item:

```yaml
kind: backlog
title: "Welcome and device pairing"
backlog_id: "<opaque id from pdlc backlog show>"
```

Scaffold with:

```bash
pdlc backlog show <id>
pdlc backlog validate <id>
pdlc plan template --backlog-id "<id>" --title "Short descriptive title"
```

Write every JSON object that includes both `path` and `content` (including `manifest`).

| File | Purpose |
|------|---------|
| `plan.yaml` | Links the plan to a backlog item (`backlog_id`) |
| `spec_delta.md` | Proposed changes to the global product spec |
| `tasks.md` | Ordered, detailed work for an implementer |

### Verification source

Map item **Acceptance criteria** to lines under `## Verification` in `tasks.md`.

## Direct

A **direct plan** changes the global product spec without a backlog link. Plans
live as `plan-{NNNN}-{slug}/` (global plan numbers).

### Before you plan

Clarify intent with the user: what product behavior changes, what “done” looks
like, and any constraints (APIs, designs, compatibility). Read the themed spec:

- `pdlc spec theme list` — global product topics
- `pdlc spec show RNNNN` — an active requirement
- `pdlc/spec/themes/<topic>/` — one markdown file per requirement

Direct plans do not use backlog **Acceptance criteria**. Observable outcomes live
in the spec delta **Checks** and in `tasks.md` **Verification**.

### Artifacts

Each plan directory holds `plan.yaml`, `spec_delta.md`, and `tasks.md`.

| File | Purpose |
|------|---------|
| `plan.yaml` | Records `kind: direct`, `title`, and `plan_number` |
| `spec_delta.md` | Proposed changes to the global product spec |
| `tasks.md` | Ordered work for an implementer |

Scaffold with:

```bash
pdlc plan next
pdlc plan template --direct --title "Short descriptive title"
```

Write every JSON object that includes both `path` and `content` (including `manifest`).

Optional: `--number NNNN` to override the next global plan id.

### Verification source

Map spec delta **Checks** to lines under `## Verification` in `tasks.md`.

## Global spec and requirements

The product spec is themed by **global topics** under `pdlc/spec/themes/<topic-id>/`
(one file per requirement). Topics are listed in `pdlc/spec/themes.toml`—they are
not backlog ids or plan ids.

Each requirement has:

- **Id** — `RNNNN` in the heading (`## RNNNN: Short title`)
- **Theme** — on **Add** blocks in the delta: `- Theme: <topic-id>`
- **Title** — short name for **one testable outcome** after the colon
- **Description** — durable product language (what the product must do), not
  how the team will build it
- **Checks** — verifiable facets of that **single** outcome under `### Checks`
  as `- [ ] …` items

### One requirement = one testable outcome

A requirement is **one falsifiable product claim**—user-facing or not (UI
behavior, API contract, CLI exit code, validation rule). It is **not** a feature,
deliverable, page, or product area.

- **Checks** support the same outcome from different angles—they are not a
  backlog of unrelated behaviors.
- **Themes** group related requirements; multiple small requirements under one
  theme is normal.
- Typical plans **Add one new requirement** (or a small set of clearly
  separate outcomes). **Modify** is uncommon.

**Check count heuristic** (also enforced as `pdlc plan validate` warnings):

| Checks | Guidance |
|--------|----------|
| 1–5 | Normal |
| 6–8 | Confirm this is still one outcome; split if not |
| 9+ | Almost certainly multiple requirements—split before merge |

Use `--strict-requirements` to treat oversized requirements as validation errors.

### Add vs Modify vs Remove

Run `pdlc spec theme list` before planning.

- **Add** — default for new work. Use when the plan introduces a **new testable
  outcome** that does not contradict existing requirements.
- **Modify** — only when **genuinely changing** an existing requirement.
- **Remove** — when the plan explicitly retires product scope.

If follow-up work adds behavior that could stand alone, **Add** a new id—do
not **Modify** a sibling requirement to absorb it.

### Choosing a theme

- Pick the **narrowest** topic that fits—never default to `general` without
  checking the catalog.
- Use `pdlc` for PDLC workflow, CLI merge, plan/spec layout, and agent tooling.
- Reserve `general` for genuinely cross-cutting product rules with no better home.
- Add a topic with `pdlc spec theme add` when none fit, then plan against it.

Write requirements so they still make sense after the plan ships—avoid
plan-local wording that will not age in the global spec.

## spec_delta.md

The delta contains **only** three sections, in this order: **Add**, **Modify**,
**Remove**. At least one must be non-empty. Do not add other top-level sections,
summaries, or backlog prose in this file.

### Add

Full requirement blocks for new ids. Each id must **not** already exist in the
active spec. Each block must include `- Theme: <topic-id>` matching `themes.toml`.
Choose the next free global numbers with `pdlc plan requirement template`.

### Modify

Full **replacement** requirement blocks for ids that already exist in the active
spec. Include `- Theme:` only when moving the requirement to another global topic.
Include the complete heading, description, and checks after the change—not a
partial diff or comment about what changed.

### Remove

Bullets only, one per line: `- RNNNN`. Each id must exist in the active spec.
Do not embed descriptions or checks in Remove.

Do not put file paths, library choices, migrations, or sprint notes in the delta.
Those belong in `tasks.md`.

## tasks.md

An ordered checklist an agent executes line by line. The file has **three
sections in this order**: `## Preconditions`, `## Tasks`, `## Verification`.

Use scaffolded templates from the plan workflow—never hand-author section
headings, group headings, or checkbox lines:

### Structure rules

- **Preconditions** — checkbox lines only (e.g. backlog item validated, plan validated)
- **Tasks** — numbered groups `### 1. Title`, `### 2. Title`, … without gaps; at
  least one task line per group
- **Verification** — checkbox lines only; each traces to acceptance criteria (backlog-linked) or spec checks (direct)

### Single-line tasks

Each implementable item is exactly one checkbox line under a group:

`- [ ] Imperative step; path or command; how to verify`

No nested bullets, no continuation lines, no paragraphs under a checkbox.

Strong task lines:

- Small enough for one focused implement pass
- Name **concrete** locations (paths, endpoints, commands) on the same line
- Include how to verify on the same line

Do not duplicate feature prose. Do not restate the spec delta—implement it.

## Quality bar

Before calling a plan ready:

- `pdlc plan coverage pdlc/spec/changes/<plan-id>/` reports `complete: true`
- `pdlc plan validate pdlc/spec/changes/<plan-id>/` exits 0
- Every **Add** id is new; every **Modify** id exists; every **Remove** id exists
- Each requirement in Add/Modify has a non-empty description and at least one check
- `spec_delta.md` has no implementation detail; `tasks.md` has enough detail to implement
- Coverage: every acceptance criteria bullet (backlog-linked) or spec delta check (direct) has a matching line under `## Verification`; no scaffold placeholders remain in `tasks.md`
- Each Add/Modify requirement is one testable outcome; check count within heuristic

## Anti-patterns

- Planning before a backlog item is validated or still a placeholder
- **Modify** to append scope without changing what an existing requirement promises
- Partial Modify blocks (missing checks or description)
- One requirement with many checks covering unrelated behaviors (split instead)
- Implementation detail in `spec_delta.md`
- Vague tasks ("implement feature", "add tests") with no path or verification
- Hand-authored `###` groups or task lines instead of scaffolded templates
- Multi-line or nested tasks under one checkbox
- Storing plans under `pdlc/epics/`
- Creating backlog items “from” a direct plan (wrong direction)
