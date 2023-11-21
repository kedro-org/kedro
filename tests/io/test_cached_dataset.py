import pickle
from io import StringIO

import pytest
import yaml
from kedro_datasets.pandas import CSVDataset

from kedro.io import CachedDataset, DataCatalog, DatasetError, MemoryDataset

YML_CONFIG = """
test_ds:
  type: CachedDataset
  dataset:
    type: kedro_datasets.pandas.CSVDataset
    filepath: example.csv
"""

YML_CONFIG_VERSIONED = """
test_ds:
  type: CachedDataset
  versioned: true
  dataset:
    type: kedro_datasets.pandas.CSVDataset
    filepath: example.csv
"""

YML_CONFIG_VERSIONED_BAD = """
test_ds:
  type: CachedDataset
  dataset:
    type: kedro_datasets.pandas.CSVDataset
    filepath: example.csv
    versioned: true
"""


@pytest.fixture
def cached_ds():
    wrapped = MemoryDataset()
    return CachedDataset(wrapped)


class TestCachedDataset:
    def test_load_empty(self, cached_ds):
        with pytest.raises(DatasetError, match=r"has not been saved yet"):
            _ = cached_ds.load()

    def test_save_load(self, cached_ds):
        cached_ds.save(42)
        assert cached_ds.load() == 42

    def test_save_load_caching(self, mocker):
        wrapped = MemoryDataset(-42)
        mocker.spy(wrapped, "load")
        mocker.spy(wrapped, "save")

        cached_ds = CachedDataset(wrapped)
        mocker.spy(cached_ds._cache, "save")
        mocker.spy(cached_ds._cache, "load")

        cached_ds.save(42)
        assert cached_ds.load() == 42
        assert wrapped.load.call_count == 0
        assert wrapped.save.call_count == 1
        assert cached_ds._cache.load.call_count == 1
        assert cached_ds._cache.save.call_count == 1

    def test_load_empty_cache(self, mocker):
        wrapped = MemoryDataset(-42)
        mocker.spy(wrapped, "load")

        cached_ds = CachedDataset(wrapped)
        mocker.spy(cached_ds._cache, "load")

        assert cached_ds.load() == -42
        assert wrapped.load.call_count == 1
        assert cached_ds._cache.load.call_count == 0

    def test_from_yaml(self, mocker):
        config = yaml.safe_load(StringIO(YML_CONFIG))
        catalog = DataCatalog.from_config(config)
        assert catalog.list() == ["test_ds"]
        mock = mocker.Mock()
        assert isinstance(catalog._datasets["test_ds"]._dataset, CSVDataset)
        catalog._datasets["test_ds"]._dataset = mock
        catalog.save("test_ds", 20)

        assert catalog.load("test_ds") == 20
        mock.save.assert_called_once_with(20)
        mock.load.assert_not_called()

    def test_bad_argument(self):
        with pytest.raises(
            ValueError,
            match=r"The argument type of 'dataset' "
            r"should be either a dict/YAML representation "
            r"of the dataset, or the actual dataset object",
        ):
            _ = CachedDataset(dataset="BadArgument")

    def test_config_good_version(self):
        config = yaml.safe_load(StringIO(YML_CONFIG_VERSIONED))
        catalog = DataCatalog.from_config(config, load_versions={"test_ds": "42"})
        assert catalog._datasets["test_ds"]._dataset._version.load == "42"

    def test_config_bad_version(self):
        config = yaml.safe_load(StringIO(YML_CONFIG_VERSIONED_BAD))
        with pytest.raises(
            DatasetError,
            match=r"Cached datasets should specify that they are "
            r"versioned in the 'CachedDataset', not in the "
            r"wrapped dataset",
        ):
            _ = DataCatalog.from_config(config, load_versions={"test_ds": "42"})

    def test_exists(self, cached_ds):
        assert not cached_ds.exists()
        cached_ds.save(42)
        assert cached_ds.exists()

    def test_pickle(self, cached_ds, caplog):
        _ = pickle.dumps(cached_ds)
        assert caplog.records[0].message == f"{cached_ds}: clearing cache to pickle."

    def test_str(self):
        assert (
            str(CachedDataset(MemoryDataset(42))) == "CachedDataset(cache={}, "
            "dataset={'data': <int>})"
        )

    def test_release(self, cached_ds):
        cached_ds.save(5)
        cached_ds.release()
        with pytest.raises(
            DatasetError, match=r"Data for MemoryDataset has not been saved yet"
        ):
            _ = cached_ds.load()

    def test_copy_mode(self, mocker):
        mocked_memory_dataset = mocker.patch("kedro.io.cached_dataset.MemoryDataset")
        CachedDataset(MemoryDataset(), copy_mode="assign")
        mocked_memory_dataset.assert_called_once_with(copy_mode="assign")
