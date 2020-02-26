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
"""``Transformers`` modify the loading and saving of ``DataSets`` in a
``DataCatalog``.
"""
import logging
import time
from typing import Any, Callable
from warnings import warn

from kedro.io import AbstractTransformer

warn(
    "`kedro.contrib.io.transformers.transformers` will be deprecated in future releases. "
    "Please refer to replacement in kedro.extras.transformers.time_profiler",
    DeprecationWarning,
)


class ProfileTimeTransformer(AbstractTransformer):
    """ A transformer that logs the runtime of data set load and save calls """

    @property
    def _logger(self):
        return logging.getLogger("ProfileTimeTransformer")

    def load(self, data_set_name: str, load: Callable[[], Any]) -> Any:
        start = time.time()
        data = load()
        self._logger.info(
            "Loading %s took %0.3f seconds", data_set_name, time.time() - start
        )
        return data

    def save(self, data_set_name: str, save: Callable[[Any], None], data: Any) -> None:
        start = time.time()
        save(data)
        self._logger.info(
            "Saving %s took %0.3f seconds", data_set_name, time.time() - start
        )
