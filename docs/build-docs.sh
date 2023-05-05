#!/usr/bin/env bash

set -e

# Exit script if you try to use an uninitialized variable.
set -o nounset

action=$1

# Reinstall kedro-datasets locally
rm -rf kedro/datasets
bash docs/kedro-datasets-docs.sh

if [ "$action" == "linkcheck" ]; then
  sphinx-build -WETan -j auto -D language=en -b linkcheck -d docs/build/doctrees docs/source docs/build/linkcheck
elif [ "$action" == "docs" ]; then
  sphinx-build -WETa -j auto -D language=en -b html -d docs/build/doctrees docs/source docs/build/html
fi
