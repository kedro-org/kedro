#!/usr/bin/env bash
# Script to attempt to merge an automatic PR from main to develop.

# Exit script if you try to use an uninitialized variable.
set -o nounset

# Exit script if a statement returns a non-true return value.
set -o errexit

SOURCE_BRANCH=$1
TARGET_BRANCH=$2
GITHUB_TAGGING_TOKEN=$3
GITHUB_USER="kedro-org"
GITHUB_REPO="kedro"

# Array of GitHub mergeable states that are valid to proceed with automatic PR merging.
# Adding "unstable" can be convenient, as it allows to auto-merge pull requests that
# pass just the required CI checks (whereas "clean" requires all CI checks to pass,
# regardless of whether they are required or not). More info:
# https://docs.github.com/en/graphql/reference/enums#mergestatestatus
# https://github.com/octokit/octokit.net/issues/1763
VALID_MERGEABLE_STATES=("clean" "unstable")

find_github_pr() {
  # Find a PR from source to target branch
  # Returns PR number if GitHub returned exactly one such PR
  endpoint="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/pulls?base=${TARGET_BRANCH}&head=${GITHUB_USER}:${SOURCE_BRANCH}&state=open"
  response=$(curl --silent --header "Authorization: token ${GITHUB_TAGGING_TOKEN}" "${endpoint}")
  num_open_prs=$(echo "$response" | tr '\r\n' ' ' | jq "length")
  if [ "$num_open_prs" -eq 1 ]; then
    echo "$response" | tr '\r\n' ' ' | jq ".[0].number"
  fi
}

check_pr_mergeable() {
  # Check that the given PR is in a mergeable state
  pr=$1
  endpoint="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/pulls/${pr}"
  response=$(curl --silent --header "Authorization: token ${GITHUB_TAGGING_TOKEN}" "${endpoint}")
  mergeable=$(echo "${response}" | tr '\r\n' ' ' | jq ".mergeable // false")  # default to false
  echo "PR ${pr} mergeable: ${mergeable}"
  mergeable_state=$(echo "${response}" | tr '\r\n' ' ' | jq --raw-output ".mergeable_state // \"unknown\"")
  echo "PR ${pr} mergeable_state: ${mergeable_state}"
  [ "${mergeable}" == true ] && [[ " ${VALID_MERGEABLE_STATES[@]} " =~ " ${mergeable_state} " ]]
}

toggle_merge_commits() {
  # Turns merge commits on or off for the repository
  allow_merge_commit=$1
  endpoint="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}"
  payload="{\"allow_merge_commit\": ${allow_merge_commit}}"
  status_code=$(curl -X PATCH \
    --silent \
    --header "Authorization: token ${GITHUB_TAGGING_TOKEN}" \
    --header "Content-Type: application/json" \
    --data "${payload}" \
    --output /dev/null \
    --write-out "%{http_code}\n" \
    "${endpoint}")
  [ "${status_code}" -eq 200 ]
}

delete_git_ref() {
  # Delete a reference
  git_ref=$1
  endpoint="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/git/refs/${git_ref}"
  status_code=$(curl -X DELETE \
    --silent \
    --header "Authorization: token ${GITHUB_TAGGING_TOKEN}" \
    --output /dev/null \
    --write-out "%{http_code}\n" \
    "${endpoint}")
  [ "${status_code}" -eq 204 ]
}

merge_pr() {
  # Merge a given PR using merge commit
  pr=$1
  toggle_merge_commits true
  endpoint="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/pulls/${pr}/merge"
  payload='{"merge_method": "merge"}'
  response=$(curl -X PUT \
    --silent \
    --header "Authorization: token ${GITHUB_TAGGING_TOKEN}" \
    --header "Content-Type: application/json" \
    --data "${payload}" \
    "${endpoint}")
  toggle_merge_commits false
  merged=$(echo "${response}" | tr '\r\n' ' ' | jq ".merged // false")  # default to false
  if [ "${merged}" == true ]; then
    echo "PR ${pr} successfully merged"
    delete_git_ref "heads/${SOURCE_BRANCH}"
    echo "Branch ${SOURCE_BRANCH} successfully deleted"
  else
    message=$(echo "${response}" | tr '\r\n' ' ' | jq --raw-output ".message")
    echo "PR ${pr} NOT merged. Message: ${message}"
  fi
  [ "${merged}" == true ]
}

pr_number=$(find_github_pr)

if [ -z "${pr_number}" ]; then
  echo "No PR found from ${SOURCE_BRANCH} to ${TARGET_BRANCH}"
  exit 0
fi

if check_pr_mergeable "${pr_number}"; then
  merge_pr "${pr_number}"
else
  echo "PR ${pr_number} is not in a mergeable state"
fi
