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
# pylint: disable=protected-access
import pickle
from io import StringIO

import pytest
import yaml

from kedro.contrib.io.cached import CachedDataSet
from kedro.io import CSVLocalDataSet, DataCatalog, DataSetError, MemoryDataSet

YML_CONFIG = """
test_ds:
  type: kedro.contrib.io.cached.CachedDataSet
  dataset:
      type: CSVLocalDataSet
      filepath: example.csv
"""

YML_CONFIG_VERSIONED = """
test_ds:
  type: kedro.contrib.io.cached.CachedDataSet
  versioned: true
  dataset:
      type: CSVLocalDataSet
      filepath: example.csv
"""

YML_CONFIG_VERSIONED_BAD = """
test_ds:
  type: kedro.contrib.io.cached.CachedDataSet
  dataset:
      type: CSVLocalDataSet
      filepath: example.csv
      versioned: true
"""


@pytest.fixture
def cached_ds():
    wrapped = MemoryDataSet()
    return CachedDataSet(wrapped)


class TestCachedDataset:
    def test_load_empty(self, cached_ds):
        with pytest.raises(DataSetError, match=r"has not been saved yet"):
            _ = cached_ds.load()

    def test_save_load(self, cached_ds):
        cached_ds.save(42)
        assert cached_ds.load() == 42

    def test_save_load_caching(self, mocker):
        wrapped = MemoryDataSet(-42)
        mocker.spy(wrapped, "load")
        mocker.spy(wrapped, "save")

        cached_ds = CachedDataSet(wrapped)
        mocker.spy(cached_ds._cache, "save")
        mocker.spy(cached_ds._cache, "load")

        cached_ds.save(42)
        assert cached_ds.load() == 42
        assert wrapped.load.call_count == 0
        assert wrapped.save.call_count == 1
        assert cached_ds._cache.load.call_count == 1
        assert cached_ds._cache.save.call_count == 1

    def test_load_empty_cache(self, mocker):
        wrapped = MemoryDataSet(-42)
        mocker.spy(wrapped, "load")

        cached_ds = CachedDataSet(wrapped)
        mocker.spy(cached_ds._cache, "load")

        assert cached_ds.load() == -42
        assert wrapped.load.call_count == 1
        assert cached_ds._cache.load.call_count == 0

    def test_from_yaml(self, mocker):
        config = yaml.safe_load(StringIO(YML_CONFIG))
        catalog = DataCatalog.from_config(config)
        assert catalog.list() == ["test_ds"]
        mock = mocker.Mock()
        assert isinstance(catalog._data_sets["test_ds"]._dataset, CSVLocalDataSet)
        catalog._data_sets["test_ds"]._dataset = mock
        catalog.save("test_ds", 20)

        assert catalog.load("test_ds") == 20
        mock.save.assert_called_once_with(20)
        mock.load.assert_not_called()

    def test_bad_argument(self):
        with pytest.raises(
            ValueError,
            match=r"The argument type of `dataset` "
            r"should be either a dict/YAML representation "
            r"of the dataset, or the actual dataset object",
        ):
            _ = CachedDataSet(dataset="BadArgument")

    def test_config_good_version(self):
        config = yaml.safe_load(StringIO(YML_CONFIG_VERSIONED))
        catalog = DataCatalog.from_config(config, load_versions={"test_ds": "42"})
        assert catalog._data_sets["test_ds"]._dataset._version.load == "42"

    def test_config_bad_version(self):
        config = yaml.safe_load(StringIO(YML_CONFIG_VERSIONED_BAD))
        with pytest.raises(
            DataSetError,
            match=r"Cached datasets should specify that they are "
            r"versioned in the `CachedDataSet`, not in the "
            r"wrapped dataset",
        ):
            _ = DataCatalog.from_config(config, load_versions={"test_ds": "42"})

    def test_exists(self, cached_ds):
        assert not cached_ds.exists()
        cached_ds.save(42)
        assert cached_ds.exists()

    def test_pickle(self, cached_ds, caplog):
        _ = pickle.dumps(cached_ds)
        assert caplog.records[0].message == "{}: clearing cache to pickle.".format(
            cached_ds
        )

    def test_str(self):
        assert (
            str(CachedDataSet(MemoryDataSet(42))) == "CachedDataSet(cache={}, "
            "dataset={'data': <int>})"
        )

    def test_release(self, cached_ds):
        cached_ds.save(5)
        cached_ds.release()
        with pytest.raises(
            DataSetError, match=r"Data for MemoryDataSet has not been saved yet"
        ):
            _ = cached_ds.load()
