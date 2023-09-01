"""``PartitionedDataset`` loads and saves partitioned file-like data using the
underlying dataset definition. It also uses `fsspec` for filesystem level operations.
"""
from __future__ import annotations

import operator
import warnings
from copy import deepcopy
from typing import Any, Callable
from urllib.parse import urlparse

from cachetools import Cache, cachedmethod

from kedro.io.core import (
    VERSION_KEY,
    VERSIONED_FLAG_KEY,
    AbstractDataset,
    DatasetError,
    parse_dataset_definition,
)
from kedro.io.data_catalog import CREDENTIALS_KEY
from kedro.utils import load_obj

DATASET_CREDENTIALS_KEY = "dataset_credentials"
CHECKPOINT_CREDENTIALS_KEY = "checkpoint_credentials"

KEY_PROPAGATION_WARNING = (
    "Top-level %(keys)s will not propagate into the %(target)s since "
    "%(keys)s were explicitly defined in the %(target)s config."
)

S3_PROTOCOLS = ("s3", "s3a", "s3n")

# https://github.com/pylint-dev/pylint/issues/4300#issuecomment-1043601901
PartitionedDataSet: type[PartitionedDataset]
IncrementalDataSet: type[IncrementalDataset]


class PartitionedDataset(AbstractDataset):
    # noqa: too-many-instance-attributes,protected-access
    """``PartitionedDataset`` loads and saves partitioned file-like data using the
    underlying dataset definition. For filesystem level operations it uses `fsspec`:
    https://github.com/intake/filesystem_spec.

    It also supports advanced features like
    `lazy saving <https://docs.kedro.org/en/stable/data/\
    partitioned_and_incremental_datasets.html#partitioned-dataset-lazy-saving>`_.

    Example usage for the
    `YAML API <https://kedro.readthedocs.io/en/stable/data/\
    data_catalog_yaml_examples.html>`_:


    .. code-block:: yaml

        station_data:
          type: PartitionedDataset
          path: data/03_primary/station_data
          dataset:
            type: pandas.CSVDataset
            load_args:
              sep: '\\t'
            save_args:
              sep: '\\t'
              index: true
          filename_suffix: '.dat'

    Example usage for the
    `Python API <https://kedro.readthedocs.io/en/stable/data/\
    advanced_data_catalog_usage.html>`_:
    ::

        >>> import pandas as pd
        >>> from kedro.io import PartitionedDataset
        >>>
        >>> # Create a fake pandas dataframe with 10 rows of data
        >>> df = pd.DataFrame([{"DAY_OF_MONTH": str(i), "VALUE": i} for i in range(1, 11)])
        >>>
        >>> # Convert it to a dict of pd.DataFrame with DAY_OF_MONTH as the dict key
        >>> dict_df = {
                day_of_month: df[df["DAY_OF_MONTH"] == day_of_month]
                for day_of_month in df["DAY_OF_MONTH"]
            }
        >>>
        >>> # Save it as small paritions with DAY_OF_MONTH as the partition key
        >>> data_set = PartitionedDataset(
                path="df_with_partition",
                dataset="pandas.CSVDataset",
                filename_suffix=".csv"
            )
        >>> # This will create a folder `df_with_partition` and save multiple files
        >>> # with the dict key + filename_suffix as filename, i.e. 1.csv, 2.csv etc.
        >>> data_set.save(dict_df)
        >>>
        >>> # This will create lazy load functions instead of loading data into memory immediately.
        >>> loaded = data_set.load()
        >>>
        >>> # Load all the partitions
        >>> for partition_id, partition_load_func in loaded.items():
                # The actual function that loads the data
                partition_data = partition_load_func()
        >>>
        >>> # Add the processing logic for individual partition HERE
        >>> print(partition_data)

    You can also load multiple partitions from a remote storage and combine them
    like this:
    ::

        >>> import pandas as pd
        >>> from kedro.io import PartitionedDataset
        >>>
        >>> # these credentials will be passed to both 'fsspec.filesystem()' call
        >>> # and the dataset initializer
        >>> credentials = {"key1": "secret1", "key2": "secret2"}
        >>>
        >>> data_set = PartitionedDataset(
                path="s3://bucket-name/path/to/folder",
                dataset="pandas.CSVDataset",
                credentials=credentials
            )
        >>> loaded = data_set.load()
        >>> # assert isinstance(loaded, dict)
        >>>
        >>> combine_all = pd.DataFrame()
        >>>
        >>> for partition_id, partition_load_func in loaded.items():
                partition_data = partition_load_func()
                combine_all = pd.concat(
                    [combine_all, partition_data], ignore_index=True, sort=True
                )
        >>>
        >>> new_data = pd.DataFrame({"new": [1, 2]})
        >>> # creates "s3://bucket-name/path/to/folder/new/partition.csv"
        >>> data_set.save({"new/partition.csv": new_data})

    """

    def __init__(  # noqa: too-many-arguments
        self,
        path: str,
        dataset: str | type[AbstractDataset] | dict[str, Any],
        filepath_arg: str = "filepath",
        filename_suffix: str = "",
        credentials: dict[str, Any] = None,
        load_args: dict[str, Any] = None,
        fs_args: dict[str, Any] = None,
        overwrite: bool = False,
        metadata: dict[str, Any] = None,
    ):
        """Creates a new instance of ``PartitionedDataset``.

        Args:
            path: Path to the folder containing partitioned data.
                If path starts with the protocol (e.g., ``s3://``) then the
                corresponding ``fsspec`` concrete filesystem implementation will
                be used. If protocol is not specified,
                ``fsspec.implementations.local.LocalFileSystem`` will be used.
                **Note:** Some concrete implementations are bundled with ``fsspec``,
                while others (like ``s3`` or ``gcs``) must be installed separately
                prior to usage of the ``PartitionedDataset``.
            dataset: Underlying dataset definition. This is used to instantiate
                the dataset for each file located inside the ``path``.
                Accepted formats are:
                a) object of a class that inherits from ``AbstractDataset``
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
                All possible credentials management scenarios are documented here:
                https://docs.kedro.org/en/stable/data/partitioned_and_incremental_datasets.html#partitioned-dataset-credentials
            load_args: Keyword arguments to be passed into ``find()`` method of
                the filesystem implementation.
            fs_args: Extra arguments to pass into underlying filesystem class constructor
                (e.g. `{"project": "my-project"}` for ``GCSFileSystem``)
            overwrite: If True, any existing partitions will be removed.
            metadata: Any arbitrary metadata.
                This is ignored by Kedro, but may be consumed by users or external plugins.

        Raises:
            DatasetError: If versioning is enabled for the underlying dataset.
        """
        # noqa: import-outside-toplevel
        from fsspec.utils import infer_storage_options  # for performance reasons

        super().__init__()

        self._path = path
        self._filename_suffix = filename_suffix
        self._overwrite = overwrite
        self._protocol = infer_storage_options(self._path)["protocol"]
        self._partition_cache: Cache = Cache(maxsize=1)
        self.metadata = metadata

        dataset = dataset if isinstance(dataset, dict) else {"type": dataset}
        self._dataset_type, self._dataset_config = parse_dataset_definition(dataset)
        if VERSION_KEY in self._dataset_config:
            raise DatasetError(
                f"'{self.__class__.__name__}' does not support versioning of the "
                f"underlying dataset. Please remove '{VERSIONED_FLAG_KEY}' flag from "
                f"the dataset definition."
            )

        if credentials:
            if CREDENTIALS_KEY in self._dataset_config:
                self._logger.warning(
                    KEY_PROPAGATION_WARNING,
                    {"keys": CREDENTIALS_KEY, "target": "underlying dataset"},
                )
            else:
                self._dataset_config[CREDENTIALS_KEY] = deepcopy(credentials)

        self._credentials = deepcopy(credentials) or {}

        self._fs_args = deepcopy(fs_args) or {}
        if self._fs_args:
            if "fs_args" in self._dataset_config:
                self._logger.warning(
                    KEY_PROPAGATION_WARNING,
                    {"keys": "filesystem arguments", "target": "underlying dataset"},
                )
            else:
                self._dataset_config["fs_args"] = deepcopy(self._fs_args)

        self._filepath_arg = filepath_arg
        if self._filepath_arg in self._dataset_config:
            warnings.warn(
                f"'{self._filepath_arg}' key must not be specified in the dataset "
                f"definition as it will be overwritten by partition path"
            )

        self._load_args = deepcopy(load_args) or {}
        self._sep = self._filesystem.sep
        # since some filesystem implementations may implement a global cache
        self._invalidate_caches()

    @property
    def _filesystem(self):
        # for performance reasons
        import fsspec  # noqa: import-outside-toplevel

        protocol = "s3" if self._protocol in S3_PROTOCOLS else self._protocol
        return fsspec.filesystem(protocol, **self._credentials, **self._fs_args)

    @property
    def _normalized_path(self) -> str:
        if self._protocol in S3_PROTOCOLS:
            return urlparse(self._path)._replace(scheme="s3").geturl()
        return self._path

    @cachedmethod(cache=operator.attrgetter("_partition_cache"))
    def _list_partitions(self) -> list[str]:
        return [
            path
            for path in self._filesystem.find(self._normalized_path, **self._load_args)
            if path.endswith(self._filename_suffix)
        ]

    def _join_protocol(self, path: str) -> str:
        protocol_prefix = f"{self._protocol}://"
        if self._path.startswith(protocol_prefix) and not path.startswith(
            protocol_prefix
        ):
            return f"{protocol_prefix}{path}"
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

    def _load(self) -> dict[str, Callable[[], Any]]:
        partitions = {}

        for partition in self._list_partitions():
            kwargs = deepcopy(self._dataset_config)
            # join the protocol back since PySpark may rely on it
            kwargs[self._filepath_arg] = self._join_protocol(partition)
            dataset = self._dataset_type(**kwargs)  # type: ignore
            partition_id = self._path_to_partition(partition)
            partitions[partition_id] = dataset.load

        if not partitions:
            raise DatasetError(f"No partitions found in '{self._path}'")

        return partitions

    def _save(self, data: dict[str, Any]) -> None:
        if self._overwrite and self._filesystem.exists(self._normalized_path):
            self._filesystem.rm(self._normalized_path, recursive=True)

        for partition_id, partition_data in sorted(data.items()):
            kwargs = deepcopy(self._dataset_config)
            partition = self._partition_to_path(partition_id)
            # join the protocol back since tools like PySpark may rely on it
            kwargs[self._filepath_arg] = self._join_protocol(partition)
            dataset = self._dataset_type(**kwargs)  # type: ignore
            if callable(partition_data):
                partition_data = partition_data()  # noqa: redefined-loop-name
            dataset.save(partition_data)
        self._invalidate_caches()

    def _describe(self) -> dict[str, Any]:
        clean_dataset_config = (
            {k: v for k, v in self._dataset_config.items() if k != CREDENTIALS_KEY}
            if isinstance(self._dataset_config, dict)
            else self._dataset_config
        )
        return {
            "path": self._path,
            "dataset_type": self._dataset_type.__name__,
            "dataset_config": clean_dataset_config,
        }

    def _invalidate_caches(self):
        self._partition_cache.clear()
        self._filesystem.invalidate_cache(self._normalized_path)

    def _exists(self) -> bool:
        return bool(self._list_partitions())

    def _release(self) -> None:
        super()._release()
        self._invalidate_caches()


class IncrementalDataset(PartitionedDataset):
    """``IncrementalDataset`` inherits from ``PartitionedDataset``, which loads
    and saves partitioned file-like data using the underlying dataset
    definition. For filesystem level operations it uses `fsspec`:
    https://github.com/intake/filesystem_spec. ``IncrementalDataset`` also stores
    the information about the last processed partition in so-called `checkpoint`
    that is persisted to the location of the data partitions by default, so that
    subsequent pipeline run loads only new partitions past the checkpoint.

    Example:
    ::

        >>> from kedro.io import IncrementalDataset
        >>>
        >>> # these credentials will be passed to:
        >>> # a) 'fsspec.filesystem()' call,
        >>> # b) the dataset initializer,
        >>> # c) the checkpoint initializer
        >>> credentials = {"key1": "secret1", "key2": "secret2"}
        >>>
        >>> data_set = IncrementalDataset(
        >>>     path="s3://bucket-name/path/to/folder",
        >>>     dataset="pandas.CSVDataset",
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

    def __init__(  # noqa: too-many-arguments
        self,
        path: str,
        dataset: str | type[AbstractDataset] | dict[str, Any],
        checkpoint: str | dict[str, Any] | None = None,
        filepath_arg: str = "filepath",
        filename_suffix: str = "",
        credentials: dict[str, Any] = None,
        load_args: dict[str, Any] = None,
        fs_args: dict[str, Any] = None,
        metadata: dict[str, Any] = None,
    ):

        """Creates a new instance of ``IncrementalDataset``.

        Args:
            path: Path to the folder containing partitioned data.
                If path starts with the protocol (e.g., ``s3://``) then the
                corresponding ``fsspec`` concrete filesystem implementation will
                be used. If protocol is not specified,
                ``fsspec.implementations.local.LocalFileSystem`` will be used.
                **Note:** Some concrete implementations are bundled with ``fsspec``,
                while others (like ``s3`` or ``gcs``) must be installed separately
                prior to usage of the ``PartitionedDataset``.
            dataset: Underlying dataset definition. This is used to instantiate
                the dataset for each file located inside the ``path``.
                Accepted formats are:
                a) object of a class that inherits from ``AbstractDataset``
                b) a string representing a fully qualified class name to such class
                c) a dictionary with ``type`` key pointing to a string from b),
                other keys are passed to the Dataset initializer.
                Credentials for the dataset can be explicitly specified in
                this configuration.
            checkpoint: Optional checkpoint configuration. Accepts a dictionary
                with the corresponding dataset definition including ``filepath``
                (unlike ``dataset`` argument). Checkpoint configuration is
                described here:
                https://docs.kedro.org/en/stable/data/partitioned_and_incremental_datasets.html#checkpoint-configuration
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
                https://docs.kedro.org/en/stable/data/partitioned_and_incremental_datasets.html#checkpoint-configuration
            load_args: Keyword arguments to be passed into ``find()`` method of
                the filesystem implementation.
            fs_args: Extra arguments to pass into underlying filesystem class constructor
                (e.g. `{"project": "my-project"}` for ``GCSFileSystem``).
            metadata: Any arbitrary metadata.
                This is ignored by Kedro, but may be consumed by users or external plugins.

        Raises:
            DatasetError: If versioning is enabled for the underlying dataset.
        """

        super().__init__(
            path=path,
            dataset=dataset,
            filepath_arg=filepath_arg,
            filename_suffix=filename_suffix,
            credentials=credentials,
            load_args=load_args,
            fs_args=fs_args,
        )

        self._checkpoint_config = self._parse_checkpoint_config(checkpoint)
        self._force_checkpoint = self._checkpoint_config.pop("force_checkpoint", None)
        self.metadata = metadata

        comparison_func = self._checkpoint_config.pop("comparison_func", operator.gt)
        if isinstance(comparison_func, str):
            comparison_func = load_obj(comparison_func)
        self._comparison_func = comparison_func

    def _parse_checkpoint_config(
        self, checkpoint_config: str | dict[str, Any] | None
    ) -> dict[str, Any]:
        checkpoint_config = deepcopy(checkpoint_config)
        if isinstance(checkpoint_config, str):
            checkpoint_config = {"force_checkpoint": checkpoint_config}
        checkpoint_config = checkpoint_config or {}

        for key in {VERSION_KEY, VERSIONED_FLAG_KEY} & checkpoint_config.keys():
            raise DatasetError(
                f"'{self.__class__.__name__}' does not support versioning of the "
                f"checkpoint. Please remove '{key}' key from the checkpoint definition."
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
                KEY_PROPAGATION_WARNING,
                {"keys": CREDENTIALS_KEY, "target": "checkpoint"},
            )

        return {**default_config, **checkpoint_config}

    @cachedmethod(cache=operator.attrgetter("_partition_cache"))
    def _list_partitions(self) -> list[str]:
        checkpoint = self._read_checkpoint()
        checkpoint_path = self._filesystem._strip_protocol(  # noqa: protected-access
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
    def _checkpoint(self) -> AbstractDataset:
        type_, kwargs = parse_dataset_definition(self._checkpoint_config)
        return type_(**kwargs)  # type: ignore

    def _read_checkpoint(self) -> str | None:
        if self._force_checkpoint is not None:
            return self._force_checkpoint
        try:
            return self._checkpoint.load()
        except DatasetError:
            return None

    def _load(self) -> dict[str, Callable[[], Any]]:
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


_DEPRECATED_CLASSES = {
    "PartitionedDataSet": PartitionedDataset,
    "IncrementalDataSet": IncrementalDataset,
}


def __getattr__(name):
    if name in _DEPRECATED_CLASSES:
        alias = _DEPRECATED_CLASSES[name]
        warnings.warn(
            f"{repr(name)} has been renamed to {repr(alias.__name__)}, "
            f"and the alias will be removed in Kedro 0.19.0",
            DeprecationWarning,
            stacklevel=2,
        )
        return alias
    raise AttributeError(f"module {repr(__name__)} has no attribute {repr(name)}")
