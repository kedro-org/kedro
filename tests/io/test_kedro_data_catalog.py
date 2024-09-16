import pytest
from pandas.testing import assert_frame_equal

from kedro.io import (
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    KedroDataCatalog,
    MemoryDataset,
)


@pytest.fixture
def data_catalog(dataset):
    return KedroDataCatalog(datasets={"test": dataset})


@pytest.fixture
def memory_catalog():
    ds1 = MemoryDataset({"data": 42})
    ds2 = MemoryDataset([1, 2, 3, 4, 5])
    return KedroDataCatalog({"ds1": ds1, "ds2": ds2})


@pytest.fixture
def conflicting_feed_dict():
    return {"ds1": 0, "ds3": 1}


class TestKedroDataCatalog:
    def test_save_and_load(self, data_catalog, dummy_dataframe):
        """Test saving and reloading the data set"""
        data_catalog.save("test", dummy_dataframe)
        reloaded_df = data_catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_add_save_and_load(self, dataset, dummy_dataframe):
        """Test adding and then saving and reloading the data set"""
        catalog = KedroDataCatalog(datasets={})
        catalog.add("test", dataset)
        catalog.save("test", dummy_dataframe)
        reloaded_df = catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_load_error(self, data_catalog):
        """Check the error when attempting to load a data set
        from nonexistent source"""
        pattern = r"Failed while loading data from data set CSVDataset"
        with pytest.raises(DatasetError, match=pattern):
            data_catalog.load("test")

    def test_add_dataset_twice(self, data_catalog, dataset):
        """Check the error when attempting to add the data set twice"""
        pattern = r"Dataset 'test' has already been registered"
        with pytest.raises(DatasetAlreadyExistsError, match=pattern):
            data_catalog.add("test", dataset)

    def test_load_from_unregistered(self):
        """Check the error when attempting to load unregistered data set"""
        catalog = KedroDataCatalog(datasets={})
        pattern = r"Dataset 'test' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern):
            catalog.load("test")

    def test_save_to_unregistered(self, dummy_dataframe):
        """Check the error when attempting to save to unregistered data set"""
        catalog = KedroDataCatalog(datasets={})
        pattern = r"Dataset 'test' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern):
            catalog.save("test", dummy_dataframe)

    def test_feed_dict(self, memory_catalog, conflicting_feed_dict):
        """Test feed dict overriding some of the data sets"""
        assert "data" in memory_catalog.load("ds1")
        memory_catalog.add_feed_dict(conflicting_feed_dict, replace=True)
        assert memory_catalog.load("ds1") == 0
        assert isinstance(memory_catalog.load("ds2"), list)
        assert memory_catalog.load("ds3") == 1
