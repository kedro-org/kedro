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

"""``Transformers`` modify the loading and saving of ``DataSets`` in a
``DataCatalog``.
"""

import logging
from typing import Any, Callable

from kedro.io import AbstractTransformer

try:
    from memory_profiler import memory_usage
except ImportError as exc:
    raise ImportError(
        f"{exc}: `pip install kedro[profilers]` to get the required "
        "memory profiler dependencies."
    ) from exc


def _normalise_mem_usage(mem_usage):
    # memory_profiler < 0.56.0 returns list instead of float
    return mem_usage[0] if isinstance(mem_usage, (list, tuple)) else mem_usage


class ProfileMemoryTransformer(AbstractTransformer):
    """ A transformer that logs the maximum memory consumption during load and save calls """

    @property
    def _logger(self):
        return logging.getLogger(self.__class__.__name__)

    def load(self, data_set_name: str, load: Callable[[], Any]) -> Any:
        mem_usage, data = memory_usage(
            (load, [], {}),
            interval=0.1,
            max_usage=True,
            retval=True,
            include_children=True,
        )
        mem_usage = _normalise_mem_usage(mem_usage)

        self._logger.info(
            "Loading %s consumed %2.2fMiB memory at peak time", data_set_name, mem_usage
        )
        return data

    def save(self, data_set_name: str, save: Callable[[Any], None], data: Any) -> None:
        mem_usage = memory_usage(
            (save, [data], {}),
            interval=0.1,
            max_usage=True,
            retval=False,
            include_children=True,
        )
        mem_usage = _normalise_mem_usage(mem_usage)

        self._logger.info(
            "Saving %s consumed %2.2fMiB memory at peak time", data_set_name, mem_usage
        )
