---
name: kedro-security-review
description: >-
  Run a Kedro security scan on the full codebase or just a pull request. This
  skill always runs Semgrep first and then evaluates the findings against the
  Kedro security model. Use when the user says things like "run security scan
  on the full codebase" or "run security scan on this PR". Produce one final
  report only, in chat by default or posted to GitHub when explicitly asked.
---

# Security Scan

Before scanning, decide three things:

1. **Target source** — full codebase or PR (see `## Mode selection`)
2. **Scan scope** — Kedro framework code or a Kedro project (see `## Scan scope`)
3. **Delivery** — chat (default) or post to GitHub (see `## Delivery modes`)

Then run the numbered Workflow below:

1. detect which Semgrep binary is available (see Defaults)
2. create a temporary working directory with `mktemp -d`
3. determine what to scan — full repo or changed files from the PR
4. run Semgrep in parallel across all rulesets
5. read and deduplicate findings
6. triage and classify findings against the Kedro security model
7. run manual review checks from `reference.md`
8. emit one final report

## References

Read these before triaging findings:
- [../../../docs/about/security_model.md](../../../docs/about/security_model.md)
- [reference.md](reference.md)

## Scan scope

Before scanning, ask once:

> Are we scanning **Kedro framework code** (this repository's `kedro/`)
> or a **Kedro project** (user pipelines, catalog, and project config)?

Use the answer to pre-classify findings (see `reference.md`). For example,
`kedro-yaml-unsafe-load` in `kedro/` is `candidate_kedro_vulnerability`; the
same rule in project code is `project_developer_responsibility`.

If the user already stated the scope, do not ask again.

## Defaults

- Runtime:
  - `semgrep`
  - otherwise `uvx --from semgrep semgrep`
  - otherwise `uv tool run --from semgrep semgrep`
- Rulesets:
  - `p/security-audit`
  - `p/secrets`
  - `p/python`
  - `.agents/skills/kedro-security-review/rules/kedro-security-patterns.yml`
- Path exclusions (every Semgrep invocation):
  - `--exclude tests/`
  - `--exclude docs/`
  - `--exclude features/`
  - `--exclude .agents/`
- Temporary working directory:
  - create with `mktemp -d`
  - delete at the end unless the user explicitly asks to keep artifacts

Always use `--metrics=off`.

## Runtime note

If a `uvx` or `uv tool run` Semgrep command fails with a permissions error on a
`~/.cache/uv` path, ask the user for permission to run outside the sandbox
(i.e. with full filesystem access) and then rerun the same command. Do not
treat a cache permission failure as a real scan failure.

Later workflow steps that invoke Semgrep should refer back to this note instead
of repeating it.

## Delivery modes

### Chat mode

Default mode. Show one final report in chat and do not expose intermediate scan
output.

### Post mode

Only use when the user explicitly asks to post, submit, or publish the scan
result to GitHub.

Post mode is only valid in PR mode — it produces a GitHub PR review payload
and there is no PR to attach it to in full-codebase mode. If a user asks to
post a full-codebase scan, fall back to chat mode and tell the user why.

In post mode:
- still do all scanning and triage locally first
- construct one final GitHub review payload
- post it after the review is complete

Do not post partial results or progress updates.

## Mode selection

### Full codebase mode

Use when the user asks to scan the repo, codebase, project, or current branch
without narrowing to a PR.

Target:
- the current repo root

### PR mode

Use when the user asks to scan a PR or when the request names a PR number or
URL.

Resolve the PR from:
- the explicit PR number or URL if provided
- otherwise the current branch via `gh pr view`

Then get the changed files:

```bash
gh pr diff <number> --name-only
```

Only keep files that still exist in the working tree. Scan just those files.

If the PR has no scannable files, report that clearly and stop.

## Workflow

### 1. Resolve runtime

```bash
if command -v semgrep >/dev/null 2>&1; then
  ENGINE_LABEL="Semgrep OSS (host CLI)"
  SEMGREP_CMD=(semgrep)
elif command -v uvx >/dev/null 2>&1; then
  ENGINE_LABEL="Semgrep OSS (uvx)"
  SEMGREP_CMD=(uvx --from semgrep semgrep)
elif command -v uv >/dev/null 2>&1; then
  ENGINE_LABEL="Semgrep OSS (uv tool run)"
  SEMGREP_CMD=(uv tool run --from semgrep semgrep)
else
  echo "ERROR: neither semgrep, uvx, nor uv is available."
  exit 1
fi

SEMGREP_EXCLUDE=(
  --exclude tests/
  --exclude docs/
  --exclude features/
  --exclude .agents/
)

"${SEMGREP_CMD[@]}" --version
```

If the version check fails, apply the **Runtime note** above before treating
the scan as failed.

### 2. Resolve temporary working directory

Check whether the user explicitly asked to keep artifacts **before** emitting
the script below.

If NOT keeping artifacts:

```bash
OUTPUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/kedro-security-review.XXXXXX")"
cleanup() {
  rm -rf "$OUTPUT_DIR"
}
trap cleanup EXIT
mkdir -p "$OUTPUT_DIR/raw"
```

If keeping artifacts (omit the trap entirely):

```bash
OUTPUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/kedro-security-review.XXXXXX")"
mkdir -p "$OUTPUT_DIR/raw"
```

In that case, report `$OUTPUT_DIR` at the end of the scan so the user can
inspect it.

### 3. Resolve scan target

For full codebase mode:

```bash
SCAN_TARGETS=(.)
TARGET_LABEL="full codebase"
```

For PR mode:

```bash
PR_NUMBER="<resolved-pr-number>"

# Apply the same path exclusions as full-codebase mode.
# Semgrep's --exclude only filters during directory walk, so explicit file
# arguments would otherwise bypass the exclusion list (e.g. tests/foo.py).
EXCLUDE_PREFIXES=(tests/ docs/ features/ .agents/)

SCAN_TARGETS=()
while IFS= read -r path; do
  [ -f "$path" ] || continue
  skip=0
  for prefix in "${EXCLUDE_PREFIXES[@]}"; do
    [[ "$path" == "$prefix"* ]] && skip=1 && break
  done
  (( skip == 0 )) && SCAN_TARGETS+=("$path")
done < <(gh pr diff "$PR_NUMBER" --name-only)
TARGET_LABEL="PR #$PR_NUMBER"
```

If `SCAN_TARGETS` is empty, stop and report that there are no scannable files
(this also happens when a PR only touches excluded paths like `tests/` or
`docs/`).

### 4. Run Semgrep

Set:

```bash
LOCAL_RULESET="$(pwd)/.agents/skills/kedro-security-review/rules/kedro-security-patterns.yml"
```

Run these in parallel (each command includes `"${SEMGREP_EXCLUDE[@]}"`):

```bash
(
  "${SEMGREP_CMD[@]}" scan --metrics=off \
    "${SEMGREP_EXCLUDE[@]}" \
    --config p/security-audit \
    --json --output "$OUTPUT_DIR/raw/security-audit.json" \
    "${SCAN_TARGETS[@]}"
) &

(
  "${SEMGREP_CMD[@]}" scan --metrics=off \
    "${SEMGREP_EXCLUDE[@]}" \
    --config p/secrets \
    --json --output "$OUTPUT_DIR/raw/secrets.json" \
    "${SCAN_TARGETS[@]}"
) &

(
  "${SEMGREP_CMD[@]}" scan --metrics=off \
    "${SEMGREP_EXCLUDE[@]}" \
    --include="*.py" --config p/python \
    --json --output "$OUTPUT_DIR/raw/python.json" \
    "${SCAN_TARGETS[@]}"
) &

(
  "${SEMGREP_CMD[@]}" scan --metrics=off \
    "${SEMGREP_EXCLUDE[@]}" \
    --include="*.py" \
    --config "$LOCAL_RULESET" \
    --json --output "$OUTPUT_DIR/raw/kedro-security-patterns.json" \
    "${SCAN_TARGETS[@]}"
) &

wait
```

If one or more rulesets fail, continue with the findings from the rulesets that
did succeed. Do not abort the full scan. In the final report, include a
"Scan errors" section that lists each failed ruleset and its error message so
the user knows the scan was partial.

If a scan command fails, apply the **Runtime note** before marking that
ruleset as failed.

### 5. Read findings

Read all JSON files in `$OUTPUT_DIR/raw/` directly. Deduplicate by
`(check_id, path, start.line)` — if the same finding appears in more than one
ruleset output, count it once.

### 6. Triage against the Kedro security model

For every unique finding:
- open the flagged file and inspect the surrounding code
- classify it using [reference.md](reference.md)
- tie the reasoning back to the code-vs-data boundary in
  [../../../docs/about/security_model.md](../../../docs/about/security_model.md)
- include the **Suggested next step** from the matching bucket in `reference.md`

Use these buckets:
- `candidate_kedro_vulnerability`
- `project_developer_responsibility`
- `deployment_or_environment_issue`
- `false_positive_or_informational`
- `needs_manual_review`

### 7. Manual review checks (always run, even with zero Semgrep findings)

After triaging Semgrep output, run the **Manual review checks** from
`reference.md` against the scan target.

For each check:
- Search the scanned files for the pattern described
- If found and unmitigated, add it to the findings list with classification
  `candidate_kedro_vulnerability` or `needs_manual_review`
- If not found, the check was clean — do not itemise it

When all checks are clean, report them as a single line in the final report
rather than enumerating each one. Only expand a check when it actually
flagged something.

This step exists because Semgrep only catches known patterns. These checks
catch the class of issues that static analysis misses.

### 8. Build the final report

Do not stream intermediate findings to the user.

Accumulate findings during triage, then produce exactly one final report using
the format below.

If post mode was requested, write a single review JSON payload and post it via:

```bash
bash .agents/scripts/post_github_review.sh <review_json_file>
```

Delete the temporary review JSON file after posting.

## Reporting

Keep the report short and decisive. The classification summary already carries
the counts — do not repeat non-actionable findings as prose.

Always include:
- mode used: full codebase or PR
- scan scope: framework code or Kedro project
- target scanned
- total Semgrep findings reviewed
- counts by classification bucket
- highest Semgrep severities present

**Only itemise actionable findings** in the Findings section:
- Always: `candidate_kedro_vulnerability`, `needs_manual_review`
- When scope is **Kedro project**: also `project_developer_responsibility`
  (this is the primary actionable bucket for the project owner — include file,
  line, rule id, and suggested fix for each finding)

**Do not itemise** findings in these buckets — they are reflected in the
classification summary counts and that is sufficient:
- `false_positive_or_informational`
- `deployment_or_environment_issue`
- `project_developer_responsibility` when scope is **Kedro framework**

If the Findings section has nothing actionable, replace it with a single line
that names the non-actionable counts (e.g. "None actionable. 2 false positives
on pre-existing lines.").

For each actionable finding, include:
- file
- line
- rule id
- Semgrep severity
- Kedro classification
- one-sentence reasoning
- suggested next step (from `reference.md` for that bucket; for `candidate_kedro_vulnerability`, pick the ERROR or WARNING recommendation based on Semgrep severity)

If no findings are plausible Kedro vulnerabilities, say so explicitly.

## Output format

### Chat mode

Return one final report in this shape:

```markdown
## Kedro Security Scan
> Generated with `kedro-security-review`.

### Overview
- **Mode:** <full codebase | PR>
- **Scope:** <Kedro framework | Kedro project>
- **Target:** <repo root | PR #123>
- **Findings reviewed:** <count>
- **Highest Semgrep severities:** <list or "none">

### Classification summary
- **candidate_kedro_vulnerability:** <count>
- **needs_manual_review:** <count>
- **project_developer_responsibility:** <count>
- **deployment_or_environment_issue:** <count>
- **false_positive_or_informational:** <count>

### Findings
<For each actionable finding (candidate_kedro_vulnerability, needs_manual_review):>
- `path/to/file.py:L42` — `<classification>` — <rule id> — <reason> — <next step>

<If nothing actionable, replace the list with a single line, e.g.:>
None actionable. <count> false positives on pre-existing lines.

### Manual review checks
<If all clean, one line:>
All clean (config-dict consumers, env-var paths, path construction, security suppression comments, subprocess/eval/exec/pickle/yaml/dynamic import).

<Otherwise, only list the checks that flagged something, with reasoning.>

### Conclusion
- <short conclusion, or "No plausible Kedro vulnerabilities found.">
```

### Post mode

Write one GitHub review payload:

```json
{
  "event": "COMMENT",
  "body": "## Kedro Security Scan\n...(final summary report)...",
  "comments": [
    {
      "path": "file.py",
      "line": 42,
      "side": "RIGHT",
      "body": "**candidate_kedro_vulnerability:** <reason>\n\nRule: `<rule id>`\nSeverity: `<severity>`\nNext step: <next step>"
    }
  ]
}
```

Use inline comments only for actionable findings tied to changed PR lines:
- Always: `candidate_kedro_vulnerability`, `needs_manual_review`
- When scope is **Kedro project**: also `project_developer_responsibility`

Do not post inline comments for `false_positive_or_informational`,
`deployment_or_environment_issue`, or `project_developer_responsibility` when
scope is **Kedro framework**. Put the full summary in `body`, following the
same conciseness rules as chat mode (counts only for non-actionable buckets;
collapse clean manual review checks to one line).
