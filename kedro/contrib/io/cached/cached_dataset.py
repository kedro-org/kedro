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
This module contains ``CachedDataSet``, a dataset wrapper which caches in memory the data saved,
so that the user avoids io operations with slow storage media
"""
import logging
from typing import Any, Dict, Union
from warnings import warn

from kedro.io import AbstractDataSet, MemoryDataSet, Version
from kedro.io.core import VERSIONED_FLAG_KEY


class CachedDataSet(AbstractDataSet):
    """``CachedDataSet`` is a dataset wrapper which caches in memory the data saved,
    so that the user avoids io operations with slow storage media.

    You can also specify a ``CachedDataSet`` in catalog.yml:
    ::

        >>> test_ds:
        >>>    type: kedro.contrib.io.cached.CachedDataSet
        >>>    versioned: true
        >>>    dataset:
        >>>       type: CSVLocalDataSet
        >>>       filepath: example.csv

    Please note that if your dataset is versioned, this should be indicated in the wrapper
    class as shown above.
    """

    def __init__(self, dataset: Union[AbstractDataSet, Dict], version: Version = None):
        warn(
            "kedro.contrib.io.cached.CachedDataSet will be deprecated in future releases. "
            "Please refer to replacement dataset in kedro.io.",
            DeprecationWarning,
        )
        if isinstance(dataset, Dict):
            self._dataset = self._from_config(dataset, version)
        elif isinstance(dataset, AbstractDataSet):
            self._dataset = dataset
        else:
            raise ValueError(
                "The argument type of `dataset` should be either a dict/YAML "
                "representation of the dataset, or the actual dataset object."
            )
        self._cache = MemoryDataSet()

    def _release(self) -> None:
        self._cache.release()
        self._dataset.release()

    @staticmethod
    def _from_config(config, version):
        if VERSIONED_FLAG_KEY in config:
            raise ValueError(
                "Cached datasets should specify that they are versioned in the "
                "`CachedDataSet`, not in the wrapped dataset."
            )
        if version:
            config[VERSIONED_FLAG_KEY] = True
            return AbstractDataSet.from_config(
                "_cached", config, version.load, version.save
            )
        return AbstractDataSet.from_config("_cached", config)

    def _describe(self) -> Dict[str, Any]:
        return {
            "dataset": self._dataset._describe(),  # pylint: disable=protected-access
            "cache": self._cache._describe(),  # pylint: disable=protected-access
        }

    def _load(self):
        data = self._cache.load() if self._cache.exists() else self._dataset.load()

        if not self._cache.exists():
            self._cache.save(data)

        return data

    def _save(self, data: Any) -> None:
        self._dataset.save(data)
        self._cache.save(data)

    def _exists(self) -> bool:
        return self._cache.exists() or self._dataset.exists()

    def __getstate__(self):
        # clearing the cache can be prevented by modifying
        # how parallel runner handles datasets (not trivial!)
        logging.getLogger(__name__).warning("%s: clearing cache to pickle.", str(self))
        self._cache.release()
        return self.__dict__
