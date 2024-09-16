import pytest
from pandas.testing import assert_frame_equal

from kedro.io import KedroDataCatalog


@pytest.fixture
def data_catalog(dataset):
    return KedroDataCatalog(datasets={"test": dataset})


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
