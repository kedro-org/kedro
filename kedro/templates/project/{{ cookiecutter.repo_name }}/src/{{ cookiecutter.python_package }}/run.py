# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""Application entry point."""
from pathlib import Path

from kedro.framework.context import load_context
from kedro.framework.project import _generate_toml_config


def run_package():
    # Entry point for running a Kedro project packaged with `kedro package`
    # using `python -m <project_package>.run` command.
    package_path = Path(__file__).resolve().parent
    project_path = Path.cwd()

    # All the metadata that is required to instantiate KedroContext
    # is located in `pyproject.toml`. When running the Kedro project in package
    # mode `pyproject.toml` with all the required values needs to exist in
    # the current directory. `_generate_toml_config()` is used to create the toml
    # file with all the values derived from the packaged project.
    _generate_toml_config(project_path, package_path)

    project_context = load_context(project_path, skip_validation=True)
    project_context.run()


if __name__ == "__main__":
    run_package()
