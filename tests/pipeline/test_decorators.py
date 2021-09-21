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

import logging
from functools import partial
from time import sleep

import pytest
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline, node
from kedro.pipeline.decorators import _human_readable_time, log_time
from kedro.runner import SequentialRunner


def sleeping_identity(inp):
    sleep(0.1)
    return inp


def identity(arg):
    return arg


@pytest.mark.parametrize(
    "elapsed,expected",
    [(3600.1, "1h00m00s"), (3599., "59m59s"), (59, "59.00s"), (0.1, "100ms")],
)
def test_human_readable_time(elapsed, expected):
    message = _human_readable_time(elapsed)
    assert message == expected


def test_log_time(caplog):
    caplog.clear()
    func = log_time(sleeping_identity)
    res = func(1)

    logger_name, severity, message = caplog.record_tuples[0]
    assert res == 1
    assert logger_name == "kedro.pipeline.decorators"
    assert severity == logging.INFO
    expected = (
        f"Running '{sleeping_identity.__module__}.{sleeping_identity.__qualname__}' "
        f"took"
    )
    assert expected in message


def test_log_time_no_module(caplog):
    """When func module is not defined, function full name is not logged."""

    def no_module(arg):
        return sleeping_identity(arg)

    no_module.__module__ = None

    caplog.clear()
    func = log_time(no_module)
    res = func(1)

    logger_name, severity, message = caplog.record_tuples[0]
    assert res == 1
    assert logger_name == "kedro.pipeline.decorators"
    assert severity == logging.INFO
    expected = f"Running {no_module.__qualname__!r} took"
    assert expected in message


def test_log_time_with_partial(recwarn):
    pipeline = Pipeline(
        [node(partial(identity, 1), None, "output", name="identity1")]
    ).decorate(log_time)
    catalog = DataCatalog({}, dict(number=1))
    result = SequentialRunner().run(pipeline, catalog)
    assert result["output"] == 1
    warning = recwarn.pop(UserWarning)
    assert (
        "The node producing outputs `['output']` is made from a "
        "`partial` function. Partial functions do not have a "
        "`__name__` attribute" in str(warning.message)
    )
