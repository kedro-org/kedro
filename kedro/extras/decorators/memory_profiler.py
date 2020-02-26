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

"""
This module contains function decorators for memory-profiler, which can
be used as ``Node`` decorators. See ``kedro.pipeline.node.decorate``
"""
import logging
from functools import wraps
from typing import Callable

from kedro.pipeline.decorators import _func_full_name

try:
    from memory_profiler import memory_usage
except ImportError as error:
    raise ImportError(
        "{}: `pip install kedro[memory_profiler]` to get the required "
        "memory-profiler dependencies.".format(error)
    )


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
        # memory_profiler < 0.56.0 returns list instead of float
        mem_usage = mem_usage[0] if isinstance(mem_usage, (list, tuple)) else mem_usage
        log.info(
            "Running %r consumed %2.2fMiB memory at peak time",
            _func_full_name(func),
            mem_usage,
        )
        return result

    return with_memory
