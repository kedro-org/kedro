#!/usr/bin/env bash

# Exit script if you try to use an uninitialized variable.
set -o nounset

# Exit script if a statement returns a non-true return value.
set -o errexit

PROJECT_SLUG=$1
CIRCLE_ENDPOINT="https://circleci.com/api/v2/project/${PROJECT_SLUG}/pipeline"

PAYLOAD=$(cat <<-END
{
  "branch": "${CIRCLE_BRANCH}",
  "parameters": {"release_kedro": true}
}
END
)

curl -X POST \
  --silent --show-error --fail --retry 3 \
  --output /dev/null \
  --header "Content-Type: application/json" \
  --header "Circle-Token: ${CIRCLE_RELEASE_TOKEN}" \
  --data "${PAYLOAD}" \
  "${CIRCLE_ENDPOINT}"
