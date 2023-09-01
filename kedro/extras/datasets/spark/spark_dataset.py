"""``AbstractVersionedDataset`` implementation to access Spark dataframes using
``pyspark``
"""
import json
from copy import deepcopy
from fnmatch import fnmatch
from functools import partial
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple
from warnings import warn

import fsspec
from hdfs import HdfsError, InsecureClient
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType
from pyspark.sql.utils import AnalysisException
from s3fs import S3FileSystem

from kedro.io.core import (
    AbstractVersionedDataset,
    DatasetError,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)

# NOTE: kedro.extras.datasets will be removed in Kedro 0.19.0.
# Any contribution to datasets should be made in kedro-datasets
# in kedro-plugins (https://github.com/kedro-org/kedro-plugins)


def _parse_glob_pattern(pattern: str) -> str:
    special = ("*", "?", "[")
    clean = []
    for part in pattern.split("/"):
        if any(char in part for char in special):
            break
        clean.append(part)
    return "/".join(clean)


def _split_filepath(filepath: str) -> Tuple[str, str]:
    split_ = filepath.split("://", 1)
    MIN_SPLIT_SIZE = 2
    if len(split_) == MIN_SPLIT_SIZE:
        return split_[0] + "://", split_[1]
    return "", split_[0]


def _strip_dbfs_prefix(path: str, prefix: str = "/dbfs") -> str:
    return path[len(prefix) :] if path.startswith(prefix) else path


def _dbfs_glob(pattern: str, dbutils: Any) -> List[str]:
    """Perform a custom glob search in DBFS using the provided pattern.
    It is assumed that version paths are managed by Kedro only.

    Args:
        pattern: Glob pattern to search for.
        dbutils: dbutils instance to operate with DBFS.

    Returns:
            List of DBFS paths prefixed with '/dbfs' that satisfy the glob pattern.
    """
    pattern = _strip_dbfs_prefix(pattern)
    prefix = _parse_glob_pattern(pattern)
    matched = set()
    filename = pattern.split("/")[-1]

    for file_info in dbutils.fs.ls(prefix):
        if file_info.isDir():
            path = str(
                PurePosixPath(_strip_dbfs_prefix(file_info.path, "dbfs:")) / filename
            )
            if fnmatch(path, pattern):
                path = "/dbfs" + path
                matched.add(path)
    return sorted(matched)


def _get_dbutils(spark: SparkSession) -> Optional[Any]:
    """Get the instance of 'dbutils' or None if the one could not be found."""
    dbutils = globals().get("dbutils")
    if dbutils:
        return dbutils

    try:
        from pyspark.dbutils import DBUtils  # pylint: disable=import-outside-toplevel

        dbutils = DBUtils(spark)
    except ImportError:
        try:
            import IPython  # pylint: disable=import-outside-toplevel
        except ImportError:
            pass
        else:
            ipython = IPython.get_ipython()
            dbutils = ipython.user_ns.get("dbutils") if ipython else None

    return dbutils


def _dbfs_exists(pattern: str, dbutils: Any) -> bool:
    """Perform an `ls` list operation in DBFS using the provided pattern.
    It is assumed that version paths are managed by Kedro.
    Broad `Exception` is present due to `dbutils.fs.ExecutionError` that
    cannot be imported directly.
    Args:
        pattern: Filepath to search for.
        dbutils: dbutils instance to operate with DBFS.
    Returns:
        Boolean value if filepath exists.
    """
    pattern = _strip_dbfs_prefix(pattern)
    file = _parse_glob_pattern(pattern)
    try:
        dbutils.fs.ls(file)
        return True
    except Exception:  # pylint: disable=broad-except
        return False


class KedroHdfsInsecureClient(InsecureClient):
    """Subclasses ``hdfs.InsecureClient`` and implements ``hdfs_exists``
    and ``hdfs_glob`` methods required by ``SparkDataSet``"""

    def hdfs_exists(self, hdfs_path: str) -> bool:
        """Determines whether given ``hdfs_path`` exists in HDFS.

        Args:
            hdfs_path: Path to check.

        Returns:
            True if ``hdfs_path`` exists in HDFS, False otherwise.
        """
        return bool(self.status(hdfs_path, strict=False))

    def hdfs_glob(self, pattern: str) -> List[str]:
        """Perform a glob search in HDFS using the provided pattern.

        Args:
            pattern: Glob pattern to search for.

        Returns:
            List of HDFS paths that satisfy the glob pattern.
        """
        prefix = _parse_glob_pattern(pattern) or "/"
        matched = set()
        try:
            for dpath, _, fnames in self.walk(prefix):
                if fnmatch(dpath, pattern):
                    matched.add(dpath)
                matched |= {
                    f"{dpath}/{fname}"
                    for fname in fnames
                    if fnmatch(f"{dpath}/{fname}", pattern)
                }
        except HdfsError:  # pragma: no cover
            # HdfsError is raised by `self.walk()` if prefix does not exist in HDFS.
            # Ignore and return an empty list.
            pass
        return sorted(matched)


class SparkDataSet(AbstractVersionedDataset[DataFrame, DataFrame]):
    """``SparkDataSet`` loads and saves Spark dataframes.

    Example usage for the
    `YAML API <https://kedro.readthedocs.io/en/stable/data/\
    data_catalog_yaml_examples.html>`_:


    .. code-block:: yaml

        weather:
          type: spark.SparkDataSet
          filepath: s3a://your_bucket/data/01_raw/weather/*
          file_format: csv
          load_args:
            header: True
            inferSchema: True
          save_args:
            sep: '|'
            header: True

        weather_with_schema:
          type: spark.SparkDataSet
          filepath: s3a://your_bucket/data/01_raw/weather/*
          file_format: csv
          load_args:
            header: True
            schema:
              filepath: path/to/schema.json
          save_args:
            sep: '|'
            header: True

        weather_cleaned:
          type: spark.SparkDataSet
          filepath: data/02_intermediate/data.parquet
          file_format: parquet

    Example usage for the
    `Python API <https://kedro.readthedocs.io/en/stable/data/\
    advanced_data_catalog_usage.html>`_:
    ::

        >>> from pyspark.sql import SparkSession
        >>> from pyspark.sql.types import (StructField, StringType,
        >>>                                IntegerType, StructType)
        >>>
        >>> from kedro.extras.datasets.spark import SparkDataSet
        >>>
        >>> schema = StructType([StructField("name", StringType(), True),
        >>>                      StructField("age", IntegerType(), True)])
        >>>
        >>> data = [('Alex', 31), ('Bob', 12), ('Clarke', 65), ('Dave', 29)]
        >>>
        >>> spark_df = SparkSession.builder.getOrCreate()\
        >>>                        .createDataFrame(data, schema)
        >>>
        >>> data_set = SparkDataSet(filepath="test_data")
        >>> data_set.save(spark_df)
        >>> reloaded = data_set.load()
        >>>
        >>> reloaded.take(4)
    """

    # this dataset cannot be used with ``ParallelRunner``,
    # therefore it has the attribute ``_SINGLE_PROCESS = True``
    # for parallelism within a Spark pipeline please consider
    # ``ThreadRunner`` instead
    _SINGLE_PROCESS = True
    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {}  # type: Dict[str, Any]

    def __init__(  # ruff: noqa: PLR0913
        self,
        filepath: str,
        file_format: str = "parquet",
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
        credentials: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``SparkDataSet``.

        Args:
            filepath: Filepath in POSIX format to a Spark dataframe. When using Databricks
                and working with data written to mount path points,
                specify ``filepath``s for (versioned) ``SparkDataSet``s
                starting with ``/dbfs/mnt``.
            file_format: File format used during load and save
                operations. These are formats supported by the running
                SparkContext include parquet, csv, delta. For a list of supported
                formats please refer to Apache Spark documentation at
                https://spark.apache.org/docs/latest/sql-programming-guide.html
            load_args: Load args passed to Spark DataFrameReader load method.
                It is dependent on the selected file format. You can find
                a list of read options for each supported format
                in Spark DataFrame read documentation:
                https://spark.apache.org/docs/latest/api/python/getting_started/quickstart_df.html
            save_args: Save args passed to Spark DataFrame write options.
                Similar to load_args this is dependent on the selected file
                format. You can pass ``mode`` and ``partitionBy`` to specify
                your overwrite mode and partitioning respectively. You can find
                a list of options for each format in Spark DataFrame
                write documentation:
                https://spark.apache.org/docs/latest/api/python/getting_started/quickstart_df.html
            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
                attribute is None, save version will be autogenerated.
            credentials: Credentials to access the S3 bucket, such as
                ``key``, ``secret``, if ``filepath`` prefix is ``s3a://`` or ``s3n://``.
                Optional keyword arguments passed to ``hdfs.client.InsecureClient``
                if ``filepath`` prefix is ``hdfs://``. Ignored otherwise.
        """
        credentials = deepcopy(credentials) or {}
        fs_prefix, filepath = _split_filepath(filepath)
        exists_function = None
        glob_function = None

        if fs_prefix in ("s3a://", "s3n://"):
            if fs_prefix == "s3n://":
                warn(
                    "'s3n' filesystem has now been deprecated by Spark, "
                    "please consider switching to 's3a'",
                    DeprecationWarning,
                )
            _s3 = S3FileSystem(**credentials)
            exists_function = _s3.exists
            glob_function = partial(_s3.glob, refresh=True)
            path = PurePosixPath(filepath)

        elif fs_prefix == "hdfs://" and version:
            warn(
                f"HDFS filesystem support for versioned {self.__class__.__name__} is "
                f"in beta and uses 'hdfs.client.InsecureClient', please use with "
                f"caution"
            )

            # default namenode address
            credentials.setdefault("url", "http://localhost:9870")
            credentials.setdefault("user", "hadoop")

            _hdfs_client = KedroHdfsInsecureClient(**credentials)
            exists_function = _hdfs_client.hdfs_exists
            glob_function = _hdfs_client.hdfs_glob  # type: ignore
            path = PurePosixPath(filepath)

        else:
            path = PurePosixPath(filepath)

            if filepath.startswith("/dbfs"):
                dbutils = _get_dbutils(self._get_spark())
                if dbutils:
                    glob_function = partial(_dbfs_glob, dbutils=dbutils)
                    exists_function = partial(_dbfs_exists, dbutils=dbutils)

        super().__init__(
            filepath=path,
            version=version,
            exists_function=exists_function,
            glob_function=glob_function,
        )

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

        # Handle schema load argument
        self._schema = self._load_args.pop("schema", None)
        if self._schema is not None:
            if isinstance(self._schema, dict):
                self._schema = self._load_schema_from_file(self._schema)

        self._file_format = file_format
        self._fs_prefix = fs_prefix
        self._handle_delta_format()

    @staticmethod
    def _load_schema_from_file(schema: Dict[str, Any]) -> StructType:

        filepath = schema.get("filepath")
        if not filepath:
            raise DatasetError(
                "Schema load argument does not specify a 'filepath' attribute. Please"
                "include a path to a JSON-serialised 'pyspark.sql.types.StructType'."
            )

        credentials = deepcopy(schema.get("credentials")) or {}
        protocol, schema_path = get_protocol_and_path(filepath)
        file_system = fsspec.filesystem(protocol, **credentials)
        pure_posix_path = PurePosixPath(schema_path)
        load_path = get_filepath_str(pure_posix_path, protocol)

        # Open schema file
        with file_system.open(load_path) as fs_file:

            try:
                return StructType.fromJson(json.loads(fs_file.read()))
            except Exception as exc:
                raise DatasetError(
                    f"Contents of 'schema.filepath' ({schema_path}) are invalid. Please"
                    f"provide a valid JSON-serialised 'pyspark.sql.types.StructType'."
                ) from exc

    def _describe(self) -> Dict[str, Any]:
        return {
            "filepath": self._fs_prefix + str(self._filepath),
            "file_format": self._file_format,
            "load_args": self._load_args,
            "save_args": self._save_args,
            "version": self._version,
        }

    @staticmethod
    def _get_spark():
        return SparkSession.builder.getOrCreate()

    def _load(self) -> DataFrame:
        load_path = _strip_dbfs_prefix(self._fs_prefix + str(self._get_load_path()))
        read_obj = self._get_spark().read

        # Pass schema if defined
        if self._schema:
            read_obj = read_obj.schema(self._schema)

        return read_obj.load(load_path, self._file_format, **self._load_args)

    def _save(self, data: DataFrame) -> None:
        save_path = _strip_dbfs_prefix(self._fs_prefix + str(self._get_save_path()))
        data.write.save(save_path, self._file_format, **self._save_args)

    def _exists(self) -> bool:
        load_path = _strip_dbfs_prefix(self._fs_prefix + str(self._get_load_path()))

        try:
            self._get_spark().read.load(load_path, self._file_format)
        except AnalysisException as exception:
            # `AnalysisException.desc` is deprecated with pyspark >= 3.4
            message = (
                exception.desc if hasattr(exception, "desc") else exception.message
            )
            if "Path does not exist:" in message or "is not a Delta table" in message:
                return False
            raise
        return True

    def _handle_delta_format(self) -> None:
        supported_modes = {"append", "overwrite", "error", "errorifexists", "ignore"}
        write_mode = self._save_args.get("mode")
        if (
            write_mode
            and self._file_format == "delta"
            and write_mode not in supported_modes
        ):
            raise DatasetError(
                f"It is not possible to perform 'save()' for file format 'delta' "
                f"with mode '{write_mode}' on 'SparkDataSet'. "
                f"Please use 'spark.DeltaTableDataSet' instead."
            )
