#!/usr/bin/env bash
# Script to copy kedro-datasets to kedro.datasets before the documentation build for Kedro in ReadTheDocs.

# Exit script if you try to use an uninitialized variable.
set -o nounset

# Exit script if a statement returns a non-true return value.
set -o errexit

pip install --no-deps -t kedro/to_delete kedro-datasets
mv kedro/to_delete/kedro_datasets kedro/datasets
rm -r kedro/to_delete
