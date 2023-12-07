import pytest

from kedro.io import DatasetError, SharedMemoryDataset
from kedro.runner.parallel_runner import ParallelRunnerManager
from tests.io.test_memory_dataset import _check_equals, _update_data


@pytest.fixture
def shared_memory_dataset():
    manager = ParallelRunnerManager()
    manager.start()
    return SharedMemoryDataset(manager=manager)


class TestSharedMemoryDataset:
    def test_save_and_load(self, shared_memory_dataset, input_data):
        """Test basic load"""
        shared_memory_dataset.save(input_data)
        loaded_data = shared_memory_dataset.load()
        assert _check_equals(loaded_data, input_data)

    def test_save(self, shared_memory_dataset, input_data, new_data):
        """Test overriding the dataset"""
        shared_memory_dataset.save(input_data)
        shared_memory_dataset.save(data=new_data)
        reloaded = shared_memory_dataset.load()
        assert not _check_equals(reloaded, input_data)
        assert _check_equals(reloaded, new_data)

    def test_load_modify_original_data(self, shared_memory_dataset, input_data):
        """Check that the dataset object is not updated when the original
        object is changed."""
        shared_memory_dataset.save(input_data)
        input_data = _update_data(input_data, 1, 1, -5)
        assert not _check_equals(shared_memory_dataset.load(), input_data)

    def test_save_modify_original_data(self, shared_memory_dataset, new_data):
        """Check that the dataset object is not updated when the original
        object is changed."""
        shared_memory_dataset.save(new_data)
        new_data = _update_data(new_data, 1, 1, "new value")

        assert not _check_equals(shared_memory_dataset.load(), new_data)

    @pytest.mark.parametrize(
        "input_data", ["dummy_dataframe", "dummy_numpy_array"], indirect=True
    )
    def test_load_returns_new_object(self, shared_memory_dataset, input_data):
        """Test that consecutive loads point to different objects in case of a
        pandas DataFrame and numpy array"""
        shared_memory_dataset.save(input_data)
        loaded_data = shared_memory_dataset.load()
        reloaded_data = shared_memory_dataset.load()
        assert _check_equals(loaded_data, input_data)
        assert _check_equals(reloaded_data, input_data)
        assert loaded_data is not reloaded_data

    def test_create_without_data(self):
        """Test instantiation without data"""
        assert SharedMemoryDataset() is not None

    def test_loading_none(self, shared_memory_dataset):
        """Check the error when attempting to load the dataset that doesn't
        contain any data"""
        pattern = r"Data for MemoryDataset has not been saved yet\."
        with pytest.raises(DatasetError, match=pattern):
            shared_memory_dataset.load()

    def test_saving_none(self, shared_memory_dataset):
        """Check the error when attempting to save the dataset without
        providing the data"""
        pattern = r"Saving 'None' to a 'Dataset' is not allowed"
        with pytest.raises(DatasetError, match=pattern):
            shared_memory_dataset.save(None)

    def test_str_representation(self, shared_memory_dataset):
        """Test string representation of the dataset"""
        assert "MemoryDataset" in str(shared_memory_dataset)
