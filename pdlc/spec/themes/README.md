# Product spec themes

Requirements live in one markdown file per id under each global topic
directory. Topic ids are listed in `themes.toml` at the spec root.

## Requirement size

Each requirement (`RNNNN`) is **one testable outcome**—not an epic, story, or
whole product area. Multiple requirements under the same theme is normal.

- Aim for **1–5 checks** per requirement; **6–8** suggests verifying the scope is
  still atomic; **9+** usually means split into more requirements.
- `pdlc plan validate` warns on large requirements; use `--strict-requirements`
  to fail validation.

## Choosing a topic

- Pick the **narrowest** topic that fits the capability.
- Use `pdlc` for PDLC workflow, CLI merge, plan/spec layout, and agent tooling—not `general`.
- Reserve `general` for genuinely cross-cutting product rules with no better home.
- Add topics with `pdlc spec theme add` before planning if none fit.
- Run `pdlc spec theme list` and `pdlc plan validate` (warnings flag vague `general` use).
