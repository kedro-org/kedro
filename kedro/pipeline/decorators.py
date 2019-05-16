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
"""A module containing predefined node decorators in Kedro.
"""

import logging
import time
from functools import wraps
from typing import Callable

from memory_profiler import memory_usage


def _func_full_name(func: Callable):
    if not func.__module__:
        return func.__qualname__
    return "%s.%s" % (func.__module__, func.__qualname__)


def _human_readable_time(elapsed: float):  # pragma: no cover
    mins, secs = divmod(elapsed, 60)
    hours, mins = divmod(mins, 60)

    if hours > 0:
        message = "%dh%02dm%02ds" % (hours, mins, secs)
    elif mins > 0:
        message = "%dm%02ds" % (mins, secs)
    elif secs >= 1:
        message = "%.2fs" % secs
    else:
        message = "%.0fms" % (secs * 1000.0)

    return message


def log_time(func: Callable) -> Callable:
    """A function decorator which logs the time taken for executing a function.

    Args:
        func: The function to be logged.

    Returns:
        A wrapped function, which will execute the provided function and log
        the running time.

    """

    @wraps(func)
    def with_time(*args, **kwargs):
        log = logging.getLogger(__name__)
        t_start = time.time()
        result = func(*args, **kwargs)
        t_end = time.time()
        elapsed = t_end - t_start

        log.info(
            "Running %r took %s [%.3fs]",
            _func_full_name(func),
            _human_readable_time(elapsed),
            elapsed,
        )
        return result

    return with_time


def mem_profile(func: Callable) -> Callable:
    """A function decorator which profiles the memory used when executing the
    function. The logged memory is collected by using the memory_profiler
    python module and includes memory used by children processes. The usage
    is collected by taking memory snapshots every 100ms. This decorator will
    only work with functions taking at least 0.5s to execute due to a bug in
    the memory_profiler python module. For more information about the bug,
    please see https://github.com/pythonprofilers/memory_profiler/issues/216

    Args:
        func: The function to be profiled.

    Returns:
        A wrapped function, which will execute the provided function and log
        its max memory usage upon completion.

    """

    @wraps(func)
    def with_memory(*args, **kwargs):
        log = logging.getLogger(__name__)
        mem_usage, result = memory_usage(
            (func, args, kwargs),
            interval=0.1,
            timeout=1,
            max_usage=True,
            retval=True,
            include_children=True,
        )
        log.info(
            "Running %r consumed %2.2fMiB memory at peak time",
            _func_full_name(func),
            mem_usage[0],
        )
        return result

    return with_memory
