# pylint: disable=import-outside-toplevel
from pathlib import PurePosixPath

import numpy as np
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs import S3FileSystem

from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version


# In this test module, we wrap tensorflow and TensorFlowModelDataset imports into a module-scoped
# fixtures to avoid them being evaluated immediately when a new test process is spawned.
# Specifically:
#   - ParallelRunner spawns a new subprocess.
#   - pytest coverage is initialised on every new subprocess to update the global coverage
#     statistics.
#   - Coverage has to import the tests including tensorflow tests, which then import tensorflow.
#   - tensorflow in eager mode triggers the remove_function method in
#     tensorflow/python/eager/context.py, which acquires a threading.Lock.
#   - Using a mutex/condition variable after fork (from the child process) is unsafe:
#   it can lead to deadlocks" and can lead to segfault.
#
# So tl;dr is pytest-coverage importing of tensorflow creates a potential deadlock within
# a subprocess spawned by the parallel runner, so we wrap the import inside fixtures.
@pytest.fixture(scope="module")
def tf():
    import tensorflow as tf

    return tf


@pytest.fixture(scope="module")
def tensorflow_model_dataset():
    from kedro.extras.datasets.tensorflow import TensorFlowModelDataset

    return TensorFlowModelDataset


@pytest.fixture
def filepath(tmp_path):
    return (tmp_path / "test_tf").as_posix()


@pytest.fixture
def dummy_x_train():
    return np.array([[[1.0], [1.0]], [[0.0], [0.0]]])


@pytest.fixture
def dummy_y_train():
    return np.array([[[1], [1]], [[1], [1]]])


@pytest.fixture
def dummy_x_test():
    return np.array([[[0.0], [0.0]], [[1.0], [1.0]]])


@pytest.fixture
def tf_model_dataset(filepath, load_args, save_args, fs_args, tensorflow_model_dataset):
    return tensorflow_model_dataset(
        filepath=filepath, load_args=load_args, save_args=save_args, fs_args=fs_args
    )


@pytest.fixture
def versioned_tf_model_dataset(
    filepath, load_version, save_version, tensorflow_model_dataset
):
    return tensorflow_model_dataset(
        filepath=filepath, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_tf_base_model(dummy_x_train, dummy_y_train, tf):
    # dummy 1 layer model as used in TF tests, see
    # https://github.com/tensorflow/tensorflow/blob/8de272b3f3b73bea8d947c5f15143a9f1cfcfc6f/tensorflow/python/keras/models_test.py#L342
    inputs = tf.keras.Input(shape=(2, 1))
    x = tf.keras.layers.Dense(1)(inputs)
    outputs = tf.keras.layers.Dense(1)(x)

    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="1_layer_dummy")
    model.compile("rmsprop", "mse")
    model.fit(dummy_x_train, dummy_y_train, batch_size=64, epochs=1)
    # from https://www.tensorflow.org/guide/keras/save_and_serialize
    # Reset metrics before saving so that loaded model has same state,
    # since metric states are not preserved by Model.save_weights
    model.reset_metrics()
    return model


@pytest.fixture
def dummy_tf_subclassed_model(dummy_x_train, dummy_y_train, tf):
    """Demonstrate that own class models cannot be saved
    using HDF5 format but can using TF format
    """

    class MyModel(tf.keras.Model):
        def __init__(self):
            super().__init__()
            self.dense1 = tf.keras.layers.Dense(4, activation=tf.nn.relu)
            self.dense2 = tf.keras.layers.Dense(5, activation=tf.nn.softmax)

        # pylint: disable=unused-argument
        def call(self, inputs, training=None, mask=None):  # pragma: no cover
            x = self.dense1(inputs)
            return self.dense2(x)

    model = MyModel()
    model.compile("rmsprop", "mse")
    model.fit(dummy_x_train, dummy_y_train, batch_size=64, epochs=1)
    return model


class TestTensorFlowModelDataset:
    """No versioning passed to creator"""

    def test_save_and_load(self, tf_model_dataset, dummy_tf_base_model, dummy_x_test):
        """Test saving and reloading the data set."""
        predictions = dummy_tf_base_model.predict(dummy_x_test)
        tf_model_dataset.save(dummy_tf_base_model)

        reloaded = tf_model_dataset.load()
        new_predictions = reloaded.predict(dummy_x_test)
        np.testing.assert_allclose(predictions, new_predictions, rtol=1e-6, atol=1e-6)

        assert tf_model_dataset._load_args == {}
        assert tf_model_dataset._save_args == {"save_format": "tf"}

    def test_load_missing_model(self, tf_model_dataset):
        """Test error message when trying to load missing model."""
        pattern = (
            r"Failed while loading data from data set TensorFlowModelDataset\(.*\)"
        )
        with pytest.raises(DataSetError, match=pattern):
            tf_model_dataset.load()

    def test_exists(self, tf_model_dataset, dummy_tf_base_model):
        """Test `exists` method invocation for both existing and nonexistent data set."""
        assert not tf_model_dataset.exists()
        tf_model_dataset.save(dummy_tf_base_model)
        assert tf_model_dataset.exists()

    def test_hdf5_save_format(
        self, dummy_tf_base_model, dummy_x_test, filepath, tensorflow_model_dataset
    ):
        """Test TensorflowModelDataset can save TF graph models in HDF5 format"""
        hdf5_dataset = tensorflow_model_dataset(
            filepath=filepath, save_args={"save_format": "h5"}
        )

        predictions = dummy_tf_base_model.predict(dummy_x_test)
        hdf5_dataset.save(dummy_tf_base_model)

        reloaded = hdf5_dataset.load()
        new_predictions = reloaded.predict(dummy_x_test)
        np.testing.assert_allclose(predictions, new_predictions, rtol=1e-6, atol=1e-6)

    def test_unused_subclass_model_hdf5_save_format(
        self,
        dummy_tf_subclassed_model,
        dummy_x_train,
        dummy_y_train,
        dummy_x_test,
        filepath,
        tensorflow_model_dataset,
    ):
        """Test TensorflowModelDataset cannot save subclassed user models in HDF5 format

        Subclassed model

        From TF docs
        First of all, a subclassed model that has never been used cannot be saved.
        That's because a subclassed model needs to be called on some data in order to
        create its weights.
        """
        hdf5_data_set = tensorflow_model_dataset(
            filepath=filepath, save_args={"save_format": "h5"}
        )
        # demonstrating is a working model
        dummy_tf_subclassed_model.fit(
            dummy_x_train, dummy_y_train, batch_size=64, epochs=1
        )
        dummy_tf_subclassed_model.predict(dummy_x_test)
        pattern = (
            r"Saving the model to HDF5 format requires the model to be a Functional model or a "
            r"Sequential model. It does not work for subclassed models, because such models are "
            r"defined via the body of a Python method, which isn\'t safely serializable. Consider "
            r"saving to the Tensorflow SavedModel format \(by setting save_format=\"tf\"\) "
            r"or using `save_weights`."
        )
        with pytest.raises(DataSetError, match=pattern):
            hdf5_data_set.save(dummy_tf_subclassed_model)

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/test_tf", S3FileSystem),
            ("file:///tmp/test_tf", LocalFileSystem),
            ("/tmp/test_tf", LocalFileSystem),
            ("gcs://bucket/test_tf", GCSFileSystem),
            ("https://example.com/test_tf", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type, tensorflow_model_dataset):
        """Test that can be instantiated with mocked arbitrary file systems."""
        data_set = tensorflow_model_dataset(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "compile": False}], indirect=True
    )
    def test_load_extra_params(self, tf_model_dataset, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert tf_model_dataset._load_args[key] == value

    def test_catalog_release(self, mocker, tensorflow_model_dataset):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.tf"
        data_set = tensorflow_model_dataset(filepath=filepath)
        assert data_set._version_cache.currsize == 0  # no cache if unversioned
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)
        assert data_set._version_cache.currsize == 0

    @pytest.mark.parametrize("fs_args", [{"storage_option": "value"}])
    def test_fs_args(self, fs_args, mocker, tensorflow_model_dataset):
        fs_mock = mocker.patch("fsspec.filesystem")
        tensorflow_model_dataset("test.tf", fs_args=fs_args)

        fs_mock.assert_called_once_with("file", auto_mkdir=True, storage_option="value")

    def test_exists_with_exception(self, tf_model_dataset, mocker):
        """Test `exists` method invocation when `get_filepath_str` raises an exception."""
        mocker.patch("kedro.io.core.get_filepath_str", side_effct=DataSetError)
        assert not tf_model_dataset.exists()


class TestTensorFlowModelDatasetVersioned:
    """Test suite with versioning argument passed into TensorFlowModelDataset creator"""

    @pytest.mark.parametrize(
        "load_version,save_version",
        [
            (
                "2019-01-01T23.59.59.999Z",
                "2019-01-01T23.59.59.999Z",
            ),  # long version names can fail on Win machines due to 260 max filepath
            (
                None,
                None,
            ),  # passing None default behaviour of generating timestamp for current time
        ],
        indirect=True,
    )
    def test_save_and_load(
        self,
        dummy_tf_base_model,
        versioned_tf_model_dataset,
        dummy_x_test,
        load_version,
        save_version,
    ):  # pylint: disable=unused-argument
        """Test saving and reloading the versioned data set."""

        predictions = dummy_tf_base_model.predict(dummy_x_test)
        versioned_tf_model_dataset.save(dummy_tf_base_model)

        reloaded = versioned_tf_model_dataset.load()
        new_predictions = reloaded.predict(dummy_x_test)
        np.testing.assert_allclose(predictions, new_predictions, rtol=1e-6, atol=1e-6)

    def test_hdf5_save_format(
        self,
        dummy_tf_base_model,
        dummy_x_test,
        filepath,
        tensorflow_model_dataset,
        load_version,
        save_version,
    ):
        """Test versioned TensorflowModelDataset can save TF graph models in
        HDF5 format"""
        hdf5_dataset = tensorflow_model_dataset(
            filepath=filepath,
            save_args={"save_format": "h5"},
            version=Version(load_version, save_version),
        )

        predictions = dummy_tf_base_model.predict(dummy_x_test)
        hdf5_dataset.save(dummy_tf_base_model)

        reloaded = hdf5_dataset.load()
        new_predictions = reloaded.predict(dummy_x_test)
        np.testing.assert_allclose(predictions, new_predictions, rtol=1e-6, atol=1e-6)

    def test_prevent_overwrite(self, dummy_tf_base_model, versioned_tf_model_dataset):
        """Check the error when attempting to override the data set if the
        corresponding file for a given save version already exists."""
        versioned_tf_model_dataset.save(dummy_tf_base_model)
        pattern = (
            r"Save path \`.+\` for TensorFlowModelDataset\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_tf_model_dataset.save(dummy_tf_base_model)

    @pytest.mark.parametrize(
        "load_version,save_version",
        [("2019-01-01T23.59.59.999Z", "2019-01-02T00.00.00.000Z")],
        indirect=True,
    )
    def test_save_version_warning(
        self,
        versioned_tf_model_dataset,
        load_version,
        save_version,
        dummy_tf_base_model,
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            rf"Save version `{save_version}` did not match load version `{load_version}` "
            rf"for TensorFlowModelDataset\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_tf_model_dataset.save(dummy_tf_base_model)

    def test_http_filesystem_no_versioning(self, tensorflow_model_dataset):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            tensorflow_model_dataset(
                filepath="https://example.com/file.tf", version=Version(None, None)
            )

    def test_exists(self, versioned_tf_model_dataset, dummy_tf_base_model):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_tf_model_dataset.exists()
        versioned_tf_model_dataset.save(dummy_tf_base_model)
        assert versioned_tf_model_dataset.exists()

    def test_no_versions(self, versioned_tf_model_dataset):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for TensorFlowModelDataset\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_tf_model_dataset.load()

    def test_version_str_repr(self, tf_model_dataset, versioned_tf_model_dataset):
        """Test that version is in string representation of the class instance
        when applicable."""

        assert str(tf_model_dataset._filepath) in str(tf_model_dataset)
        assert "version=" not in str(tf_model_dataset)
        assert "protocol" in str(tf_model_dataset)
        assert "save_args" in str(tf_model_dataset)

        assert str(versioned_tf_model_dataset._filepath) in str(
            versioned_tf_model_dataset
        )
        ver_str = f"version={versioned_tf_model_dataset._version}"
        assert ver_str in str(versioned_tf_model_dataset)
        assert "protocol" in str(versioned_tf_model_dataset)
        assert "save_args" in str(versioned_tf_model_dataset)

    def test_versioning_existing_dataset(
        self, tf_model_dataset, versioned_tf_model_dataset, dummy_tf_base_model
    ):
        """Check behavior when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset. Note: because TensorFlowModelDataset
        saves to a directory even if non-versioned, an error is not expected."""
        tf_model_dataset.save(dummy_tf_base_model)
        assert tf_model_dataset.exists()
        assert tf_model_dataset._filepath == versioned_tf_model_dataset._filepath
        versioned_tf_model_dataset.save(dummy_tf_base_model)
        assert versioned_tf_model_dataset.exists()
