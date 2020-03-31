#!/usr/bin/env bash

# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

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
eval_command PYLINT "python -m pylint --version"
eval_command PYTEST "python -m pytest --version"
eval_command BLACK "python -m black --version"
eval_command BEHAVE "python -m behave --version"
eval_command MYPY "python -m mypy --version"
eval_command FLAKE8 "python -m flake8 --version"
eval_command ISORT "python -m isort --version"
eval_command PRE-COMMIT "python -m pre_commit --version"
eval_command SPARK "python -c \\
  \"import pyspark; print(f'PySpark: {pyspark.__version__}')\" 2>/dev/null && \\
  spark-submit --version || echo \"Spark not found\""
eval_command SPHINX "python -m sphinx --version 2>/dev/null || echo \"Sphinx not found\""
eval_command KEDRO "python -m kedro info 2>/dev/null || echo \"Kedro not found\""
