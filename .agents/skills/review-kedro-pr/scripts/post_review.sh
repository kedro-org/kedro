#!/usr/bin/env bash
set -euo pipefail

# Posts a full PR review (summary + inline comments) to GitHub.
# Input: a JSON file matching the GitHub "Create a review" API format.
#
# Expected JSON structure:
# {
#   "event": "COMMENT",
#   "body": "## Kedro PR Review\n...",
#   "comments": [
#     { "path": "file.py", "line": 42, "side": "RIGHT", "body": "Comment text" }
#   ]
# }
#
# Usage: bash post_review.sh <review_json_file>

review_file="${1:-}"

if [[ -z "$review_file" ]]; then
    echo "Error: No review JSON file provided."
    echo "Usage: bash post_review.sh <review_json_file>"
    exit 1
fi

if [[ ! -f "$review_file" ]]; then
    echo "Error: File not found: $review_file"
    exit 1
fi

if ! command -v gh &>/dev/null; then
    echo "Error: gh CLI is not installed."
    echo "Install it: https://cli.github.com/"
    exit 1
fi

if ! gh auth status &>/dev/null; then
    echo "Error: gh is not authenticated."
    echo "Run: gh auth login"
    exit 1
fi

repo=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)

if [[ -z "$repo" ]]; then
    echo "Error: Could not determine the repository."
    exit 1
fi

pr_number=$(gh pr view --json number -q .number 2>/dev/null || true)

if [[ -z "$pr_number" ]]; then
    echo "Error: No PR found for the current branch."
    echo "Make sure you're on a branch with an open PR."
    exit 1
fi

echo "Posting review to ${repo}#${pr_number}..."

if result=$(gh api "repos/${repo}/pulls/${pr_number}/reviews" \
    --method POST \
    --input "$review_file" \
    --jq '.html_url' 2>&1); then
    echo "Review posted: ${result}"
else
    echo "Error: Failed to post the review."
    echo "$result"
    exit 1
fi
