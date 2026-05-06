#!/usr/bin/env bash
# watch_ci.sh — poll GitHub CI for the current PR and dump failed-job logs.
#
# Workflow:
#   1. Preflight: `gh` installed + authenticated (else exit 64).
#   2. Resolve PR (from current branch or --pr arg).
#   3. Watch via `gh pr checks --watch --interval <s>` until all checks complete
#      (skipped if --no-wait is given — useful when CI is still running and you
#      just want to see what's failed so far).
#   4. Fetch the final structured state.
#   5. For each failed check: extract the run ID from the GitHub Actions URL,
#      annotate with the local Make target, dump the failed-step logs (deduped
#      per run, tail -n <N>).
#
# Usage:
#   bash watch_ci.sh                          # current branch's PR; block until done
#   bash watch_ci.sh --pr 1234                # explicit PR
#   bash watch_ci.sh --pr https://github.com/kedro-org/kedro/pull/1234
#   bash watch_ci.sh --interval 60 --tail 100 # slower poll, shorter log dump
#   bash watch_ci.sh --no-wait                # snapshot mode: skip --watch,
#                                             # fetch current state + dump logs
#                                             # for any already-failed checks
#
# Exit codes:
#   0     all checks passed (or, with --no-wait, no failures so far)
#   1-63  count of FAILED checks (capped)
#   64    preflight failure (gh missing / not authenticated / no PR)

set -uo pipefail

# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------
PR=""
INTERVAL=30   # plan default; gh's own default is 10
TAIL=200      # log lines per failed run
NO_WAIT=0     # --no-wait: snapshot mode (skip the blocking --watch call)

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr)        PR="$2"; shift 2 ;;
        --interval)  INTERVAL="$2"; shift 2 ;;
        --tail)      TAIL="$2"; shift 2 ;;
        --no-wait)   NO_WAIT=1; shift ;;
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
# Preflight: gh installed + authenticated
# --------------------------------------------------------------------------
if ! command -v gh >/dev/null 2>&1; then
    echo "Error: gh not installed. See https://github.com/cli/cli#installation" >&2
    exit 64
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "Error: gh not authenticated. Run: gh auth login" >&2
    exit 64
fi

# --------------------------------------------------------------------------
# Resolve PR
# --------------------------------------------------------------------------
if [[ -n "$PR" ]]; then
    PR_FIELDS="$(gh pr view "$PR" --json number,headRefName,baseRefName,url \
        -q '"\(.number)\t\(.headRefName)\t\(.baseRefName)\t\(.url)"' 2>/dev/null || true)"
else
    PR_FIELDS="$(gh pr view --json number,headRefName,baseRefName,url \
        -q '"\(.number)\t\(.headRefName)\t\(.baseRefName)\t\(.url)"' 2>/dev/null || true)"
fi

if [[ -z "$PR_FIELDS" ]]; then
    echo "Error: could not resolve a PR." >&2
    echo "  Ensure the current branch has an open PR, or pass --pr <number-or-url>." >&2
    exit 64
fi

IFS=$'\t' read -r PR_NUMBER HEAD_REF BASE_REF PR_URL <<< "$PR_FIELDS"

echo "PR     : #$PR_NUMBER"
echo "Branch : $HEAD_REF (base: $BASE_REF)"
echo "URL    : $PR_URL"
if [[ $NO_WAIT -eq 1 ]]; then
    echo "Mode   : snapshot (--no-wait); log tail=${TAIL} lines"
else
    echo "Watch  : interval=${INTERVAL}s, log tail=${TAIL} lines"
fi
echo

# --------------------------------------------------------------------------
# Map a check name to its local equivalent (CI-to-local mapping in reference.md)
# --------------------------------------------------------------------------
map_check_to_local() {
    local name="$1"
    case "$name" in
        *lint-imports*|*Import\ Linter*) echo "make lint  (import-linter contract — see reference.md)" ;;
        *mypy*)                          echo "make lint  (mypy)" ;;
        lint*|*\ /\ lint*)               echo "make lint" ;;
        unit-tests*|*\ /\ unit-tests*)   echo "make test" ;;
        e2e-tests*|*\ /\ e2e-tests*)     echo "make e2e-tests" ;;
        detect-secrets*)                 echo "git ls-files -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline" ;;
        docs-linkcheck*|*linkcheck*)     echo "make linkcheck  (requires lychee)" ;;
        docs-language-linter*|*vale*)    echo "make language-lint dir=docs  (non-blocking)" ;;
        merge-gatekeeper*)               echo "n/a  (aggregator — turns green when all required checks pass)" ;;
        pipeline-performance-test*)      echo "n/a  (timing only — investigate manually)" ;;
        DCO*|dco*)                       echo "git rebase $BASE_REF --signoff && git push --force-with-lease  (see reference.md DCO recipes)" ;;
        *)                               echo "(no local mapping — see reference.md \"CI-to-local mapping\")" ;;
    esac
}

# Extract the GitHub Actions run ID from a check.link URL.
# Format: .../actions/runs/<run_id>[/job/<job_id>]
extract_run_id() {
    local url="$1"
    [[ -z "$url" ]] && { echo ""; return; }
    echo "$url" | grep -oE 'actions/runs/[0-9]+' | head -1 | grep -oE '[0-9]+$'
}

# --------------------------------------------------------------------------
# Watch CI (skipped in snapshot mode)
# --------------------------------------------------------------------------
if [[ $NO_WAIT -eq 1 ]]; then
    echo "Snapshot mode: skipping --watch; reading current CI state."
    echo
else
    echo "Watching CI (Ctrl-C to stop)..."
    echo

    # `gh pr checks --watch` blocks until all checks complete. It exits non-zero
    # if any failed; we capture but don't propagate yet — we want to dump logs first.
    gh pr checks "$PR_NUMBER" --watch --interval "$INTERVAL" || true
fi

# --------------------------------------------------------------------------
# Final state
# --------------------------------------------------------------------------
echo
echo "============================================================"
echo ">>> Final CI state for PR #$PR_NUMBER"
echo "============================================================"

# Pull the structured state. Tab-separated for stable parsing.
CHECKS_TSV="$(gh pr checks "$PR_NUMBER" --json name,bucket,workflow,link \
    -q '.[] | "\(.bucket)\t\(.name)\t\(.workflow)\t\(.link)"' 2>/dev/null || true)"

if [[ -z "$CHECKS_TSV" ]]; then
    echo "Error: could not fetch final CI state." >&2
    exit 64
fi

# Tally + collect failures.
PASS_COUNT=0
FAIL_COUNT=0
PENDING_COUNT=0
SKIP_COUNT=0
CANCEL_COUNT=0
FAILED_LINES=()

while IFS=$'\t' read -r bucket name workflow link; do
    [[ -z "$bucket" ]] && continue
    case "$bucket" in
        pass)     PASS_COUNT=$((PASS_COUNT + 1)) ;;
        fail)
            FAIL_COUNT=$((FAIL_COUNT + 1))
            FAILED_LINES+=("$name"$'\t'"$workflow"$'\t'"$link")
            ;;
        pending)  PENDING_COUNT=$((PENDING_COUNT + 1)) ;;
        skipping) SKIP_COUNT=$((SKIP_COUNT + 1)) ;;
        cancel)   CANCEL_COUNT=$((CANCEL_COUNT + 1)) ;;
    esac
done <<< "$CHECKS_TSV"

echo "  pass=$PASS_COUNT  fail=$FAIL_COUNT  pending=$PENDING_COUNT  skipping=$SKIP_COUNT  cancel=$CANCEL_COUNT"

if [[ $FAIL_COUNT -eq 0 ]]; then
    echo
    echo "All non-pending checks passed."
    if [[ $PENDING_COUNT -gt 0 ]]; then
        if [[ $NO_WAIT -eq 1 ]]; then
            echo "Note: $PENDING_COUNT check(s) still pending; re-run without --no-wait to block until done."
        else
            echo "Note: $PENDING_COUNT check(s) still pending (re-run watch_ci.sh to wait again)."
        fi
    fi
    exit 0
fi

# --------------------------------------------------------------------------
# Per-failure annotation + log dump (deduped per run ID)
# --------------------------------------------------------------------------
echo
echo "============================================================"
echo ">>> Failed checks (annotated with local Make target)"
echo "============================================================"

# Portable dedup (bash 3.2 on macOS lacks `declare -A`): space-padded list.
SEEN_RUNS=" "

for line in "${FAILED_LINES[@]}"; do
    IFS=$'\t' read -r name workflow link <<< "$line"
    run_id="$(extract_run_id "$link")"
    local_cmd="$(map_check_to_local "$name")"

    echo
    echo "--- FAILED: $name"
    echo "    Workflow : $workflow"
    echo "    Local fix: $local_cmd"
    echo "    Link     : $link"

    if [[ -z "$run_id" ]]; then
        echo "    (could not extract run ID from link; open URL above for logs)"
        continue
    fi

    if [[ "$SEEN_RUNS" == *" $run_id "* ]]; then
        echo "    (logs already shown for run #$run_id above)"
        continue
    fi
    SEEN_RUNS="$SEEN_RUNS$run_id "

    logs="$(gh run view "$run_id" --log-failed 2>/dev/null | tail -n "$TAIL" || true)"
    if [[ -z "$logs" ]]; then
        echo "    Logs     : (no failed-step logs — run may still be uploading,"
        echo "               or failure occurred outside a step; open the link above)"
    else
        echo "    Logs (run #$run_id, last $TAIL lines):"
        echo "$logs" | sed 's/^/      /'
    fi
done

echo
echo "============================================================"
echo ">>> Summary: $FAIL_COUNT failed check(s)"
echo "============================================================"

# Cap exit at 63 — preflight reserves 64.
if [[ $FAIL_COUNT -gt 63 ]]; then
    exit 63
fi
exit "$FAIL_COUNT"
