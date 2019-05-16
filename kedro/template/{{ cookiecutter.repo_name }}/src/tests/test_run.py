# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
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
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module contains an example test.

Tests should be placed in ``src/tests``, in modules that mirror your
project's structure, and in files named test_*.py. They are simply functions
named ``test_*`` which test a unit of logic.

To run the tests, run ``kedro test``.
"""
from os.path import abspath, curdir, join
from pathlib import Path

import pytest
from kedro.config import ConfigLoader
from kedro.io import DataCatalog

from {{ cookiecutter.python_package }}.run import (
    CONF_ROOT,
    DEFAULT_RUN_ENV,
    create_catalog,
    get_config,
    main,
)


def test_main_wrong_cwd(mocker):
    cwd = mocker.MagicMock(name="mocked", __str__=mocker.Mock(return_value="invalid/"))
    mocker.patch.object(Path, "cwd", return_value=cwd)
    with pytest.raises(
        ValueError,
        match=r"Given configuration path either does not "
        r"exist or is not a valid directory: invalid.*",
    ):
        main()


def test_get_config():
    project_dir = abspath(curdir)
    local_env = join(project_dir, CONF_ROOT, DEFAULT_RUN_ENV)

    conf = get_config(project_dir, env=None)

    assert isinstance(conf, ConfigLoader)
    assert local_env in conf.conf_paths


def test_create_catalog():
    project_dir = abspath(curdir)
    conf = get_config(project_dir)
    catalog = create_catalog(conf)
    assert isinstance(catalog, DataCatalog)
