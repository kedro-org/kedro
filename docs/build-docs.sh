#!/usr/bin/env bash

set -e

# Exit script if you try to use an uninitialized variable.
set -o nounset

action=$1

if [ "$action" == "linkcheck" ]; then
  sphinx-build -ETan -j auto -D language=en -b linkcheck -d docs/build/doctrees docs/source docs/build/linkcheck
elif [ "$action" == "docs" ]; then
  sphinx-build -ETa --keep-going -j auto -D language=en -b html -d docs/build/doctrees docs/source docs/build/html
fi
