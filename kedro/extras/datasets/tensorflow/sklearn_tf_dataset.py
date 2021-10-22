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

"""``SklearnPipelineTFDataSet`` is a data set implementation which can save and load
scikit-learn pipelines with tensorflow estimators.
"""
from pathlib import Path
from typing import Any, Dict

from sklearn.pipeline import Pipeline as SklearnPipeline

from kedro.extras.datasets.pickle import PickleDataSet
from kedro.extras.datasets.tensorflow import TensorFlowModelDataset
from kedro.io.core import Version


class SklearnPipelineTFDataSet(PickleDataSet):
    """``SklearnPipelineTFDataSet`` loads and saves scikit-learn pipelines with
    tensorflow estimators. The underlying functionality is supported by, and passes
    input arguments through to, ``TensorFlowModelDataset`` and ``PickleDataSet``.

    Example:
    ::

        >>> from sklearn.pipeline import Pipeline as SklearnPipeline
        >>> from sklearn.preprocessing import StandardScaler
        >>> from tensorflow.keras.wrappers.scikit_learn import KerasRegressor
        >>>
        >>> def build_fn(input_shape=(2,)):
        >>>     # create model
        >>>     import tensorflow as tf
        >>>
        >>>     model = tf.keras.Sequential()
        >>>     model.add(tf.keras.layers.Input(shape=input_shape))
        >>>     model.add(tf.keras.layers.Dense(13))
        >>>     model.add(tf.keras.layers.Dense(1))
        >>>     # Compile model
        >>>     model.compile(loss="mean_squared_error", optimizer="adam")
        >>>     return model
        >>>
        >>> model_pipe = SklearnPipeline(
        >>>         [
        >>>             ("scaler", StandardScaler()),
        >>>             ("regressor", KerasRegressor(build_fn=build_fn)),
        >>>         ]
        >>>     )
        >>>
        >>> from kedro.extras.datasets.tensorflow import SklearnPipelineTFDataSet
        >>>
        >>> data_set = TensorFlowModelDataset("saved_model_path")
        >>> model_pipe.fit(...)
        >>> predictions = model.predict([...])
        >>>
        >>> data_set.save(model_pipe)
        >>> loaded_model = data_set.load()
        >>> new_predictions = loaded_model.predict([...])
        >>> np.testing.assert_allclose(predictions, new_predictions, rtol=1e-6, atol=1e-6)

    """

    def __init__(  # pylint:disable=too-many-arguments
        self,
        filepath: str,
        load_args_pickle: Dict[str, Any] = None,
        load_args_tf: Dict[str, Any] = None,
        save_args_pickle: Dict[str, Any] = None,
        save_args_tf: Dict[str, Any] = None,
        version: Version = None,
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
        backend: str = "pickle",
        pickle_file_name: str = "sklearn_pipe.pickle",
        tf_file_name: str = "tf_model",
    ) -> None:
        """Creates a new instance of ``SklearnPipelineTFDataSet``.

        Args:
            filepath (str): Filepath in POSIX format to a model directory prefixed with a
                protocol like `s3://`. If prefix is not provided `file` protocol (local filesystem)
                will be used. The prefix should be any protocol supported by ``fsspec``.
                Note: `http(s)` doesn't support versioning.
            load_args_pickle (Dict[str, Any], optional): Pickle options for loading pickle files.
                You can pass in arguments that the backend load function specified accepts, e.g:
                pickle.load: https://docs.python.org/3/library/pickle.html#pickle.load
                joblib.load: https://joblib.readthedocs.io/en/latest/generated/joblib.load.html
                dill.load: https://dill.readthedocs.io/en/latest/dill.html#dill._dill.load
                compress_pickle.load:
                https://lucianopaz.github.io/compress_pickle/html/api/compress_pickle.html#compress_pickle.compress_pickle.load
                All defaults are preserved. Defaults to None.
            load_args_tf (Dict[str, Any], optional): TensorFlow options for loading models.
                Here you can find all available arguments:
                https://www.tensorflow.org/api_docs/python/tf/keras/models/load_model
                All defaults are preserved. Defaults to None.
            save_args_pickle (Dict[str, Any], optional): Pickle options for saving pickle files.
                You can pass in arguments that the backend dump function specified accepts, e.g:
                pickle.dump: https://docs.python.org/3/library/pickle.html#pickle.dump
                joblib.dump: https://joblib.readthedocs.io/en/latest/generated/joblib.dump.html
                dill.dump: https://dill.readthedocs.io/en/latest/dill.html#dill._dill.dump
                compress_pickle.dump:
                https://lucianopaz.github.io/compress_pickle/html/api/compress_pickle.html#compress_pickle.compress_pickle.dump
                All defaults are preserved. Defaults to None.
            save_args_tf (Dict[str, Any], optional): TensorFlow options for saving models.
                Here you can find all available arguments:
                https://www.tensorflow.org/api_docs/python/tf/keras/models/save_model
                All defaults are preserved, except for "save_format", which is set to "tf".
                Defaults to None.
            version (Version, optional): If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
                attribute is None, save version will be autogenerated. Defaults to None.
            credentials (Dict[str, Any], optional): Credentials required to get access to the
                underlying filesystem. E.g. for ``GCSFileSystem`` it should look like
                `{'token': None}`. Defaults to None.
            fs_args (Dict[str, Any], optional): Extra arguments to pass into underlying filesystem
                class constructor (e.g. `{"project": "my-project"}` for ``GCSFileSystem``).
                Defaults to None.
            backend (str, optional): Backend to use, must be an import path to a module which
                satisfies the ``pickle`` interface. That is, contains a `load` and `dump` function.
                Defaults to 'pickle'. Defaults to "pickle".
            pickle_file_name (str, optional): Name for pickle file. Defaults to
                "sklearn_pipe.pickle".
            tf_file_name (str, optional): Name for tf model folder. Defaults to "tf_model".
        """
        super().__init__(
            str(Path(filepath) / pickle_file_name),
            backend=backend,
            load_args=load_args_pickle,
            save_args=save_args_pickle,
            version=version,
            fs_args=fs_args,
            credentials=credentials,
        )
        self._tf_ds = TensorFlowModelDataset(
            str(Path(filepath) / tf_file_name),
            load_args=load_args_tf,
            save_args=save_args_tf,
            version=version,
            fs_args=fs_args,
            credentials=credentials,
        )

    def _load(self) -> SklearnPipeline:
        pickle_obj = super()._load()
        if self._is_fitted(pickle_obj):
            pickle_obj[-1].model = self._tf_ds._load()
        return pickle_obj

    def _is_fitted(self, pickle_obj) -> bool:
        return hasattr(pickle_obj[-1], "model")

    def _describe(self) -> Dict[str, str]:
        return {**super()._describe(), **self._tf_ds._describe()}

    def _exists(self) -> bool:
        return super()._exists() and self._tf_ds._exists()

    def _save(
        self, pickle_obj: SklearnPipeline
    ) -> None:  # pylint: disable=arguments-renamed
        if self._is_fitted(pickle_obj):
            self._tf_ds._save(pickle_obj[-1].model)
            pickle_obj[-1].model = None
        super()._save(pickle_obj)
