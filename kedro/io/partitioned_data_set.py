# Copyright 2020 QuantumBlack Visual Analytics Limited
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

"""``PartitionedDataSet`` loads and saves partitioned file-like data using the
underlying dataset definition. It also uses `fsspec` for filesystem level operations.
"""
import operator
from copy import deepcopy
from typing import Any, Callable, Dict, List, Tuple, Type, Union
from urllib.parse import urlparse
from warnings import warn

from cachetools import Cache, cachedmethod

from kedro.io.core import (
    VERSION_KEY,
    VERSIONED_FLAG_KEY,
    AbstractDataSet,
    DataSetError,
    parse_dataset_definition,
)
from kedro.io.data_catalog import CREDENTIALS_KEY
from kedro.utils import load_obj

DATASET_CREDENTIALS_KEY = "dataset_credentials"
CHECKPOINT_CREDENTIALS_KEY = "checkpoint_credentials"

S3_PROTOCOLS = ("s3", "s3a", "s3n")


class PartitionedDataSet(AbstractDataSet):
    # pylint: disable=too-many-instance-attributes,protected-access
    """``PartitionedDataSet`` loads and saves partitioned file-like data using the
    underlying dataset definition. For filesystem level operations it uses `fsspec`:
    https://github.com/intake/filesystem_spec.

    Example:
    ::

        >>> import pandas as pd
        >>> from kedro.io import PartitionedDataSet
        >>>
        >>> # these credentials will be passed to both 'fsspec.filesystem()' call
        >>> # and the dataset initializer
        >>> credentials = {"key1": "secret1", "key2": "secret2"}
        >>>
        >>> data_set = PartitionedDataSet(
        >>>     path="s3://bucket-name/path/to/folder",
        >>>     dataset="CSVDataSet",
        >>>     credentials=credentials
        >>> )
        >>> loaded = data_set.load()
        >>> # assert isinstance(loaded, dict)
        >>>
        >>> combine_all = pd.DataFrame()
        >>>
        >>> for partition_id, partition_load_func in loaded.items():
        >>>     partition_data = partition_load_func()
        >>>     combine_all = pd.concat(
        >>>         [combine_all, partition_data], ignore_index=True, sort=True
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
                If path starts with the protocol (e.g., ``s3://``) then the
                corresponding ``fsspec`` concrete filesystem implementation will
                be used. If protocol is not specified,
                ``fsspec.implementations.local.LocalFileSystem`` will be used.
                **Note:** Some concrete implementations are bundled with ``fsspec``,
                while others (like ``s3`` or ``gcs``) must be installed separately
                prior to usage of the ``PartitionedDataSet``.
            dataset: Underlying dataset definition. This is used to instantiate
                the dataset for each file located inside the ``path``.
                Accepted formats are:
                a) object of a class that inherits from ``AbstractDataSet``
                b) a string representing a fully qualified class name to such class
                c) a dictionary with ``type`` key pointing to a string from b),
                other keys are passed to the Dataset initializer.
                Credentials for the dataset can be explicitly specified in
                this configuration.
            filepath_arg: Underlying dataset initializer argument that will
                contain a path to each corresponding partition file.
                If unspecified, defaults to "filepath".
            filename_suffix: If specified, only partitions that end with this
                string will be processed.
            credentials: Protocol-specific options that will be passed to
                ``fsspec.filesystem``
                https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.filesystem
                and the dataset initializer. If the dataset config contains
                explicit credentials spec, then such spec will take precedence.
                **Note:** ``dataset_credentials`` key has now been deprecated
                and should not be specified.
                All possible credentials management scenarios are documented here:
                https://kedro.readthedocs.io/en/stable/04_user_guide/08_advanced_io.html#partitioned-dataset-credentials
            load_args: Keyword arguments to be passed into ``find()`` method of
                the filesystem implementation.

        Raises:
            DataSetError: If versioning is enabled for the underlying dataset.
        """
        # pylint: disable=import-outside-toplevel
        from fsspec.utils import infer_storage_options  # for performance reasons

        super().__init__()

        self._path = path
        self._filename_suffix = filename_suffix
        self._protocol = infer_storage_options(self._path)["protocol"]
        self._partition_cache = Cache(maxsize=1)

        dataset = dataset if isinstance(dataset, dict) else {"type": dataset}
        self._dataset_type, self._dataset_config = parse_dataset_definition(dataset)
        if VERSION_KEY in self._dataset_config:
            raise DataSetError(
                "`{}` does not support versioning of the underlying dataset. "
                "Please remove `{}` flag from the dataset definition.".format(
                    self.__class__.__name__, VERSIONED_FLAG_KEY
                )
            )

        self._credentials, dataset_credentials = _split_credentials(credentials)
        if dataset_credentials:
            if CREDENTIALS_KEY in self._dataset_config:
                self._logger.warning(
                    "Top-level credentials will not propagate into the "
                    "underlying dataset since credentials were explicitly "
                    "defined in the dataset config."
                )
            else:
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
        self._invalidate_caches()

    @property
    def _filesystem(self):
        # for performance reasons
        import fsspec  # pylint: disable=import-outside-toplevel

        protocol = "s3" if self._protocol in S3_PROTOCOLS else self._protocol
        return fsspec.filesystem(protocol, **self._credentials)

    @property
    def _normalized_path(self) -> str:
        if self._protocol in S3_PROTOCOLS:
            return urlparse(self._path)._replace(scheme="s3").geturl()
        return self._path

    @cachedmethod(cache=operator.attrgetter("_partition_cache"))
    def _list_partitions(self) -> List[str]:
        return [
            path
            for path in self._filesystem.find(self._normalized_path, **self._load_args)
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
        dir_path = self._filesystem._strip_protocol(self._normalized_path)
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
        self._invalidate_caches()

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

    def _invalidate_caches(self):
        self._partition_cache.clear()
        self._filesystem.invalidate_cache(self._normalized_path)

    def _exists(self) -> bool:
        return bool(self._list_partitions())

    def _release(self) -> None:
        super()._release()
        self._invalidate_caches()


def _split_credentials(
    credentials: Union[Dict[str, Any], None]
) -> Tuple[Dict[str, Any], Any]:
    credentials = deepcopy(credentials) or {}
    if DATASET_CREDENTIALS_KEY in credentials:
        warn(
            "Support for `{}` key in the credentials is now deprecated and will be "
            "removed in the next version. Please specify the dataset credentials "
            "explicitly inside the dataset config.".format(DATASET_CREDENTIALS_KEY),
            DeprecationWarning,
        )
        dataset_credentials = credentials.pop(DATASET_CREDENTIALS_KEY)
    else:
        dataset_credentials = deepcopy(credentials)
    return credentials, dataset_credentials


class IncrementalDataSet(PartitionedDataSet):
    """``IncrementalDataSet`` inherits from ``PartitionedDataSet``, which loads
    and saves partitioned file-like data using the underlying dataset
    definition. For filesystem level operations it uses `fsspec`:
    https://github.com/intake/filesystem_spec. ``IncrementalDataSet`` also stores
    the information about the last processed partition in so-called `checkpoint`
    that is persisted to the location of the data partitions by default, so that
    subsequent pipeline run loads only new partitions past the checkpoint.

    Example:
    ::

        >>> from kedro.io import IncrementalDataSet
        >>>
        >>> # these credentials will be passed to:
        >>> # a) 'fsspec.filesystem()' call,
        >>> # b) the dataset initializer,
        >>> # c) the checkpoint initializer
        >>> credentials = {"key1": "secret1", "key2": "secret2"}
        >>>
        >>> data_set = IncrementalDataSet(
        >>>     path="s3://bucket-name/path/to/folder",
        >>>     dataset="CSVDataSet",
        >>>     credentials=credentials
        >>> )
        >>> loaded = data_set.load()  # loads all available partitions
        >>> # assert isinstance(loaded, dict)
        >>>
        >>> data_set.confirm()  # update checkpoint value to the last processed partition ID
        >>> reloaded = data_set.load()  # still loads all available partitions
        >>>
        >>> data_set.release()  # clears load cache
        >>> # returns an empty dictionary as no new partitions were added
        >>> data_set.load()
    """

    DEFAULT_CHECKPOINT_TYPE = "kedro.extras.datasets.text.TextDataSet"
    DEFAULT_CHECKPOINT_FILENAME = "CHECKPOINT"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        path: str,
        dataset: Union[str, Type[AbstractDataSet], Dict[str, Any]],
        checkpoint: Union[str, Dict[str, Any]] = None,
        filepath_arg: str = "filepath",
        filename_suffix: str = "",
        credentials: Dict[str, Any] = None,
        load_args: Dict[str, Any] = None,
    ):

        """Creates a new instance of ``IncrementalDataSet``.

        Args:
            path: Path to the folder containing partitioned data.
                If path starts with the protocol (e.g., ``s3://``) then the
                corresponding ``fsspec`` concrete filesystem implementation will
                be used. If protocol is not specified,
                ``fsspec.implementations.local.LocalFileSystem`` will be used.
                **Note:** Some concrete implementations are bundled with ``fsspec``,
                while others (like ``s3`` or ``gcs``) must be installed separately
                prior to usage of the ``PartitionedDataSet``.
            dataset: Underlying dataset definition. This is used to instantiate
                the dataset for each file located inside the ``path``.
                Accepted formats are:
                a) object of a class that inherits from ``AbstractDataSet``
                b) a string representing a fully qualified class name to such class
                c) a dictionary with ``type`` key pointing to a string from b),
                other keys are passed to the Dataset initializer.
                Credentials for the dataset can be explicitly specified in
                this configuration.
            checkpoint: Optional checkpoint configuration. Accepts a dictionary
                with the corresponding dataset definition including ``filepath``
                (unlike ``dataset`` argument). Checkpoint configuration is
                described here:
                https://kedro.readthedocs.io/en/stable/04_user_guide/08_advanced_io.html#checkpoint-configuration
                Credentials for the checkpoint can be explicitly specified
                in this configuration.
            filepath_arg: Underlying dataset initializer argument that will
                contain a path to each corresponding partition file.
                If unspecified, defaults to "filepath".
            filename_suffix: If specified, only partitions that end with this
                string will be processed.
            credentials: Protocol-specific options that will be passed to
                ``fsspec.filesystem``
                https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.filesystem,
                the dataset dataset initializer and the checkpoint. If
                the dataset or the checkpoint configuration contains explicit
                credentials spec, then such spec will take precedence.
                All possible credentials management scenarios are documented here:
                https://kedro.readthedocs.io/en/stable/04_user_guide/08_advanced_io.html#partitioned-dataset-credentials
            load_args: Keyword arguments to be passed into ``find()`` method of
                the filesystem implementation.

        Raises:
            DataSetError: If versioning is enabled for the underlying dataset.
        """

        super().__init__(
            path, dataset, filepath_arg, filename_suffix, credentials, load_args
        )

        self._checkpoint_config = self._parse_checkpoint_config(checkpoint)
        self._force_checkpoint = self._checkpoint_config.pop("force_checkpoint", None)

        comparison_func = self._checkpoint_config.pop("comparison_func", operator.gt)
        if isinstance(comparison_func, str):
            comparison_func = load_obj(comparison_func)
        self._comparison_func = comparison_func

    def _parse_checkpoint_config(
        self, checkpoint_config: Union[str, Dict[str, Any], None]
    ) -> Dict[str, Any]:
        checkpoint_config = deepcopy(checkpoint_config)
        if isinstance(checkpoint_config, str):
            checkpoint_config = {"force_checkpoint": checkpoint_config}
        checkpoint_config = checkpoint_config or {}

        for key in {VERSION_KEY, VERSIONED_FLAG_KEY} & checkpoint_config.keys():
            raise DataSetError(
                "`{}` does not support versioning of the checkpoint. "
                "Please remove `{}` key from the checkpoint definition.".format(
                    self.__class__.__name__, key
                )
            )

        default_checkpoint_path = self._sep.join(
            [self._normalized_path.rstrip(self._sep), self.DEFAULT_CHECKPOINT_FILENAME]
        )
        default_config = {
            "type": self.DEFAULT_CHECKPOINT_TYPE,
            self._filepath_arg: default_checkpoint_path,
        }
        if self._credentials:
            default_config[CREDENTIALS_KEY] = deepcopy(self._credentials)

        if CREDENTIALS_KEY in default_config.keys() & checkpoint_config.keys():
            self._logger.warning(
                "Top-level credentials will not propagate into the checkpoint since "
                "credentials were explicitly defined in the checkpoint config."
            )

        return {**default_config, **checkpoint_config}

    @cachedmethod(cache=operator.attrgetter("_partition_cache"))
    def _list_partitions(self) -> List[str]:
        checkpoint = self._read_checkpoint()
        checkpoint_path = self._filesystem._strip_protocol(  # pylint: disable=protected-access
            self._checkpoint_config[self._filepath_arg]
        )

        def _is_valid_partition(partition) -> bool:
            if not partition.endswith(self._filename_suffix):
                return False
            if partition == checkpoint_path:
                return False
            if checkpoint is None:
                # nothing was processed yet
                return True
            partition_id = self._path_to_partition(partition)
            return self._comparison_func(partition_id, checkpoint)

        return sorted(
            part
            for part in self._filesystem.find(self._normalized_path, **self._load_args)
            if _is_valid_partition(part)
        )

    @property
    def _checkpoint(self) -> AbstractDataSet:
        type_, kwargs = parse_dataset_definition(self._checkpoint_config)
        return type_(**kwargs)  # type: ignore

    def _read_checkpoint(self) -> Union[str, None]:
        if self._force_checkpoint is not None:
            return self._force_checkpoint
        try:
            return self._checkpoint.load()
        except DataSetError:
            return None

    def _load(self) -> Dict[str, Callable[[], Any]]:
        partitions = {}

        for partition in self._list_partitions():
            partition_id = self._path_to_partition(partition)
            kwargs = deepcopy(self._dataset_config)
            # join the protocol back since PySpark may rely on it
            kwargs[self._filepath_arg] = self._join_protocol(partition)
            partitions[partition_id] = self._dataset_type(  # type: ignore
                **kwargs
            ).load()

        return partitions

    def confirm(self) -> None:
        """Confirm the dataset by updating the checkpoint value to the latest
        processed partition ID"""
        partition_ids = [self._path_to_partition(p) for p in self._list_partitions()]
        if partition_ids:
            self._checkpoint.save(partition_ids[-1])  # checkpoint to last partition
