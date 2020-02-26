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
This module contains the retry decorator, which can be used as
``Node`` decorators to retry nodes. See ``kedro.pipeline.node.decorate``
"""

import logging
from functools import wraps
from time import sleep
from typing import Callable, Type
from warnings import warn

warn(
    "`kedro.contrib.decorators.retry` will be deprecated in future releases. "
    "Please refer to replacement decorator in kedro.extras.decorators.",
    DeprecationWarning,
)


def retry(
    exceptions: Type[Exception] = Exception, n_times: int = 1, delay_sec: float = 0
) -> Callable:
    """
    Catches exceptions from the wrapped function at most n_times and then
    bundles and propagates them.

    **Make sure your function does not mutate the arguments**

    Args:
        exceptions: The superclass of exceptions to catch.
            By default catch all exceptions.
        n_times: At most let the function fail n_times. The bundle the
            errors and propagate them. By default retry only once.
        delay_sec: Delay between failure and next retry in seconds

    Returns:
        The original function with retry functionality.

    """

    def _retry(func: Callable):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            counter = n_times
            errors = []
            while counter >= 0:
                try:
                    return func(*args, **kwargs)
                # pylint: disable=broad-except
                except exceptions as exc:
                    errors.append(exc)
                    if counter != 0:
                        sleep(delay_sec)
                counter -= 1

            if errors:
                log = logging.getLogger(__name__)
                log.error(
                    "Function `%s` failed %i times. Errors:\n", func.__name__, n_times
                )
                log.error("\n".join(str(err) for err in errors))
                log.error("Raising last exception")
                raise errors[-1]

        return _wrapper

    return _retry
