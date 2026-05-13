---
name: security-scan
description: >-
  Run a Kedro security scan on the full codebase or just a pull request. This
  skill always runs Semgrep first and then evaluates the findings against the
  Kedro security model. Use when the user says things like "run security scan
  on the full codebase" or "run security scan on this PR". Produce one final
  report only, in chat by default or posted to GitHub when explicitly asked.
allowed-tools: Bash Read Glob AskUserQuestion
---

# Security Scan

Use this as the user-facing Kedro security skill.

Two modes:
- full codebase
- PR-only

In both modes:
1. run Semgrep
2. read and deduplicate findings
3. inspect the flagged code
4. classify findings against the Kedro security model
5. emit one final report

## References

Read these before triaging findings:
- [references/kedro-security-model.md](references/kedro-security-model.md)
- [references/kedro-findings-triage.md](references/kedro-findings-triage.md)

## Defaults

- Runtime:
  - `semgrep`
  - otherwise `uvx --from semgrep semgrep`
  - otherwise `uv tool run --from semgrep semgrep`
- Rulesets:
  - `p/security-audit`
  - `p/secrets`
  - `p/python`
  - `.agents/skills/security-scan/rules/kedro-security-patterns.yml`
- Optional rulesets (run only when explicitly requested):
  - `p/owasp-top-ten` — designed for web applications; expect high noise against framework code
- Temporary working directory:
  - create with `mktemp -d`
  - delete at the end unless the user explicitly asks to keep artifacts

Always use `--metrics=off`.

## Runtime note

If a `uvx` or `uv tool run` Semgrep command fails with a permissions error on a
`~/.cache/uv` path, rerun the same command with elevated filesystem permissions
instead of treating it as a real scan failure.

## Delivery modes

### Chat mode

Default mode. Show one final report in chat and do not expose intermediate scan
output.

### Post mode

Only use when the user explicitly asks to post, submit, or publish the scan
result to GitHub.

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

"${SEMGREP_CMD[@]}" --version
```

If the selected runtime is `uvx` or `uv tool run` and the version check fails
with a permissions error involving `~/.cache/uv`, rerun that same command with
elevated filesystem permissions.

### 2. Resolve temporary working directory

Check whether the user explicitly asked to keep artifacts **before** emitting
the script below.

If NOT keeping artifacts:

```bash
OUTPUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/kedro-security-scan.XXXXXX")"
cleanup() {
  rm -rf "$OUTPUT_DIR"
}
trap cleanup EXIT
mkdir -p "$OUTPUT_DIR/raw"
```

If keeping artifacts (omit the trap entirely):

```bash
OUTPUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/kedro-security-scan.XXXXXX")"
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
SCAN_TARGETS=()
while IFS= read -r f; do
  SCAN_TARGETS+=("$f")
done < <(gh pr diff "$PR_NUMBER" --name-only | while read -r path; do
  [ -f "$path" ] && printf '%s\n' "$path"
done)
TARGET_LABEL="PR #$PR_NUMBER"
```

If `SCAN_TARGETS` is empty, stop and report that there are no scannable files.

### 4. Run Semgrep

Set:

```bash
LOCAL_RULESET="$(pwd)/.agents/skills/security-scan/rules/kedro-security-patterns.yml"
```

Run these in parallel:

```bash
(
  "${SEMGREP_CMD[@]}" scan --metrics=off \
    --config p/security-audit \
    --json --output "$OUTPUT_DIR/raw/security-audit.json" \
    "${SCAN_TARGETS[@]}"
) &

(
  "${SEMGREP_CMD[@]}" scan --metrics=off \
    --config p/secrets \
    --json --output "$OUTPUT_DIR/raw/secrets.json" \
    "${SCAN_TARGETS[@]}"
) &

(
  "${SEMGREP_CMD[@]}" scan --metrics=off \
    --include="*.py" --config p/python \
    --json --output "$OUTPUT_DIR/raw/python.json" \
    "${SCAN_TARGETS[@]}"
) &

(
  "${SEMGREP_CMD[@]}" scan --metrics=off \
    --include="*.py" \
    --config "$LOCAL_RULESET" \
    --json --output "$OUTPUT_DIR/raw/kedro-security-patterns.json" \
    "${SCAN_TARGETS[@]}"
) &

wait
```

If one scan fails, report it instead of pretending the full scan succeeded.

If a scan command using `uvx` or `uv tool run` fails because of a permissions
error on `~/.cache/uv`, rerun that same scan command with elevated filesystem
permissions before marking the scan as failed.

### 5. Read findings

Read all JSON files in `$OUTPUT_DIR/raw/` directly. Deduplicate by
`(check_id, path, start.line)` — if the same finding appears in more than one
ruleset output, count it once.

### 6. Triage against the Kedro security model

For every unique finding:
- open the flagged file and inspect the surrounding code
- classify it using [references/kedro-findings-triage.md](references/kedro-findings-triage.md)
- tie the reasoning back to the code-vs-data boundary in
  [references/kedro-security-model.md](references/kedro-security-model.md)

Use these buckets:
- `candidate_kedro_vulnerability`
- `project_developer_responsibility`
- `deployment_or_environment_issue`
- `false_positive_or_informational`
- `needs_manual_review`

### 7. Build the final report

Do not stream intermediate findings to the user.

Accumulate findings during triage, then produce exactly one final report using
the format below.

If post mode was requested, write a single review JSON payload and post it via:

```bash
bash .agents/scripts/post_github_review.sh <review_json_file>
```

Delete the temporary review JSON file after posting.

## Reporting

Keep the report short and decisive.

Always include:
- mode used: full codebase or PR
- target scanned
- total Semgrep findings reviewed
- counts by classification bucket
- highest Semgrep severities present

For each finding, include:
- file
- line
- rule id
- Semgrep severity
- Kedro classification
- one-sentence reasoning
- suggested next step

If no findings are plausible Kedro vulnerabilities, say so explicitly.

## Output format

### Chat mode

Return one final report in this shape:

```markdown
## Kedro Security Scan
> Generated with `security-scan`.

### Overview
- **Mode:** <full codebase | PR>
- **Target:** <repo root | PR #123>
- **Findings reviewed:** <count>
- **Highest Semgrep severities:** <list or "none">

### Classification summary
- **candidate_kedro_vulnerability:** <count>
- **project_developer_responsibility:** <count>
- **deployment_or_environment_issue:** <count>
- **false_positive_or_informational:** <count>
- **needs_manual_review:** <count>

### Findings
- `path/to/file.py:L42` — `<classification>` — <rule id> — <reason> — <next step>

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
      "body": "**candidate_kedro_vulnerability:** <reason>\\n\\nRule: `<rule id>`\\nSeverity: `<severity>`\\nNext step: <next step>"
    }
  ]
}
```

Use inline comments only for concrete findings tied to changed PR lines. Put the
full summary in `body`.
