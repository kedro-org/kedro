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
    expected = (
        f"Running '{sleeping_identity.__module__}.{sleeping_identity.__qualname__}' "
        f"consumed"
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
    expected = (
        f"Running '{sleeping_identity.__module__}.{sleeping_identity.__qualname__}' "
        f"consumed"
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
