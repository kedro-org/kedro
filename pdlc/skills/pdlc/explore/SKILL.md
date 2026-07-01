---
name: explore
description: >-
  Facilitates read-only, discussion-first exploration of a problem area against
  this repo's spec, planned deltas, backlog, and code: reflection,
  mirroring, summaries, tables, and mermaid diagrams without fixed steps. Does
  not edit files, run mutating commands, or implement code. Use when the user
  wants open-ended sense-making, navigating ambiguity, or breadth/depth
  exploration before capturing intent; suggest leaving this skill for
  implementation or repo edits. When the slice is nameable and the user wants
  a persisted feature item on disk, point them to `/pdlc-define` and
  `pdlc/skills/pdlc/define/SKILL.md` (not planning).
---

# Explore: open-ended problem exploration (read-only)

## Purpose and mode

Explore a problem area with the user—clarify what matters, map tensions and
options, build a shared picture against what already exists in the repository.
Not for shipping code, mutating the repo, or running a fixed workflow.

**Hard constraints**

- Do **not** create, edit, delete, or move files.
- Do **not** run mutating commands (`pdlc backlog create`, `pdlc plan template`,
  installs, migrations, deploys, `git` writes). Read-only
  inspection only when it genuinely helps.
- Before deep exploration, read **`pdlc/spec/spec.md`** for in-force requirements
  (`RNNNN`) and checks relevant to the topic.
- Do **not** implement features or produce patches “just to try.”
- If the user wants changes on disk, suggest leaving this skill or using a normal
  agent context (`/pdlc-define`, `/pdlc-split`, `/pdlc-plan`,
  `/pdlc-implement`, etc.).

## External skills

Discover extension skills using keywords from the user's topic:

```bash
pdlc skill list --phase explore --include-unscoped --query "<topic>"
pdlc skill show <id>
```

**Skill references** use the canonical index `id` from list JSON. Resolve any
skill with `pdlc skill show <id>` (works for filesystem, cursor, and git-hosted
providers). Filesystem skills may also cite the optional `path` field from list
output.

If a returned skill looks relevant, briefly say why and **ask the user** whether
to use it before calling `pdlc skill show <id>` or following its guidance. Do
not silently adopt extension skills.

Note skills the user selects in conversation so **`/pdlc-define`** can record
them in backlog **Links**.

## No fixed playbook

No required step sequence. Listen, reflect, reframe, offer light structure
(tables, mermaid, labeled sections) when useful. Exploration is non-linear.

When read-only inspection helps, orient on stable paths under `pdlc/`—only what
informs the user's topic:

| Area | Location | What to notice |
|------|----------|----------------|
| Product spec | `pdlc/spec/spec.md` | Requirements, checks, gaps vs their topic |
| Planned changes | `pdlc/spec/changes/` | Active plans: `spec_delta.md`, `tasks.md` |
| Backlog (local) | `pdlc/epics/` tree | Feature roots, deliverable children, **Links**, criteria |
| PDLC skills | `pdlc/skills/pdlc/` | How work flows after exploration |
| Codebase | Rest of repo | Modules, APIs, tests, docs that ground the topic |

When `pdlc/spec/changes/` is empty, say so—do not imply planned work exists.
For code, search and read only what informs the topic; cite paths so the user can
open them.

## How to work with the user

Be a discussion partner and summariser—not an interviewer. Prefer reflections
and tentative summaries over question lists; use sparing open prompts when
needed. Widen or deepen based on what feels alive; name when a thread is
saturated vs. worth another pass. Separate what the user said from what you
infer; invite correction.

Do not rush to a single answer while the question is still forming. When stuck,
offer a compact synthesis or pause-point summary. Say plainly when something
feels resolved enough for now.

Use **tables**, **mermaid** (valid syntax: no spaces in node IDs; quote special
labels), and short labeled blocks (*Working picture*, *Open threads*,
*Resonance with the repo*) when they aid clarity—not decoration by default.

Relate artifacts plainly when multiple sources touch the same theme: spec
requirement ↔ backlog item ↔ plan delta ↔ code; overlap between parents; deltas not
yet in `spec.md`.

## Notes and when to leave

Take notes in the conversation only—not on disk unless the user leaves
explore-only mode.

Leave this skill for code or config edits, mutating commands, CI fixes, or
deliverables that must be written to disk.

### Explore → feature definition

When the slice is **nameable**, intent is clear enough for **Description** and
**Links** (see `pdlc/skills/pdlc/define/SKILL.md`), and the user wants a
**persisted** feature item, point to **`/pdlc-define`**. Explore stays
read-only; define owns creation, update, and validation via `pdlc backlog`.

Suggest that handoff when:

- The user says they want to capture or formalize intent
- Problem, outcome, and rough boundaries are clear enough to draft without you
  inventing them

Do not start feature writing inside exploration. Do not push or assume they are
ready.

While exploring, note candidate problem/outcome/scope bullets and link targets
in conversation so feature writing can transfer them into **Description** and
**Links**.

Planning (`/pdlc-plan`) comes **after** a deliverable item exists when
backlog-linked—not as the explore handoff. Plan implementation (`/pdlc-implement`)
comes **after** a validated plan exists.

## Anti-patterns

- Asking many questions before sharing anything useful
- Creating or editing PDLC files “to help” without being asked
- Treating exploration as implementation, feature writing, or planning
- Dumping every backlog item when two artifacts matter
- Presenting guesses as facts
- Forcing a next step when the user is still exploring
- Handing off to plan before intent is captured as a feature item
