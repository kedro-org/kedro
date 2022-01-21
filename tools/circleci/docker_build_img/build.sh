#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

KEDRO_REPO=$1
ECR_IMAGE_URL=$2
PY_VERSION=$3

get_pip_reqs() {
    local project_path=$1
    cat $project_path/*requirements.txt | grep -v requirements
}

docker_build() {
    local pip_reqs="$1"
    local image=$ECR_IMAGE_URL:$PY_VERSION
    echo "Building docker image: $image"
    docker build -t $image \
        --build-arg PIP_REQS="$pip_reqs" \
        --build-arg PY_VERSION=$PY_VERSION \
        .
}

docker_push() {
    local image=$ECR_IMAGE_URL:$PY_VERSION
    echo "Pushing docker image: $image"
    docker push $image
}

main() {
    local pip_reqs="$(get_pip_reqs $KEDRO_REPO)"
    docker_build "$pip_reqs"
    docker_push
}

main
