#!/usr/bin/env bash
# Check Semgrep SARIF results and generate summary.
# Parses SARIF output from Semgrep and compares against error thresholds.
# Usage: check-semgrep.sh <sarif-file> <error-threshold> <scan-type>

# Exit script if you try to use an uninitialized variable.
set -o nounset

# Exit script if a statement returns a non-true return value.
set -o errexit

SARIF_FILE="${1:-semgrep-results.sarif}"
ERROR_THRESHOLD="${2:-0}"
SCAN_TYPE="${3:-diff}"

ERROR_COUNT=0
WARNING_COUNT=0
NOTE_COUNT=0
TOTAL_COUNT=0

if [[ -f "$SARIF_FILE" ]]; then
    TOTAL_COUNT=$(jq '[.runs[].results[]] | length' "$SARIF_FILE" 2>/dev/null || echo "0")
    ERROR_COUNT=$(jq '[.runs[].results[] | select(.level == "error")] | length' "$SARIF_FILE" 2>/dev/null || echo "0")
    WARNING_COUNT=$(jq '[.runs[].results[] | select(.level == "warning")] | length' "$SARIF_FILE" 2>/dev/null || echo "0")
    NOTE_COUNT=$(jq '[.runs[].results[] | select(.level == "note")] | length' "$SARIF_FILE" 2>/dev/null || echo "0")
fi

# Output to GitHub outputs
echo "error=$ERROR_COUNT" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "warning=$WARNING_COUNT" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "note=$NOTE_COUNT" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "total=$TOTAL_COUNT" >> "${GITHUB_OUTPUT:-/dev/stdout}"

# Generate summary
{
    if [[ "$SCAN_TYPE" == "diff" ]]; then
        echo "### :mag: Semgrep SAST Results (Changed Files Only)"
        echo "_Scanned changed files: Python code, YAML configs, shell scripts_"
    else
        echo "### :mag: Semgrep Deep Scan Results (Full Repository)"
        echo "_Comprehensive scan with auto-config rulesets_"
    fi
    echo ""
    echo "| Severity | Count |"
    echo "|----------|-------|"
    echo "| Error | $ERROR_COUNT |"
    echo "| Warning | $WARNING_COUNT |"
    echo "| Note | $NOTE_COUNT |"
    echo "| **Total** | $TOTAL_COUNT |"
} >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"

# Check thresholds
if [[ "$ERROR_COUNT" -gt "$ERROR_THRESHOLD" ]]; then
    echo "blocking=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    echo "::error::Semgrep found $ERROR_COUNT error-level findings (threshold: $ERROR_THRESHOLD)"
    exit 1
else
    echo "blocking=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 0
fi
