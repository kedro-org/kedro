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

pip install -e ".[docs]"
pip install -r test_requirements.txt
python -m ipykernel install --user --name=kedro --display-name=Kedro

# Move some files around. We need a separate build directory, which would
# have all the files, build scripts would shuffle the files,
# we don't want that happening on the actual code locally.
# When running on ReadTheDocs, sphinx-build would run directly on the original files,
# but we don't care about the code state there.
rm -rf docs/build
mkdir docs/build/
cp -r docs/_templates docs/conf.py docs/*.svg docs/*.json  docs/build/

sphinx-build -c docs/ -WETa -j auto -D language=en docs/build/ docs/build/html

# Clean up build artefacts
rm -rf docs/build/html/_sources
rm -rf docs/build/01_introduction
rm -rf docs/build/02_get_started
rm -rf docs/build/03_tutorial
rm -rf docs/build/04_kedro_project_setup
rm -rf docs/build/05_data
rm -rf docs/build/06_nodes_and_pipelines
rm -rf docs/build/07_extend_kedro
rm -rf docs/build/08_logging
rm -rf docs/build/09_development
rm -rf docs/build/10_tools_integration
rm -rf docs/build/11_faq
rm -rf docs/build/12_resources
