---
name: kedro-docs-draft-writer
description: >-
  Draft Kedro documentation for a topic, feature, or PR change. Follows the
  Kedro style guide, places the draft in the correct docs/ path, and runs Vale
  before delivery. Use when the user says "draft docs for X", "write a how-to
  for X", "document this feature", or wants to beat blank-page paralysis on any
  Kedro docs page.
---
# Kedro docs draft writer

Generate a Vale-clean first draft of a Kedro documentation page and write it to the correct `docs/` path. The goal is to give the user something concrete to edit — not a polished final doc.

## How to invoke this skill

The user can supply any combination of:

| Input | Example |
|---|---|
| Topic only | "draft docs for the new `llm_context_node`" |
| Topic + doc type | "write a how-to for streaming nodes" |
| PR / branch context | "draft docs for the changes on this branch" |
| Nothing (infer from branch) | "draft docs" |

Work out what's missing from context. Before generating anything, confirm with the user: **topic**, **doc type**, and **target file path**. One short message is enough — don't ask three separate questions.

---

## Workflow

### 1. Identify the topic

**If the user supplied a topic**, use it directly.

**If no topic was supplied**, infer from the current branch:

```bash
git diff origin/main...HEAD --name-only
gh pr view --json title,body 2>/dev/null
```

Read changed files under `kedro/` to understand what the branch adds or changes. Summarise in one sentence for the user before continuing.

---

### 2. Classify the doc type

Use the Diátaxis framework. Pick one:

| Type | Purpose | Signals |
|---|---|---|
| **How-to** | Guide a practitioner through a specific task | "How to X", task-oriented, assumes prior knowledge |
| **Tutorial** | Teach by doing — complete worked example | Sequential learning, beginner-oriented, has a "by the end" goal |
| **Explanation** | Build understanding of a concept or design decision | "What is X", "Why does Kedro do X this way", no steps |
| **Reference** | Precise, complete technical information | Config keys, CLI flags, API parameters |

If the user specified a doc type, use that. Otherwise infer from the topic. When ambiguous, ask.

---

### 3. Map to a docs/ path

Use the directory map in [reference.md](reference.md) section "Directory map" to pick the right folder. Then propose a filename:

- How-to files: `how_to_<verb>_<noun>.md` (e.g. `how_to_create_a_custom_dataset.md`)
- Tutorial files: descriptive noun phrase (e.g. `add_another_pipeline.md`)
- Explanation files: noun phrase (e.g. `pipeline_introduction.md`)
- Reference files: noun phrase (e.g. `configuration_basics.md`)

Confirm the full path with the user before writing anything.

---

### 4. Gather context

Read the following before drafting. This is the most important step — the draft quality depends on accurate source material.

**Always:**
- Any existing doc in the same `docs/` subdirectory that covers a similar topic. Use it as a structural model for heading hierarchy and section order.
- The relevant source files under `kedro/` for accurate class names, method signatures, parameter names, and default values. Do not invent API details.

**For how-tos and tutorials:**
- One existing how-to or tutorial of similar scope. Mirror its step structure and tone.

**For explanations and reference:**
- One existing explanation or reference page in the same directory.

Read multiple files in parallel where possible. Take notes on: key classes/functions, important parameters, any caveats or version constraints, and related docs pages to cross-link.

---

### 5. Draft the page

Write the draft directly. Follow the structural template from the page you found in Step 4.

Apply all style rules from [reference.md](reference.md) section "Style rules" as you write — do not draft first and fix later.

Required elements by doc type:

**How-to:**
- Opening sentence: one sentence stating what the reader will achieve and what prerequisite knowledge is assumed.
- Numbered steps. Each step starts with an imperative verb.
- Code blocks with language lexers (`python`, `bash`, `yaml`).
- No explanatory tangents — link to explanation pages instead.

**Tutorial:**
- Opening "by the end of this tutorial" sentence.
- Numbered sections. Each section builds on the last.
- Complete, runnable code examples.
- Expected output shown where relevant.

**Explanation:**
- Opening paragraph answering "what is this and why does it exist".
- No numbered steps.
- Use `##` subsections to group related ideas.
- Cross-link to the relevant how-to at the end.

**Reference:**
- Table or definition-list format for parameters/options.
- Every entry: name, type, default, description.
- No prose padding — just precise facts.

---

### 6. Write to file

Write the draft to the confirmed path using the Write tool.

---

### 7. Run Vale and fix all findings

Check whether Vale is installed:

```bash
vale --version 2>/dev/null || echo "NOT_INSTALLED"
```

**If Vale is installed**, run it and fix every finding:

```bash
vale <path/to/draft.md>
```

Apply the fix rules from [reference.md](reference.md) section "Common Vale fixes". Re-run Vale after fixing until it reports zero findings. Only skip a finding if it is a false positive — tell the user why.

**If Vale is not installed**, apply the manual style checklist from [reference.md](reference.md) section "Manual style checklist" as a substitute pass, then warn the user: _"Vale is not installed — install it with `brew install vale` (macOS) or `snap install vale` (Linux) and run `vale <path>` to verify the draft."_

---

### 8. Report to the user

Tell the user:
- The path of the written file.
- What the draft covers and what it deliberately leaves blank (so the user knows what to fill in).
- Any gaps you hit — missing API details, unclear behaviour, or things to verify against the code.
- Any Vale findings that were judgment calls rather than mechanical fixes.

---

## Out of scope

- Writing tutorials from scratch when the feature code doesn't exist yet — stop at Step 4 and tell the user.
- Auto-generating API reference from docstrings — use `mkdocs` for that.
- Creating PRs, posting to GitHub, or editing the MkDocs nav — the user handles those after reviewing.
- Running the full docs build (`make build-docs`) — that's `kedro-babysit`'s job.
