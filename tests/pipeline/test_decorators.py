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
    [(3600.1, "1h00m00s"), (3599.0, "59m59s"), (59, "59.00s"), (0.1, "100ms")],
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
