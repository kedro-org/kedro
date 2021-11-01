"""``ParquetDataSet`` is a data set used to load and save data to parquet files using Dask
dataframe"""

from copy import deepcopy
from typing import Any, Dict

import dask.dataframe as dd
import fsspec

from kedro.io.core import AbstractDataSet, get_protocol_and_path


class ParquetDataSet(AbstractDataSet):
    """``ParquetDataSet`` loads and saves data to parquet file(s). It uses Dask
    remote data services to handle the corresponding load and save operations:
    https://docs.dask.org/en/latest/how-to/connect-to-remote-data.html

        Example (AWS S3):
        ::

            >>> from kedro.extras.datasets.dask import ParquetDataSet
            >>> import pandas as pd
            >>> import dask.dataframe as dd
            >>>
            >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
            >>>                      'col3': [5, 6]})
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
    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {"write_index": False}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
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
        return dict(
            filepath=self._filepath,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def _load(self) -> dd.DataFrame:
        return dd.read_parquet(
            self._filepath, storage_options=self.fs_args, **self._load_args
        )

    def _save(self, data: dd.DataFrame) -> None:
        data.to_parquet(self._filepath, storage_options=self.fs_args, **self._save_args)

    def _exists(self) -> bool:
        protocol = get_protocol_and_path(self._filepath)[0]
        file_system = fsspec.filesystem(protocol=protocol, **self.fs_args)
        return file_system.exists(self._filepath)
