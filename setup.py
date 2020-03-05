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

import re
from codecs import open
from glob import glob
from itertools import chain
from os import path

from setuptools import find_packages, setup

name = "kedro"
here = path.abspath(path.dirname(__file__))

# get package version
with open(path.join(here, name, "__init__.py"), encoding="utf-8") as f:
    result = re.search(r'__version__ = ["\']([^"\']+)', f.read())

    if not result:
        raise ValueError("Can't find the version in kedro/__init__.py")

    version = result.group(1)

# get the dependencies and installs
with open("requirements.txt", "r", encoding="utf-8") as f:
    requires = [x.strip() for x in f if x.strip()]

# get test dependencies and installs
with open("test_requirements.txt", "r", encoding="utf-8") as f:
    test_requires = [x.strip() for x in f if x.strip() and not x.startswith("-r")]


# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    readme = f.read()

doc_html_files = [
    name.replace("kedro/", "", 1) for name in glob("kedro/html/**/*", recursive=True)
]

template_files = []
for pattern in ["**/*", "**/.*", "**/.*/**", "**/.*/.**"]:
    template_files.extend(
        [
            name.replace("kedro/", "", 1)
            for name in glob("kedro/template/" + pattern, recursive=True)
        ]
    )

extras_require = {
    "docs": [
        "sphinx>=1.8.4, <2.0",
        "sphinx_rtd_theme==0.4.3",
        "nbsphinx==0.4.2",
        "nbstripout==0.3.3",
        "recommonmark==0.5.0",
        "sphinx-autodoc-typehints==1.6.0",
        "sphinx_copybutton==0.2.5",
        "jupyter_client>=5.1.0, <6.0",
        "tornado>=4.2, <6.0",
        "ipykernel>=4.8.1, <5.0",
    ],
    "pyspark": ["pyspark>=2.2.0, <3.0", "hdfs>=2.5.8, <3.0"],
    "notebook_templates": ["nbconvert>=5.3.1, <6.0", "nbformat>=4.4.0, <5.0"],
    "azure": [
        "azure-storage-blob>=1.1.0, <2.0",
        "azure-storage-file>=1.1.0, <2.0",
        "azure-storage-queue>=1.1.0, <2.0",
    ],
    "bioinformatics": ["biopython>=1.73, <2.0"],
    "dask": ["dask[complete]>=2.6.0, <3.0"],
    "gcs": ["gcsfs>=0.3.0, <1.0"],
    "gbq": ["pandas-gbq>=0.12.0, <1.0"],
    "matplotlib": ["matplotlib>=3.0.3, <4.0"],
    "networkx": ["networkx>=2.4, <3.0"],
    "memory_profiler": ["memory_profiler>=0.50.0, <1.0"],
}

extras_require["pandas"] = [*extras_require["azure"], *extras_require["gbq"]]
extras_require["all"] = sorted(chain.from_iterable(extras_require.values()))

setup(
    name=name,
    version=version,
    description="Kedro helps you build production-ready data and analytics pipelines",
    license="Apache Software License (Apache 2.0)",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/quantumblacklabs/kedro",
    python_requires=">=3.5, <3.8",
    packages=find_packages(exclude=["docs*", "tests*", "tools*", "features*"]),
    include_package_data=True,
    tests_require=test_requires,
    install_requires=requires,
    author="QuantumBlack Labs",
    entry_points={"console_scripts": ["kedro = kedro.cli:main"]},
    package_data={name: ["py.typed"] + template_files + doc_html_files},
    zip_safe=False,
    keywords="pipelines, machine learning, data pipelines, data science, data engineering",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    extras_require=extras_require,
)
