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

from pathlib import PurePosixPath

import numpy as np
import pytest
import tensorflow as tf
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs import S3FileSystem

from kedro.extras.datasets.tensorflow import TensorFlowModelDataset
from kedro.io import DataSetError
from kedro.io.core import Version

AWS_MODEL_DIR_NAME = "test_tf_model"
AWS_BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(
    aws_access_key_id="FAKE_ACCESS_KEY", aws_secret_access_key="FAKE_SECRET_KEY"
)


@pytest.fixture
def filepath(tmp_path):
    return str(tmp_path / "test_tf")


@pytest.fixture(params=[None])
def load_args(request):
    return request.param


@pytest.fixture(
    params=[
        {
            "overwrite": True,
            "include_optimizer": True,
            "save_format": "tf",
            "signatures": None,
            "options": None,
        }
    ]
)
def save_args(request):
    return request.param


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
def tensorflow_model_data_set(filepath, load_args, save_args, fs_args):
    return TensorFlowModelDataset(
        filepath=filepath, load_args=load_args, save_args=save_args, fs_args=fs_args
    )


@pytest.fixture
def versioned_tensorflow_model_data_set(filepath, load_args, save_args, version):
    return TensorFlowModelDataset(
        filepath=filepath, load_args=load_args, save_args=save_args, version=version
    )


@pytest.fixture
def dummy_tf_base_model(dummy_x_train, dummy_y_train):
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
def dummy_tf_subclassed_model(dummy_x_train, dummy_y_train):
    """Demonstrate that own class models cannot be saved
    using HDF5 format but can using TF format
    """

    class MyModel(tf.keras.Model):
        def __init__(self):
            super().__init__()
            self.dense1 = tf.keras.layers.Dense(4, activation=tf.nn.relu)
            self.dense2 = tf.keras.layers.Dense(5, activation=tf.nn.softmax)

        def call(self, inputs):
            x = self.dense1(inputs)
            return self.dense2(x)

    model = MyModel()
    model.compile("rmsprop", "mse")
    model.fit(dummy_x_train, dummy_y_train, batch_size=64, epochs=1)
    return model


class TestTensorFlowModelDataset:
    """
    no versioning passed to creator
    """

    def test_save_and_load(
        self, tensorflow_model_data_set, dummy_tf_base_model, dummy_x_test
    ):
        """Test saving and reloading the data set."""
        predictions = dummy_tf_base_model.predict(dummy_x_test)
        tensorflow_model_data_set.save(dummy_tf_base_model)

        reloaded = tensorflow_model_data_set.load()
        new_predictions = reloaded.predict(dummy_x_test)
        np.testing.assert_allclose(predictions, new_predictions, rtol=1e-6, atol=1e-6)

    def test_load_missing_model(self, tensorflow_model_data_set):
        """Test error message when trying to load missing model."""
        pattern = (
            r"Failed while loading data from data set TensorFlowModelDataset\(.*\)"
        )
        with pytest.raises(DataSetError, match=pattern):
            tensorflow_model_data_set.load()

    def test_exists(self, tensorflow_model_data_set, dummy_tf_base_model):
        """Test `exists` method invocation for both existing and nonexistent data set."""
        assert not tensorflow_model_data_set.exists()
        tensorflow_model_data_set.save(dummy_tf_base_model)
        assert tensorflow_model_data_set.exists()

    def test_prevent_overwrite(self, dummy_tf_base_model, filepath):
        """Test TensorflowModelDataset thorws error and does not
        overwrite existing model when save_arg overwrite=False
        """
        no_overwrite_data_set = TensorFlowModelDataset(
            filepath=filepath, save_args={"overwrite": False}
        )
        no_overwrite_data_set.save(dummy_tf_base_model)
        pattern = r"Failed while saving data to data set TensorFlowModelDataset\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            no_overwrite_data_set.save(dummy_tf_base_model)

    def test_hdf5_save_format(self, dummy_tf_base_model, dummy_x_test, filepath):
        """Test TensorflowModelDataset can save TF graph models in HDF5 format"""
        hdf5_data_set = TensorFlowModelDataset(
            filepath=filepath, save_args={"save_format": "h5"}
        )
        hdf5_data_set.save(dummy_tf_base_model)

        predictions = dummy_tf_base_model.predict(dummy_x_test)
        hdf5_data_set.save(dummy_tf_base_model)

        reloaded = hdf5_data_set.load()
        new_predictions = reloaded.predict(dummy_x_test)
        np.testing.assert_allclose(predictions, new_predictions, rtol=1e-6, atol=1e-6)

    def test_unused_subclass_model_hdf5_save_format(
        self,
        dummy_tf_subclassed_model,
        dummy_x_train,
        dummy_y_train,
        dummy_x_test,
        filepath,
    ):
        """Test TensorflowModelDataset cannot save subclassed user models in HDF5 format


                Subclassed model

                From TF docs
                First of all, a subclassed model that has never been used cannot be saved.
                That's because a subclassed model needs to be called on some data in order to create its weights.
                """
        hdf5_data_set = TensorFlowModelDataset(
            filepath=filepath, save_args={"save_format": "h5"}
        )
        # demonstrating is a working model
        dummy_tf_subclassed_model.fit(
            dummy_x_train, dummy_y_train, batch_size=64, epochs=1
        )
        dummy_tf_subclassed_model.predict(dummy_x_test)
        pattern = (
            r"Saving the model to HDF5 format requires the model to be a Functional model or a Sequential model. "
            r"It does not work for subclassed models, because such models are defined via the body of a Python method, "
            r"which isn\'t safely serializable. Consider saving to the Tensorflow SavedModel format \(by setting "
            r'save_format="tf"\) or using `save_weights`.'
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
    def test_protocol_usage(self, filepath, instance_type):
        """Test that can be instantiated with mocked arbitrary file systems.

        """
        data_set = TensorFlowModelDataset(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        # _strip_protocol() doesn't strip http(s) protocol
        if data_set._protocol == "https":
            path = filepath.split("://")[-1]
        else:
            path = data_set._fs._strip_protocol(filepath)

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)


class TestTensorFlowModelDatasetVersioned:
    """
    Test suite with versioning argument passed into TensorFlowModelDataset creator
    Test cases adapted from
    tests.io.test_json_dataset.TestJSONDataSetVersioned
    tests.io.test_excel_local.TestExcelLocalDataSetVersioned
    """

    @pytest.mark.parametrize(
        "load_version,save_version",
        [
            (
                "A",
                "A",
            ),  # long version names can fail on Win machines due to 260 max filepath
            (
                None,
                None,
            ),  # passing None default behaviour of generating timestamp for current time
        ],
        indirect=True,
    )
    def test_save_and_load(
        self, filepath, dummy_tf_base_model, dummy_x_test, load_version, save_version,
    ):
        """Test saving and reloading the versioned data set."""

        version_data_set = TensorFlowModelDataset(
            filepath=filepath, version=Version(load_version, save_version),
        )
        predictions = dummy_tf_base_model.predict(dummy_x_test)
        version_data_set.save(dummy_tf_base_model)

        reloaded = version_data_set.load()
        new_predictions = reloaded.predict(dummy_x_test)
        np.testing.assert_allclose(predictions, new_predictions, rtol=1e-6, atol=1e-6)

    @pytest.mark.parametrize(
        "load_version,save_version",
        [
            (
                "A",
                "A",
            ),  # long version names can fail on Win machines due to 260 max filepath
            (
                None,
                None,
            ),  # passing None default behaviour of generating timestamp for current time
        ],
        indirect=True,
    )
    def test_prevent_overwrite(
        self, dummy_tf_base_model, filepath, load_version, save_version,
    ):
        """Check the error when attempting to override the data set if the
        corresponding file for a given save version already exists."""
        overwrite_version_data_set = TensorFlowModelDataset(
            filepath=filepath, version=Version(load_version, save_version),
        )
        overwrite_version_data_set.save(dummy_tf_base_model)
        pattern = (
            r"Save path \`.+\` for TensorFlowModelDataset\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            overwrite_version_data_set.save(dummy_tf_base_model)

    @pytest.mark.parametrize(
        "load_version,save_version",
        [
            (
                "A",
                "B",
            ),  # long version names can fail on Win machines due to 260 max filepath
            # default versioning format in kedro.io.core.generate_timestamp()
            ("2019-01-01T23.59.59.999Z", "2019-01-02T00.00.00.000Z"),
        ],
        indirect=True,
    )
    def test_save_version_warning(
        self, filepath, load_version, save_version, dummy_tf_base_model
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        incompatible_version_data_set = TensorFlowModelDataset(
            filepath=filepath, version=Version(load_version, save_version)
        )

        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for TensorFlowModelDataset\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            incompatible_version_data_set.save(dummy_tf_base_model)
