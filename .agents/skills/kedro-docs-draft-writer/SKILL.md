---
name: kedro-docs-draft-writer
description: >-
  Draft or polish Kedro documentation. Writes a first draft from source code or
  a branch, or polishes an existing draft the user provides. Follows the Kedro
  style guide, places new files in the correct docs/ path, and runs Vale before
  handing back. Use when the user says "draft docs for X", "write a how-to for
  X", "document this feature", "polish my draft", or wants to beat blank-page
  paralysis on any Kedro docs page.
---
# Kedro docs draft writer

Write a first draft of a Kedro documentation page, or polish a draft the user already has. The output is always a starting point for human review — not a finished document.

## How to invoke this skill

The user can supply any combination of:

| Input | Example |
|---|---|
| Topic only | "draft docs for the new `llm_context_node`" |
| Topic + doc type | "write a how-to for streaming nodes" |
| PR / branch context | "draft docs for the changes on this branch" |
| Nothing (infer from branch) | "draft docs" |
| **Existing draft to polish** | "polish this draft", "clean up my docs", "check my draft against the style guide" |

**If the user provides an existing draft to polish**, skip straight to [Polish mode](#polish-mode) below.

Otherwise, work out what's missing from context. Before generating anything, confirm with the user: **topic**, **doc type**, and **proposed target file path** in a single message. Don't ask three separate questions, and don't ask again in Step 3.

---

## Workflow

### 1. Identify the topic

**If the user supplied a topic**, use it directly.

**If no topic was supplied**, infer from the current branch:

```bash
DEFAULT=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||')
DEFAULT=${DEFAULT:-main}
git diff origin/${DEFAULT}...HEAD --name-only
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

Include the proposed path in the single confirmation message from Step 1. Do not ask a second time here.

---

### 4. Gather context

Read the following before drafting. This is the most important step — the draft quality depends on accurate source material.

**Always:**
- Any existing doc in the same `docs/` subdirectory that covers a similar topic. Use it as a structural model for heading hierarchy and section order. To find candidates: `ls docs/<subdir>/`.
- The relevant source files under `kedro/` for accurate class names, method signatures, parameter names, and default values. Read docstrings first — they are the primary source of truth for how a feature behaves.

**For how-tos and tutorials:**
- One existing how-to or tutorial of similar scope. Mirror its step structure and tone.

**For explanations and reference:**
- One existing explanation or reference page in the same directory.

Read multiple files in parallel where possible. Take notes on: key classes/functions, important parameters, any caveats or version constraints, and related docs pages to cross-link.

**Gap rule:** If source material is missing, ambiguous, or contradictory, do not fill the gap with plausible-sounding content. Insert a `<!-- TODO: verify — <what's unclear> -->` comment in the draft and list the gap in Step 8. Gaps are expected in a first draft; invented facts are not.

---

### 5. Draft the page

Write the draft directly. Follow the structural template from the page you found in Step 4.

Apply all style rules from [reference.md](reference.md) section "Style rules" as you write — do not draft first and fix later.

**Scope discipline:** Stay specific to the feature being documented. Don't add background context the reader didn't ask for — if broader context is needed, link to an existing explanation page instead of writing it inline. A draft that says too much about the wrong thing is harder to fix than a tight draft with gaps.

**Tone guard:** Write for a practitioner. Don't over-explain, don't state things obvious from the code, and don't soften instructions with hedges like "you might want to" or "it's worth noting that". Assume the reader is competent. Condescension and sycophancy in docs erode trust.

Required elements by doc type:

**How-to:**
- Opening sentence: one sentence stating what the reader will achieve and what prerequisite knowledge is assumed.
- Numbered steps. Each step starts with an imperative verb.
- Code blocks with language lexers (`python`, `bash`, `yaml`).
- Where the feature involves configuration, include a concrete boilerplate snippet (YAML, TOML, JSON, or HCL as appropriate) that the reader can copy and edit. Mark placeholder values clearly, e.g. `# replace with your value`.
- No explanatory tangents — link to explanation pages instead.

**Tutorial:**
- Opening "by the end of this tutorial" sentence.
- Numbered sections. Each section builds on the last.
- Complete, runnable code examples.
- Include boilerplate config files where relevant — readers should be able to copy the file and edit it, not construct it from scratch.
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

**If Vale is installed**, run it from the repo root (where `.vale.ini` lives) and fix every finding:

```bash
vale <path/to/draft.md>
```

Apply the fix rules from [reference.md](reference.md) section "Common Vale fixes". Re-run Vale after fixing until it reports zero findings. Only skip a finding if it is a false positive — tell the user why.

**If Vale is not installed**, apply the manual style checklist from [reference.md](reference.md) section "Manual style checklist" as a substitute pass, then warn the user: _"Vale is not installed — install it with `brew install vale` (macOS) or `snap install vale` (Linux) and run `vale <path>` to verify the draft."_

---

### 8. Report to the user

Tell the user:
- The path of the written file.
- What the draft covers and what it deliberately leaves out (so the user knows the scope).
- Every `<!-- TODO: verify -->` gap — list them explicitly so the user can resolve them before opening a PR.
- Any Vale findings that were judgment calls rather than mechanical fixes.
- A reminder to add the new file to the MkDocs nav in `mkdocs.yml` before the docs build will include it.

Be direct about what the draft is: a starting point. The user should read it, fill the gaps, and do a final review before it goes anywhere. Don't present it as ready to ship.

---

---

## Polish mode

Use this when the user provides an existing draft and wants it improved, not rewritten. The goal is to make their text cleaner and more consistent — not to replace their decisions about what the doc should say.

### P1. Read the draft

Read the file or text the user provides. Do not rewrite it yet.

### P2. Run Vale (or manual checklist)

Follow the same Vale / manual checklist process as Step 7 in the main workflow. Collect all findings before making changes.

### P3. Apply mechanical fixes only

Fix anything that is clearly wrong and has no judgment involved: Vale rule violations, spelling, sentence length, passive voice, banned terms (see [reference.md](reference.md) "Common Vale fixes").

**Do not:**
- Restructure sections without being asked.
- Add content that isn't already there, implied by the source code, or requested.
- Remove content because you think it's unnecessary — flag it instead.
- Make opinionated style choices beyond what the style guide requires.

### P4. Flag, don't decide

For anything that would require a decision — restructuring, missing information, ambiguous scope — add an inline comment (`<!-- SUGGESTION: … -->`) and list it in your report. Let the user decide.

### P5. Report changes

Tell the user:
- A short list of mechanical fixes applied.
- Every `<!-- SUGGESTION: … -->` item, with a one-line explanation of why you flagged it.
- Any gaps you noticed (things that seem underspecified or unverifiable against the source code).

---

## Out of scope

- Writing tutorials from scratch when the feature code doesn't exist yet — stop at Step 4 and tell the user.
- Auto-generating API reference from docstrings — use `mkdocs` for that.
- Creating PRs, posting to GitHub, or editing the MkDocs nav — the user handles those after reviewing.
- Running the full docs build (`make build-docs`) — that's `kedro-babysit`'s job.
