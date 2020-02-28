#!/bin/bash

set -e
set -u
set -o pipefail

IMAGE_NAME=${IMAGE_NAME:-kedro}
IMAGE_VERSION=${IMAGE_VERSION:-$(cat version.txt)}
DOCKER_FULL_TAG_NAME="${DOCKER_USER_NAME}/${IMAGE_NAME}"

time docker build \
                 -t ${DOCKER_FULL_TAG_NAME}:${IMAGE_VERSION} \
                 .
