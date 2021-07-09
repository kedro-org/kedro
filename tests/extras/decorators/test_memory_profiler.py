# Copyright 2021 QuantumBlack Visual Analytics Limited
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

import importlib
import logging
from time import sleep

import pytest

from kedro.extras.decorators import memory_profiler


def sleeping_identity(inp):
    sleep(0.1)
    return inp


def test_mem_profile(caplog):
    func = memory_profiler.mem_profile(sleeping_identity)
    res = func(1)

    logger_name, severity, message = caplog.record_tuples[0]
    assert res == 1
    assert logger_name == "kedro.extras.decorators.memory_profiler"
    assert severity == logging.INFO
    expected = "Running '{}.{}' consumed".format(
        sleeping_identity.__module__, sleeping_identity.__qualname__
    )
    assert expected in message


def test_mem_profile_old_versions(caplog, mocker):
    mocker.patch(
        "kedro.extras.decorators.memory_profiler.memory_usage",
        return_value=[[float(0)], 1],
    )
    func = memory_profiler.mem_profile(sleeping_identity)
    res = func(1)

    logger_name, severity, message = caplog.record_tuples[0]
    assert res == 1
    assert logger_name == "kedro.extras.decorators.memory_profiler"
    assert severity == logging.INFO
    expected = "Running '{}.{}' consumed".format(
        sleeping_identity.__module__, sleeping_identity.__qualname__
    )
    assert expected in message


def test_import_error(mocker):
    mocker.patch.dict("sys.modules", {"memory_profiler": None})
    pattern = (
        r".*`pip install kedro\[profilers\]` to get the required "
        "memory profiler dependencies"
    )
    with pytest.raises(ImportError, match=pattern):
        importlib.reload(memory_profiler)
