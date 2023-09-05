"""``ParquetDataSet`` is a data set used to load and save data to parquet files using Dask
dataframe"""

from copy import deepcopy
from typing import Any, Dict

import dask.dataframe as dd
import fsspec
import triad

from kedro.io.core import AbstractDataset, get_protocol_and_path

# NOTE: kedro.extras.datasets will be removed in Kedro 0.19.0.
# Any contribution to datasets should be made in kedro-datasets
# in kedro-plugins (https://github.com/kedro-org/kedro-plugins)


class ParquetDataSet(AbstractDataset[dd.DataFrame, dd.DataFrame]):
    """``ParquetDataSet`` loads and saves data to parquet file(s). It uses Dask
    remote data services to handle the corresponding load and save operations:
    https://docs.dask.org/en/latest/how-to/connect-to-remote-data.html

    Example usage for the
    `YAML API <https://kedro.readthedocs.io/en/stable/data/\
    data_catalog_yaml_examples.html>`_:

    .. code-block:: yaml

        cars:
          type: dask.ParquetDataSet
          filepath: s3://bucket_name/path/to/folder
          save_args:
            compression: GZIP
          credentials:
            client_kwargs:
              aws_access_key_id: YOUR_KEY
              aws_secret_access_key: YOUR_SECRET

    Example usage for the
    `Python API <https://kedro.readthedocs.io/en/stable/data/\
    advanced_data_catalog_usage.html>`_:
    ::


        >>> from kedro.extras.datasets.dask import ParquetDataSet
        >>> import pandas as pd
        >>> import dask.dataframe as dd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [[5, 6], [7, 8]]})
        >>> ddf = dd.from_pandas(data, npartitions=2)
        >>>
        >>> data_set = ParquetDataSet(
        >>>     filepath="s3://bucket_name/path/to/folder",
        >>>     credentials={
        >>>         'client_kwargs':{
        >>>             'aws_access_key_id': 'YOUR_KEY',
        >>>             'aws_secret_access_key': 'YOUR SECRET',
        >>>         }
        >>>     },
        >>>     save_args={"compression": "GZIP"}
        >>> )
        >>> data_set.save(ddf)
        >>> reloaded = data_set.load()
        >>>
        >>> assert ddf.compute().equals(reloaded.compute())

    The output schema can also be explicitly specified using
    `Triad <https://triad.readthedocs.io/en/latest/api/\
    triad.collections.html#module-triad.collections.schema>`_.
    This is processed to map specific columns to
    `PyArrow field types <https://arrow.apache.org/docs/python/api/\
    datatypes.html>`_ or schema. For instance:

    .. code-block:: yaml

        parquet_dataset:
          type: dask.ParquetDataSet
          filepath: "s3://bucket_name/path/to/folder"
          credentials:
            client_kwargs:
              aws_access_key_id: YOUR_KEY
              aws_secret_access_key: "YOUR SECRET"
          save_args:
            compression: GZIP
            schema:
              col1: [int32]
              col2: [int32]
              col3: [[int32]]
    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {"write_index": False}  # type: Dict[str, Any]

    def __init__(  # noqa: too-many-arguments
        self,
        filepath: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``ParquetDataSet`` pointing to concrete
        parquet files.

        Args:
            filepath: Filepath in POSIX format to a parquet file
                parquet collection or the directory of a multipart parquet.
            load_args: Additional loading options `dask.dataframe.read_parquet`:
                https://docs.dask.org/en/latest/generated/dask.dataframe.read_parquet.html
            save_args: Additional saving options for `dask.dataframe.to_parquet`:
                https://docs.dask.org/en/latest/generated/dask.dataframe.to_parquet.html
            credentials: Credentials required to get access to the underlying filesystem.
                E.g. for ``GCSFileSystem`` it should look like `{"token": None}`.
            fs_args: Optional parameters to the backend file system driver:
                https://docs.dask.org/en/latest/how-to/connect-to-remote-data.html#optional-parameters
        """
        self._filepath = filepath
        self._fs_args = deepcopy(fs_args) or {}
        self._credentials = deepcopy(credentials) or {}

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

    @property
    def fs_args(self) -> Dict[str, Any]:
        """Property of optional file system parameters.

        Returns:
            A dictionary of backend file system parameters, including credentials.
        """
        fs_args = deepcopy(self._fs_args)
        fs_args.update(self._credentials)
        return fs_args

    def _describe(self) -> Dict[str, Any]:
        return {
            "filepath": self._filepath,
            "load_args": self._load_args,
            "save_args": self._save_args,
        }

    def _load(self) -> dd.DataFrame:
        return dd.read_parquet(
            self._filepath, storage_options=self.fs_args, **self._load_args
        )

    def _save(self, data: dd.DataFrame) -> None:
        self._process_schema()
        data.to_parquet(self._filepath, storage_options=self.fs_args, **self._save_args)

    def _process_schema(self) -> None:
        """This method processes the schema in the catalog.yml or the API, if provided.
        This assumes that the schema is specified using Triad's grammar for
        schema definition.

        When the value of the `schema` variable is a string, it is assumed that
        it corresponds to the full schema specification for the data.

        Alternatively, if the `schema` is specified as a dictionary, then only the
        columns that are specified will be strictly mapped to a field type. The other
        unspecified columns, if present, will be inferred from the data.

        This method converts the Triad-parsed schema into a pyarrow schema.
        The output directly supports Dask's specifications for providing a schema
        when saving to a parquet file.

        Note that if a `pa.Schema` object is passed directly in the `schema` argument, no
        processing will be done. Additionally, the behavior when passing a `pa.Schema`
        object is assumed to be consistent with how Dask sees it. That is, it should fully
        define the  schema for all fields.
        """
        schema = self._save_args.get("schema")

        if isinstance(schema, dict):
            # The schema may contain values of different types, e.g., pa.DataType, Python types,
            # strings, etc. The latter requires a transformation, then we use triad handle all
            # other value types.

            # Create a schema from values that triad can handle directly
            triad_schema = triad.Schema(
                {k: v for k, v in schema.items() if not isinstance(v, str)}
            )

            # Handle the schema keys that are represented as string and add them to the triad schema
            triad_schema.update(
                triad.Schema(
                    ",".join(
                        [f"{k}:{v}" for k, v in schema.items() if isinstance(v, str)]
                    )
                )
            )

            # Update the schema argument with the normalized schema
            self._save_args["schema"].update(
                {col: field.type for col, field in triad_schema.items()}
            )

        elif isinstance(schema, str):
            self._save_args["schema"] = triad.Schema(schema).pyarrow_schema

    def _exists(self) -> bool:
        protocol = get_protocol_and_path(self._filepath)[0]
        file_system = fsspec.filesystem(protocol=protocol, **self.fs_args)
        return file_system.exists(self._filepath)
