#!/usr/bin/env bash

set -eu

GITHUB_USER=$1
GITHUB_REPO=$2
GITHUB_TAGGING_TOKEN=$3
VERSION=$4

GITHUB_ENDPOINT="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/releases"

PAYLOAD=$(cat <<-END
{
    "tag_name": "${VERSION}",
    "target_commitish": "main",
    "name": "${VERSION}",
    "body": "Release ${VERSION}",
    "draft": false,
    "prerelease": false
}
END
)

STATUS=$(curl -X POST \
  --output /dev/null --location --silent --write-out "%{http_code}\n" --retry 3 \
  --header "Authorization: token ${GITHUB_TAGGING_TOKEN}" \
  --header "Content-Type: application/json" \
  --data "${PAYLOAD}" \
  "${GITHUB_ENDPOINT}")

[ "${STATUS}" == "201" ] || [ "${STATUS}" == "422" ]
