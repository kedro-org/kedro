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

"""
This module contains ``CachedDataSet``, a dataset wrapper which caches in memory the data saved,
so that the user avoids io operations with slow storage media
"""
import pickle
from typing import Any, Dict, Union

from kedro.io import (
    AbstractDataSet,
    ExistsMixin,
    FilepathVersionMixIn,
    MemoryDataSet,
    Version,
)
from kedro.io.core import VERSIONED_FLAG_KEY


class CachedDataSet(AbstractDataSet, ExistsMixin, FilepathVersionMixIn):
    """
    ``CachedDataSet`` is a dataset wrapper which caches in memory the data saved, so that the
    user avoids io operations with slow storage media.

    You can also specify ``CachedDataSet``s in catalog.yml as follows:
    ::
      test_ds:
          type: kedro.contrib.io.cached.CachedDataSet
          versioned: true
          dataset:
              type: CSVLocalDataSet
              filepath: example.csv

    Please notice that if your dataset is versioned, this should be indicated in the wrapper class
    as shown above
    """

    def __init__(
        self,
        dataset: Union[AbstractDataSet, Dict],
        max_loads: int = None,
        version: Version = None,
    ):
        super().__init__()
        if isinstance(dataset, Dict):
            self._dataset = self._from_config(dataset, version)
        elif isinstance(dataset, AbstractDataSet):
            self._dataset = dataset
        else:
            raise ValueError(
                "The argument type of `dataset` should be either a dict/YML "
                "representation of the dataset, or the actual dataset object."
            )
        self._cache = MemoryDataSet(max_loads=max_loads)

    @staticmethod
    def _from_config(config, version):
        if VERSIONED_FLAG_KEY in config:
            raise ValueError(
                "Cached datasets should specify that they are versioned in the "
                "`CachedDataSet`, not in the wrapped dataset."
            )
        if version:
            config[VERSIONED_FLAG_KEY] = True
            return AbstractDataSet.from_config("Cached", config, version.load, version.save)
        return AbstractDataSet.from_config("Cached", config)

    def _describe(self) -> Dict[str, Any]:
        return {
            "dataset": self._dataset._describe(),  # pylint: disable=protected-access
            "cache": self._cache._describe(),  # pylint: disable=protected-access
        }

    def _load(self):
        if self._cache.exists():
            return self._cache.load()

        data = self._dataset.load()
        self._cache.save(data)
        return data

    def _save(self, data: Any) -> None:
        self._dataset.save(data)
        self._cache.save(data)

    def _exists(self) -> bool:
        def _wrapped_exists():
            if hasattr(self._dataset, "exists"):
                return self._dataset.exists()
            return False  # pragma: no cover

        return self._cache.exists() or _wrapped_exists()

    def __getstate__(self):
        # in the future this can be made pickleable by erasing the cache.
        # A slight challenge would be to see how to propagate max_loads
        raise pickle.PicklingError(
            "{}: `CachedDataSet`s cannot be " r"serialised".format(str(self))
        )
