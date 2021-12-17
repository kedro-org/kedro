#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

KEDRO_REPO=$1
ECR_IMAGE_URL=$2

get_pip_reqs() {
    local project_path=$1
    cat $project_path/*requirements.txt | grep -v requirements
}

docker_build() {
    local pip_reqs="$1"
    local py_version=$2
    local image=$ECR_IMAGE_URL:$py_version
    echo "Building docker image: $image"
    docker build -t $image \
        --build-arg PIP_REQS="$pip_reqs" \
        --build-arg PY_VERSION=$py_version \
        .
}

docker_push() {
    local py_version=$1
    local image=$ECR_IMAGE_URL:$py_version
    echo "Pushing docker image: $image"
    docker push $image
}

main() {
    local pip_reqs="$(get_pip_reqs $KEDRO_REPO)"

    # Image for python 3.6
    docker_build "$pip_reqs" 3.6
    docker_push 3.6

    # Image for python 3.7
    docker_build "$pip_reqs" 3.7
    docker_push 3.7

    # Image for python 3.8
    docker_build "$pip_reqs" 3.8
    docker_push 3.8

}

main
