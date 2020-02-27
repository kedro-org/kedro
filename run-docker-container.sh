#!/bin/bash

set -e
set -u
set -o pipefail

IMAGE_NAME=${IMAGE_NAME:-kedro}
IMAGE_VERSION=${IMAGE_VERSION:-$(cat docker/version.txt)}
DOCKER_FULL_TAG_NAME="${DOCKER_USER_NAME}/${IMAGE_NAME}"

mkdir -p .cache

PYTHON_VERSION=${PYTHON_VERSION:-"3.7"}

docker run -it                                      \
           --rm                                     \
           --volume $(pwd):/home/kedro/             \
           --volume $(pwd)/.cache/:/root/.cache/    \
           ${DOCKER_FULL_TAG_NAME}:${IMAGE_VERSION} \
           /bin/bash
