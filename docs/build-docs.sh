#!/usr/bin/env bash

set -e

# Exit script if you try to use an uninitialized variable.
set -o nounset

action=$1

sphinx-build -ETa --keep-going -j auto -D language=en -b html -d docs/build/doctrees docs/source docs/build/html
fi
