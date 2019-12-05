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

"""``PartitionedDataSet`` loads and saves partitioned file-like data using the
underlying dataset definition. It also uses `fsspec` for filesystem level operations.
"""

from copy import deepcopy
from functools import lru_cache
from typing import Any, Callable, Dict, List, Tuple, Type, Union
from warnings import warn

import fsspec
from fsspec.utils import infer_storage_options

from kedro.io.core import (
    VERSION_KEY,
    VERSIONED_FLAG_KEY,
    AbstractDataSet,
    DataSetError,
    parse_dataset_definition,
)
from kedro.io.data_catalog import CREDENTIALS_KEY

DATASET_CREDENTIALS_KEY = "dataset_credentials"

S3_PROTOCOLS = ("s3", "s3a", "s3n")


class PartitionedDataSet(AbstractDataSet):
    # pylint: disable=too-many-instance-attributes
    """``PartitionedDataSet`` loads and saves partitioned file-like data using the
    underlying dataset definition. For filesystem level operations it uses `fsspec`:
    https://github.com/intake/filesystem_spec.

    Example:
    ::

        >>> import pandas as pd
        >>> from kedro.io import PartitionedDataSet
        >>>
        >>> credentials = {
        >>>     "key1": "secret1",  # will be passed to 'fsspec.filesystem()' call
        >>>     "dataset_credentials": {  # will be passed to the dataset initializer
        >>>         "key2": "secret2",
        >>>         "key3": "secret3"
        >>>     }
        >>> }
        >>>
        >>> data_set = PartitionedDataSet(
        >>>     path="s3://bucket-name/path/to/folder",
        >>>     dataset="CSVS3DataSet",
        >>>     credentials=credentials
        >>> )
        >>> loaded = data_set.load()
        >>> assert isinstance(loaded, dict)
        >>>
        >>> combine_all = pd.DataFrame()
        >>>
        >>> for partition_id, load_function in loaded.items():
        >>>     data = load_function()
        >>>     combine_all = pd.concat(
        >>>         [combine_all, data], ignore_index=True, sort=True
        >>>     )
        >>>
        >>> new_data = pd.DataFrame({"new": [1, 2]})
        >>> # creates "s3://bucket-name/path/to/folder/new/partition.csv"
        >>> data_set.save({"new/partition.csv": new_data})
        >>>
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        path: str,
        dataset: Union[str, Type[AbstractDataSet], Dict[str, Any]],
        filepath_arg: str = "filepath",
        filename_suffix: str = "",
        credentials: Dict[str, Any] = None,
        load_args: Dict[str, Any] = None,
    ):
        """Creates a new instance of ``PartitionedDataSet``.

        Args:
            path: Path to the folder containing partitioned data.
                If path starts with the protocol (e.g., `s3://`) then the
                corresponding `fsspec` concrete filesystem implementation will
                be used. If protocol is not specified,
                ``fsspec.implementations.local.LocalFileSystem`` will be used.
                **Note:** Some concrete implementations are bundled with `fsspec`,
                while others (like `s3` or `gcs`) must be installed separately
                prior to usage of the ``PartitionedDataSet``.
            dataset: Underlying dataset definition. This is used to instantiate
                the dataset for each file located inside the ``path``.
                Accepted formats are:
                a) object of a class that inherits from ``AbstractDataSet``
                b) a string representing a fully qualified class name to such class
                c) a dictionary with `type` key pointing to a string from b),
                other keys are passed to the Dataset initializer.
                **Note:** Credentials resolution is *not* currently supported
                for the underlying dataset definition.
            filepath_arg: Underlying dataset initializer argument that will
                contain a path to each corresponding partition file.
                If unspecified, defaults to "filepath".
            filename_suffix: If specified, only partitions that end with this
                string will be processed.
            credentials: Protocol-specific options that will be passed to
                `fsspec.filesystem` call:
                https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.filesystem
                _and_ also to the underlying dataset initializer. If
                `dataset_credentials` key is present in this dictionary, then
                only its value will be passed to the dataset initializer `credentials`
                argument instead of the copy of the entire dictionary.

                Example 1: If `credentials = {"k1": "secret1"}`, then filesystem
                    is called as `filesystem(..., k1="secret1")`, the dataset is
                    instantiated as `dataset_class(..., credentials={"k1": "secret1"})`.
                Example 2: If
                    `credentials = {"k1": "secret1", "dataset_credentials": {"k2": "secret2"}}`,
                    then filesystem is called as `filesystem(..., k1="secret1")`,
                    the dataset is instantiated as
                    `dataset_class(..., credentials={"k2": "secret2"})`.
                Example 3: If `credentials = {"dataset_credentials": {"k2": "secret2"}}`,
                    then credentials are not passed to the filesystem call, the dataset
                    is instantiated as `dataset_class(..., credentials={"k2": "secret2"})`.
                Example 4: If `credentials = {"k1": "secret1", "dataset_credentials": None}`,
                    then filesystem is called as `filesystem(..., k1="secret1")`,
                    credentials are not passed to the dataset initializer.

            load_args: Keyword arguments to be passed into `find()` method of
                the filesystem implementation.

        Raises:
            DataSetError: If versioning is enabled for the underlying dataset.
        """
        super().__init__()

        self._path = path
        self._filename_suffix = filename_suffix
        self._protocol = infer_storage_options(self._path)["protocol"]

        dataset = dataset if isinstance(dataset, dict) else {"type": dataset}
        self._dataset_type, self._dataset_config = parse_dataset_definition(dataset)
        if VERSION_KEY in self._dataset_config:
            raise DataSetError(
                "`{}` does not support versioning of the underlying dataset. "
                "Please remove `{}` flag from the dataset definition.".format(
                    self.__class__.__name__, VERSIONED_FLAG_KEY
                )
            )

        if CREDENTIALS_KEY in self._dataset_config:
            raise DataSetError(
                "Credentials for the underlying dataset must not be specified "
                "explicitly in dataset configuration. Please put those under "
                "`dataset_credentials` key in a dictionary and pass as "
                "`credentials` argument to {} initializer.".format(
                    self.__class__.__name__
                )
            )
        self._credentials, dataset_credentials = _split_credentials(credentials)
        if dataset_credentials:
            self._dataset_config[CREDENTIALS_KEY] = dataset_credentials

        self._filepath_arg = filepath_arg
        if self._filepath_arg in self._dataset_config:
            warn(
                "`{}` key must not be specified in the dataset definition as it "
                "will be overwritten by partition path".format(self._filepath_arg)
            )

        self._load_args = deepcopy(load_args) or {}
        self._sep = self._filesystem.sep
        # since some filesystem implementations may implement a global cache
        self.invalidate_cache()

    @property
    def _filesystem(self) -> fsspec.AbstractFileSystem:
        protocol = "s3" if self._protocol in S3_PROTOCOLS else self._protocol
        return fsspec.filesystem(protocol, **self._credentials)

    @lru_cache(maxsize=None)
    def _list_partitions(self) -> List[str]:
        return [
            path
            for path in self._filesystem.find(self._path, **self._load_args)
            if path.endswith(self._filename_suffix)
        ]

    def _join_protocol(self, path: str) -> str:
        if self._path.startswith(self._protocol) and not path.startswith(
            self._protocol
        ):
            return "{}://{}".format(self._protocol, path)
        return path

    def _partition_to_path(self, path: str):
        dir_path = self._path.rstrip(self._sep)
        path = path.lstrip(self._sep)
        full_path = self._sep.join([dir_path, path]) + self._filename_suffix
        return full_path

    def _path_to_partition(self, path: str) -> str:
        dir_path = self._filesystem._strip_protocol(  # pylint: disable=protected-access
            self._path
        )
        path = path.split(dir_path, 1).pop().lstrip(self._sep)
        if self._filename_suffix and path.endswith(self._filename_suffix):
            path = path[: -len(self._filename_suffix)]
        return path

    def _load(self) -> Dict[str, Callable[[], Any]]:
        partitions = {}

        for partition in self._list_partitions():
            kwargs = deepcopy(self._dataset_config)
            # join the protocol back since PySpark may rely on it
            kwargs[self._filepath_arg] = self._join_protocol(partition)
            dataset = self._dataset_type(**kwargs)  # type: ignore
            partition_id = self._path_to_partition(partition)
            partitions[partition_id] = dataset.load

        if not partitions:
            raise DataSetError("No partitions found in `{}`".format(self._path))

        return partitions

    def _save(self, data: Dict[str, Any]) -> None:
        for partition_id, partition_data in sorted(data.items()):
            kwargs = deepcopy(self._dataset_config)
            partition = self._partition_to_path(partition_id)
            # join the protocol back since tools like PySpark may rely on it
            kwargs[self._filepath_arg] = self._join_protocol(partition)
            dataset = self._dataset_type(**kwargs)  # type: ignore
            dataset.save(partition_data)
        self.invalidate_cache()

    def _describe(self) -> Dict[str, Any]:
        clean_dataset_config = (
            {k: v for k, v in self._dataset_config.items() if k != CREDENTIALS_KEY}
            if isinstance(self._dataset_config, dict)
            else self._dataset_config
        )
        return dict(
            path=self._path,
            dataset_type=self._dataset_type.__name__,
            dataset_config=clean_dataset_config,
        )

    def invalidate_cache(self):
        """Invalidate `_list_partitions` method and underlying filesystem caches."""
        self._list_partitions.cache_clear()
        self._filesystem.invalidate_cache(self._path)

    def _exists(self) -> bool:
        return bool(self._list_partitions())

    def _release(self) -> None:
        self.invalidate_cache()


def _split_credentials(
    credentials: Union[Dict[str, Any], None]
) -> Tuple[Dict[str, Any], Any]:
    credentials = deepcopy(credentials) or {}
    dataset_credentials = credentials.pop(
        DATASET_CREDENTIALS_KEY, deepcopy(credentials)
    )
    return credentials, dataset_credentials
