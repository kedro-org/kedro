# Copyright 2021 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=import-outside-toplevel
import numpy as np
import pytest
from sklearn.pipeline import Pipeline as SklearnPipeline
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.wrappers.scikit_learn import KerasRegressor

from kedro.extras.datasets.tensorflow import SklearnPipelineTFDataSet
from kedro.io.core import Version

# version
VERSION = "2019-01-01T23.59.59.999Z"


@pytest.fixture
def filepath_pipe(tmp_path):
    return tmp_path.as_posix()


@pytest.fixture
def unversioned_sklearn_keras_dataset(filepath_pipe):
    return SklearnPipelineTFDataSet(
        filepath=filepath_pipe,
    )


@pytest.fixture
def versioned_sklearn_keras_dataset(
    filepath_pipe, load_version=VERSION, save_version=VERSION
):
    return SklearnPipelineTFDataSet(
        filepath=filepath_pipe, version=Version(load_version, save_version)
    )


@pytest.fixture(
    params=["unversioned_sklearn_keras_dataset", "versioned_sklearn_keras_dataset"]
)
def sklearn_keras_dataset(request):
    """fixture to loop over versioned and unversioned pipeline"""
    return request.getfixturevalue(request.param)


class EqStandardScaler(StandardScaler):
    """Adds custom equality to StandardScaler."""

    def __eq__(self, other):
        if not isinstance(other, EqStandardScaler):
            return super().__eq__(other)
        fields = ["mean_", "var_"]
        return all(
            [
                np.array_equal(getattr(self, field, None), getattr(other, field, None))
                for field in fields
            ]
        )


def build_fn(input_shape=(2,)):
    # create model
    import tensorflow as tf

    model = tf.keras.Sequential()
    model.add(tf.keras.layers.Input(shape=input_shape))
    model.add(tf.keras.layers.Dense(13))
    model.add(tf.keras.layers.Dense(1))
    # Compile model
    model.compile(loss="mean_squared_error", optimizer="adam")
    return model


@pytest.fixture
def dummy_sklearn_pipe():
    return SklearnPipeline(
        [
            ("scaler", EqStandardScaler()),
            ("regressor", KerasRegressor(build_fn=build_fn)),
        ]
    )


@pytest.fixture
def dummy_x_train():
    return np.array([[1.0, 1.0], [0.0, 0.0]])


@pytest.fixture
def dummy_y_train():
    return np.array([[1], [1]])


@pytest.fixture
def dummy_fitted_sklearn_pipe(dummy_sklearn_pipe, dummy_x_train, dummy_y_train):
    dummy_sklearn_pipe.fit(dummy_x_train, dummy_y_train)
    return dummy_sklearn_pipe


@pytest.fixture
def dummy_x_test():
    return np.array([[0.0, 0.0], [1.0, 1.0]])


def assert_same_length_and_named_steps(pipe1, pipe2):
    assert len(pipe1) == len(pipe2)
    assert all([pipe1.steps[i][0] == pipe2.steps[i][0] for i in range(len(pipe1))])


def assert_same_unfitted_sklearn_pipeline(pipe1, pipe2):
    assert_same_length_and_named_steps(pipe1, pipe2)
    assert all(
        [
            getattr(pipe1[i], "__class__") == getattr(pipe2[i], "__class__")
            for i in range(len(pipe1))
        ]
    )


def test_save_and_load_unfitted(sklearn_keras_dataset, dummy_sklearn_pipe):
    """Test saving and reloading an unfitted pipeline. Both versioned and unversioned"""
    sklearn_keras_dataset.save(dummy_sklearn_pipe)
    reloaded = sklearn_keras_dataset.load()
    assert_same_unfitted_sklearn_pipeline(dummy_sklearn_pipe, reloaded)


def test_save_and_load_fitted(
    sklearn_keras_dataset, dummy_fitted_sklearn_pipe, dummy_x_test
):
    """Test saving and reloading a fitted pipeline. Both versioned and unversioned"""
    expected_preds = dummy_fitted_sklearn_pipe.predict(dummy_x_test)
    sklearn_keras_dataset.save(dummy_fitted_sklearn_pipe)
    reloaded = sklearn_keras_dataset.load()
    reloaded_preds = reloaded.predict(dummy_x_test)
    assert_same_unfitted_sklearn_pipeline(dummy_fitted_sklearn_pipe, reloaded)
    assert dummy_fitted_sklearn_pipe["scaler"] == reloaded["scaler"]
    np.testing.assert_allclose(expected_preds, reloaded_preds, rtol=1e-6, atol=1e-6)


def test_exists(versioned_sklearn_keras_dataset, dummy_fitted_sklearn_pipe):
    """Test `exists` method invocation for versioned data set."""
    assert not versioned_sklearn_keras_dataset.exists()
    versioned_sklearn_keras_dataset.save(dummy_fitted_sklearn_pipe)
    assert versioned_sklearn_keras_dataset.exists()
