#!/usr/bin/env bash
# run_local_checks.sh — orchestrate local equivalents of CI checks.
#
# Reuses Make targets where possible. Each section prints
#   >>> <check name> (CI equivalent: <workflow>)
# so failures cross-reference the GitHub Actions workflow that catches them.
#
# Scope is auto-detected from `git diff <base>...HEAD` unless overridden.
# e2e-tests are intentionally NOT runnable through this script — they're slow,
# require packaging the wheel, and are out of scope for the local babysit loop.
# To debug an e2e failure, inspect the CI logs directly.
#
# Usage:
#   bash run_local_checks.sh                 # auto-detect scope from `git diff`
#                                            # (one of: code, docs, code+docs)
#   bash run_local_checks.sh --code          # lint + test + detect-secrets
#   bash run_local_checks.sh --docs          # lint + linkcheck + language-lint
#   bash run_local_checks.sh --skip-slow     # drop test/linkcheck (fast loop)
#   bash run_local_checks.sh --base <branch> # base branch for auto-detect
#
# Note: there is no flag for the mixed `code+docs` scope — it's only reachable
# via auto-detect when the diff touches both code and docs files.
#
# Environment guard:
#   Refuses to run unless an isolated venv or non-base conda env is active
#   (exit 64). Run scripts/bootstrap_env.sh first.
#
# Exit codes:
#   0     all (non-skipped) checks passed
#   1-63  count of FAILed checks (capped)
#   64    env guard refused (no isolated env active) or bad CLI args

set -uo pipefail

# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------
SCOPE=""           # "code" | "docs" | "code+docs" | "" (auto)
SKIP_SLOW=0
BASE_REF=""        # explicit --base; else auto-detect

while [[ $# -gt 0 ]]; do
    case "$1" in
        --code)       SCOPE="code"; shift ;;
        --docs)       SCOPE="docs"; shift ;;
        --skip-slow)  SKIP_SLOW=1; shift ;;
        --base)       BASE_REF="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,/^set -uo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Error: unknown argument: $1" >&2
            echo "Run with --help for usage." >&2
            exit 64
            ;;
    esac
done

# --------------------------------------------------------------------------
# Env guard — first action, refuses on system Python or conda 'base'.
# --------------------------------------------------------------------------
ISOLATED=0
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    ISOLATED=1
elif [[ -n "${CONDA_PREFIX:-}" && "${CONDA_DEFAULT_ENV:-}" != "base" && -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    ISOLATED=1
fi

if [[ $ISOLATED -eq 0 ]]; then
    echo "Error: no isolated Python environment active." >&2
    echo "  Run scripts/bootstrap_env.sh first to create or describe an env." >&2
    echo "  (refusing to run checks against system Python or conda 'base')." >&2
    exit 64
fi

# --------------------------------------------------------------------------
# Repo root + base ref
# --------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" ]]; then
    echo "Error: not inside a git repository" >&2
    exit 64
fi
cd "$REPO_ROOT"

resolve_base_ref() {
    if [[ -n "$BASE_REF" ]]; then
        echo "$BASE_REF"
        return
    fi
    # Try gh first (gives the PR's actual base)
    if command -v gh >/dev/null 2>&1; then
        local b
        b="$(gh pr view --json baseRefName -q .baseRefName 2>/dev/null || true)"
        if [[ -n "$b" ]]; then
            echo "origin/$b"
            return
        fi
    fi
    # Fallback: origin/main if it exists, else main
    if git rev-parse --verify --quiet origin/main >/dev/null; then
        echo "origin/main"
    else
        echo "main"
    fi
}

# --------------------------------------------------------------------------
# Scope auto-detection
# --------------------------------------------------------------------------
auto_detect_scope() {
    local base
    base="$(resolve_base_ref)"
    local files
    files="$(git diff --name-only "$base"...HEAD 2>/dev/null || true)"
    if [[ -z "$files" ]]; then
        # No diff resolvable (detached HEAD, no upstream, etc.) — default to code.
        echo "code"
        return
    fi
    local has_code=0 has_docs=0
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        case "$f" in
            kedro/*|tests/*|features/*) has_code=1 ;;
            docs/*|*.md)                has_docs=1 ;;
        esac
    done <<< "$files"
    if [[ $has_code -eq 1 && $has_docs -eq 1 ]]; then
        # Mixed PR: CI runs both all-checks.yml AND docs-only-checks.yml; mirror that.
        echo "code+docs"
    elif [[ $has_docs -eq 1 ]]; then
        echo "docs"
    else
        echo "code"
    fi
}

if [[ -z "$SCOPE" ]]; then
    SCOPE="$(auto_detect_scope)"
    echo "Auto-detected scope: $SCOPE  (override with --code / --docs)"
fi

# --------------------------------------------------------------------------
# Resolve check set from scope + modifiers
# --------------------------------------------------------------------------
RUN_LINT=0
RUN_TEST=0
RUN_DETECT_SECRETS=0
RUN_LINKCHECK=0
RUN_LANGUAGE_LINT=0

case "$SCOPE" in
    code)
        RUN_LINT=1; RUN_TEST=1; RUN_DETECT_SECRETS=1
        ;;
    docs)
        RUN_LINT=1; RUN_LINKCHECK=1; RUN_LANGUAGE_LINT=1
        ;;
    code+docs)
        RUN_LINT=1; RUN_TEST=1; RUN_DETECT_SECRETS=1
        RUN_LINKCHECK=1; RUN_LANGUAGE_LINT=1
        ;;
    *)
        echo "Error: invalid scope: $SCOPE" >&2
        exit 64
        ;;
esac

if [[ $SKIP_SLOW -eq 1 ]]; then
    RUN_TEST=0
    RUN_LINKCHECK=0
fi

# --------------------------------------------------------------------------
# Result tracking
# --------------------------------------------------------------------------
CHECK_NAMES=()
CHECK_STATUSES=()   # PASS | FAIL | SKIP
CHECK_REASONS=()

record() {
    CHECK_NAMES+=("$1")
    CHECK_STATUSES+=("$2")
    CHECK_REASONS+=("${3:-}")
}

section() {
    echo
    echo "============================================================"
    echo ">>> $1 (CI equivalent: $2)"
    echo "============================================================"
}

# Run a check; capture pass/fail. Args: <name> <ci-workflow> <command...>
run_check() {
    local name="$1"; local wf="$2"; shift 2
    section "$name" "$wf"
    if "$@"; then
        record "$name" "PASS"
    else
        record "$name" "FAIL"
    fi
}

skip_check() {
    local name="$1"; local wf="$2"; local reason="$3"
    section "$name" "$wf"
    echo "  [SKIP] $reason"
    record "$name" "SKIP" "$reason"
}

# Wrappers for pipelines / things that need shell features
detect_secrets_full_tree() {
    git ls-files -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline
}

# --------------------------------------------------------------------------
# Run the selected checks
# --------------------------------------------------------------------------
echo
echo "Repo root : $REPO_ROOT"
echo "Scope     : $SCOPE"
echo "Modifiers : skip-slow=$SKIP_SLOW"
echo "Active env: ${VIRTUAL_ENV:-${CONDA_PREFIX:-?}}"

if [[ $RUN_LINT -eq 1 ]]; then
    run_check "make lint" "lint.yml" make lint
fi

if [[ $RUN_TEST -eq 1 ]]; then
    run_check "make test" "unit-tests.yml" make test
fi

if [[ $RUN_DETECT_SECRETS -eq 1 ]]; then
    if command -v detect-secrets-hook >/dev/null 2>&1; then
        run_check "detect-secrets (full tree)" "detect-secrets.yml" detect_secrets_full_tree
    else
        skip_check "detect-secrets (full tree)" "detect-secrets.yml" \
            "detect-secrets-hook not on PATH (run \`make install-test-requirements\`)"
    fi
fi

if [[ $RUN_LINKCHECK -eq 1 ]]; then
    if command -v lychee >/dev/null 2>&1; then
        run_check "make linkcheck" "docs-linkcheck.yml" make linkcheck
    else
        skip_check "make linkcheck" "docs-linkcheck.yml" "missing tool: lychee"
    fi
fi

if [[ $RUN_LANGUAGE_LINT -eq 1 ]]; then
    if command -v vale >/dev/null 2>&1; then
        run_check "make language-lint" "docs-language-linter.yml" make language-lint dir=docs
    else
        skip_check "make language-lint" "docs-language-linter.yml" "missing tool: vale"
    fi
fi

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
echo
echo "============================================================"
echo ">>> Summary"
echo "============================================================"

FAIL_COUNT=0
PASS_COUNT=0
SKIP_COUNT=0

for i in "${!CHECK_NAMES[@]}"; do
    status="${CHECK_STATUSES[$i]}"
    name="${CHECK_NAMES[$i]}"
    reason="${CHECK_REASONS[$i]}"
    case "$status" in
        PASS) PASS_COUNT=$((PASS_COUNT + 1)); printf "  [PASS] %s\n" "$name" ;;
        FAIL) FAIL_COUNT=$((FAIL_COUNT + 1)); printf "  [FAIL] %s\n" "$name" ;;
        SKIP) SKIP_COUNT=$((SKIP_COUNT + 1)); printf "  [SKIP] %s  (%s)\n" "$name" "$reason" ;;
    esac
done

echo
echo "  Totals: $PASS_COUNT pass, $FAIL_COUNT fail, $SKIP_COUNT skip"
echo
echo "  Note: e2e-tests are not run locally by this script. To debug an e2e CI"
echo "        failure, open the failing run via watch_ci.sh and inspect logs."

# Cap exit code at 63 — env guard reserves 64.
if [[ $FAIL_COUNT -gt 63 ]]; then
    exit 63
fi
exit "$FAIL_COUNT"
