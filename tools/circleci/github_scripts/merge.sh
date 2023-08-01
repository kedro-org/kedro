#!/usr/bin/env bash
# Script to merge a source branch into a target branch and raise a PR on conflict.

# Exit script if you try to use an uninitialized variable.
set -o nounset

# Exit script if a statement returns a non-true return value.
set -o errexit

# The git directory where this script will be invoked
GIT_DIRECTORY=$1
cd $GIT_DIRECTORY

# The source & target branches to perform the merge, i.e.
# git merge source target
SOURCE_BRANCH=$2
TARGET_BRANCH=$3
# A branch created to raise a PR in case SOURCE_BRANCH is push-protected.
PR_BRANCH="merge-${SOURCE_BRANCH}-to-${TARGET_BRANCH}"

# The Github details to raise a PR
GITHUB_TAGGING_TOKEN=$4
GITHUB_USER="kedro-org"
GITHUB_REPO="kedro"
GITHUB_ENDPOINT="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/pulls"
PAYLOAD=$(cat <<-END
{
    "title": "[AUTO-MERGE] Merge ${SOURCE_BRANCH} into ${TARGET_BRANCH} via ${PR_BRANCH}",
    "head": "${PR_BRANCH}",
    "base": "${TARGET_BRANCH}",
    "body": "A new change in ${SOURCE_BRANCH} cannot be merged into ${TARGET_BRANCH} as part of the regular sync job, hence this PR. Please resolve the conflicts manually, and make sure to obtain 2 approvals once the builds pass.\\n\\n### IMPORTANT NOTICE\\n\\nPlease let CircleCI merge this PR automatically, with merge commit enabled."
}
END
)

# Attempt to merge the source branch into the target branch after updating the target branch
# with latest changes from origin.
MERGE_STATUS=0
# We need to reconfigure origin.fetch because we originally clone with --single-branch
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch origin $TARGET_BRANCH && git checkout -b $TARGET_BRANCH "origin/${TARGET_BRANCH}"
git merge --no-edit $SOURCE_BRANCH $TARGET_BRANCH || MERGE_STATUS=1

if [ $MERGE_STATUS -eq 0 ]
then
    # If the merge was successful, attempt to push the target branch to origin.
    # We don't do any error handling here because if this fails, something really wrong is going on,
    # so let's just fail the job and debug it manually.
    echo "Successfully merged ${SOURCE_BRANCH} into ${TARGET_BRANCH}. Now pushing ${TARGET_BRANCH} to origin..."
    git push origin $TARGET_BRANCH
else
    # If the merge was not successful, i.e. there was some conflict between source branch and target branch,
    # abandon the merge and raise a PR instead.
    git merge --abort

    # Check if the PR_BRANCH already exists
    PR_BRANCH_EXIST=$(git ls-remote --heads origin $PR_BRANCH | wc -l)

    # If it doesn't exists, push and raise a PR
    if [ $PR_BRANCH_EXIST -eq 0 ]
    then
        echo "Failed to merge ${SOURCE_BRANCH} into ${TARGET_BRANCH}. Raising a pull request instead..."
        # Create a new branch from which to raise a PR, as ${SOURCE_BRANCH} might be push-protected
        git checkout -b ${PR_BRANCH} ${SOURCE_BRANCH}
        git push origin ${PR_BRANCH}
        STATUS=$(curl -X POST \
          --output /dev/null --location --silent --write-out "%{http_code}\n" --retry 3 \
          --header "Authorization: token ${GITHUB_TAGGING_TOKEN}" \
          --header "Content-Type: application/json" \
          --data "${PAYLOAD}" \
          "${GITHUB_ENDPOINT}")
        [ "${STATUS}" == "201" ]
    else
        echo "Failed to merge ${SOURCE_BRANCH} into ${TARGET_BRANCH} and it seems like another manual merge between ${SOURCE_BRANCH} and ${TARGET_BRANCH} is in progress. Doing nothing here."
    fi
fi

git checkout ${SOURCE_BRANCH}
