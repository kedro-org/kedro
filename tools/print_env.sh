#!/usr/bin/env bash

set -e

print_sep="=============================="

eval_command() {
    local title="$1"
    local command="$2"

    echo "$print_sep $title $print_sep"
    eval "$command"
    echo
}

eval_command CONDA "conda info 2>/dev/null || echo \"Conda not found\""
eval_command PYTHON "which python && python -V"
eval_command PIP "python -m pip -V"
eval_command PYTEST "python -m pytest --version"
eval_command RUFF "ruff --version"
eval_command BEHAVE "python -m behave --version"
eval_command PRE-COMMIT "python -m pre_commit --version"
eval_command SPARK "python -c \\
  \"import pyspark; print(f'PySpark: {pyspark.__version__}')\" 2>/dev/null && \\
  spark-submit --version || echo \"Spark not found\""
eval_command SPHINX "python -m sphinx --version 2>/dev/null || echo \"Sphinx not found\""
eval_command KEDRO "python -m kedro info 2>/dev/null || echo \"Kedro not found\""
