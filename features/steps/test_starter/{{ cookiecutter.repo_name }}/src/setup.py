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

from setuptools import find_packages, setup

entry_point = (
    "{{ cookiecutter.repo_name }} = {{ cookiecutter.python_package }}.run:run_package"
)


# get the dependencies and installs
with open("requirements.txt", "r", encoding="utf-8") as f:
    # Make sure we strip all comments and options (e.g "--extra-index-url")
    # that arise from a modified pip.conf file that configure global options
    # when running kedro build-reqs
    requires = []
    for line in f:
        req = line.split("#", 1)[0].strip()
        if req and not req.startswith("--"):
            requires.append(req)

setup(
    name="{{ cookiecutter.python_package }}",
    version="0.1",
    packages=find_packages(exclude=["tests"]),
    entry_points={"console_scripts": [entry_point]},
    install_requires=requires,
    extras_require={
        "docs": [
            "sphinx>=1.6.3, <2.0",
            "sphinx_rtd_theme==0.4.1",
            "docutils",
            "nbsphinx==0.3.4",
            "nbstripout==0.3.3",
            "recommonmark==0.5.0",
            "sphinx-autodoc-typehints==1.6.0",
            "sphinx_copybutton==0.2.5",
            "jupyter_client>=5.1.0, <7.0",
            "tornado~=6.1",
            "ipykernel~=5.3",
        ]
    },
)
