#!/usr/bin/env bash
# Script to trigger the documentation build for Kedro in ReadTheDocs.

# Exit script if you try to use an uninitialized variable.
set -o nounset

# Exit script if a statement returns a non-true return value.
set -o errexit

RTD_TOKEN=$1
BUILD_VERSION=$2  # version of the docs to be built
RTD_ENDPOINT="https://readthedocs.org/api/v3/projects/kedro/versions/${BUILD_VERSION}/builds/"

curl -X POST \
  --silent --show-error --fail --retry 3 \
  --header "Authorization: token ${RTD_TOKEN}" \
  --header "Content-Length: 0" \
  "${RTD_ENDPOINT}"
