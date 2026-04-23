#!/usr/bin/env bash
set -euo pipefail

# Posts a review summary as a top-level PR comment.
# Usage: bash post_review.sh <review_file>

review_file="${1:-}"

if [[ -z "$review_file" ]]; then
    echo "Error: No review file provided."
    echo "Usage: bash post_review.sh <review_file>"
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

pr_number=$(gh pr view --json number -q .number 2>/dev/null || true)

if [[ -z "$pr_number" ]]; then
    echo "Error: No PR found for the current branch."
    echo "Make sure you're on a branch with an open PR."
    exit 1
fi

echo "Posting review to PR #${pr_number}..."

if gh pr comment "$pr_number" --body-file "$review_file"; then
    pr_url=$(gh pr view "$pr_number" --json url -q .url)
    echo "Review posted: ${pr_url}"
else
    echo "Error: Failed to post the review comment."
    exit 1
fi
