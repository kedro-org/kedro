#!/usr/bin/env bash
# Check pip-audit results and generate summary.
# Parses JSON output from pip-audit and compares against severity thresholds.
# Usage: check-pip-audit.sh <report-file> <critical-threshold> <high-threshold>

# Exit script if you try to use an uninitialized variable.
set -o nounset

# Exit script if a statement returns a non-true return value.
set -o errexit

REPORT_FILE="${1:-pip-audit-report.json}"
CRITICAL_THRESHOLD="${2:-0}"
HIGH_THRESHOLD="${3:-0}"

VULN_COUNT=0
CRITICAL_COUNT=0
HIGH_COUNT=0

if [[ -f "$REPORT_FILE" ]]; then
    VULN_COUNT=$(jq '[.dependencies[] | .vulns[]] | length' "$REPORT_FILE" 2>/dev/null || echo "0")
    CRITICAL_COUNT=$(jq '[.dependencies[] | .vulns[] | select(.severity == "CRITICAL" or .severity == "critical")] | length' "$REPORT_FILE" 2>/dev/null || echo "0")
    HIGH_COUNT=$(jq '[.dependencies[] | .vulns[] | select(.severity == "HIGH" or .severity == "high")] | length' "$REPORT_FILE" 2>/dev/null || echo "0")
fi

# Output to GitHub outputs
echo "vuln_count=$VULN_COUNT" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "critical=$CRITICAL_COUNT" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "high=$HIGH_COUNT" >> "${GITHUB_OUTPUT:-/dev/stdout}"

# Generate summary
{
    echo "### :package: pip-audit Dependency Vulnerabilities"
    echo "Total vulnerabilities found: $VULN_COUNT"
    echo "- Critical: $CRITICAL_COUNT"
    echo "- High: $HIGH_COUNT"
} >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"

# Check thresholds
if [[ "$CRITICAL_COUNT" -gt "$CRITICAL_THRESHOLD" ]] || [[ "$HIGH_COUNT" -gt "$HIGH_THRESHOLD" ]]; then
    echo "blocking=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    echo "::error::pip-audit found $CRITICAL_COUNT critical and $HIGH_COUNT high severity vulnerabilities (thresholds: critical=$CRITICAL_THRESHOLD, high=$HIGH_THRESHOLD)"
    exit 1
else
    echo "blocking=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 0
fi
