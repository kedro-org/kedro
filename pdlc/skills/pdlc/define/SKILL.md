---
name: define
description: >-
  Guidance for writing clear feature backlog items (root scope). Use when drafting
  or improving **Description** and **Links** on a feature-profile item.
---

# Feature definition

A **feature** backlog item captures intent before planning or delivery: enough context to estimate, prioritize, and break into deliverable children later. You own the prose in **Description** and **Links**.

## External skills

Discover extension skills using keywords from the feature topic:

```bash
pdlc skill list --phase define --include-unscoped --query "<topic>"
pdlc skill show <id>
```

**Skill references** use the canonical index `id` from list JSON. Resolve any
skill with `pdlc skill show <id>` (works for filesystem, cursor, and git-hosted
providers). Filesystem skills may also cite the optional `path` field from list
output.

If a returned skill looks relevant, briefly say why and **ask the user** whether
to use it before calling `pdlc skill show <id>` or following its guidance. Do
not silently adopt extension skills.

When the user selects an extension skill, add a **Links** entry that resolves
with `pdlc skill show <id>`, for example:

- Extension skill: `repo/docs_writing` (`pdlc skill show repo/docs_writing`)

## What belongs in a feature

- **What and why** — problem, desired outcome, boundaries, and how we will know it worked.
- **Not how** — no sprint tasks, file-level implementation plans, or acceptance-test checklists (those belong in deliverables).

## Writing **Description**

A strong description answers in plain language:

### Problem

What pain or opportunity exists today? Who feels it?

### Outcome

What changes for users or the business when this is done?

### Scope

What is in? What is explicitly out? Mention implementation only when it is a real constraint (platform, compliance, hard dependency).

### Done

How will we know this succeeded? Use observable signals, not a task list.

Stay concise. A reader who missed the conversation should still understand intent and boundaries.

## Writing **Links**

Point to anything that reduces ambiguity:

- Related features, tickets, or prior attempts
- Designs, spikes, ADRs, or docs
- Code or APIs that anchor the problem

Prefer stable URLs and repo paths. If an artifact does not exist yet, say what will be created and why it matters.

## Quality bar

Before calling a feature ready to split or plan from:

- Intent is obvious without follow-up questions.
- Scope is small enough to estimate; if not, suggest splitting into separate features.
- **Out** is as clear as **In** — surprises come from silent assumptions.
- **Links** support specific claims in **Description**, not filler.
- Language is specific: vague words like “improve”, “better”, or “support” name what changes for whom.

## Anti-patterns

- Empty or placeholder sections
- A task dump disguised as a feature (move execution detail to deliverables)
- Scope creep hidden as a single bullet (“also refactor X”)
- Links that do not relate to anything in **Description**
- Success criteria that cannot be observed or verified
