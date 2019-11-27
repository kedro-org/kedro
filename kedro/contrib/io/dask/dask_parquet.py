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

"""``ParquetDaskDataSet`` is a data set used to load and save data to parquet files using Dask"""
from copy import deepcopy
from typing import Any, Dict, Optional

import dask.dataframe as dd
import fsspec
from fsspec.utils import infer_storage_options

from kedro.contrib.io import DefaultArgumentsMixIn
from kedro.io.core import AbstractDataSet

_PROTOCOL_DELIM = "://"


class ParquetDaskDataSet(DefaultArgumentsMixIn, AbstractDataSet):
    """``ParquetDaskDataSet`` loads and saves data to parquet file(s). It uses Dask
    remote data services to handle the corresponding load and save operations:
        https://docs.dask.org/en/latest/remote-data-services.html

        Example (AWS S3):
        ::

            >>> from kedro.contrib.io.dask.dask_parquet import ParquetDaskDataSet
            >>> import pandas as pd
            >>> import dask.dataframe as dd
            >>>
            >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
            >>>                      'col3': [5, 6]})
            >>> ddf = dd.from_pandas(data, npartitions=2)
            >>>
            >>> data_set = ParquetDaskDataSet(
            >>>                         filepath="s3://bucket_name/path/to/folder",
            >>>                         storage_options={
            >>>                             'client_kwargs':
            >>>                                 'aws_access_key_id': 'YOUR_KEY',
            >>>                                 'aws_secret_access_key': 'YOUR SECRET'},
            >>>                         save_args={"compression": "GZIP"})
            >>> data_set.save(data)
            >>> reloaded = data_set.load()
            >>>
            >>> assert ddf.compute().equals(reloaded.compute())
    """

    DEFAULT_SAVE_ARGS = {"write_index": False}

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        storage_options: Optional[Dict[str, Any]] = None,
        load_args: Optional[Dict[str, Any]] = None,
        save_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Creates a new instance of ``ParquetDaskDataSet`` pointing to concrete
        parquet files.

        Args:
            filepath: Path to a parquet file
                parquet collection or the directory of a multipart parquet.
            storage_options: Optional parameters to the backend file system driver,
                such as credentials:
                https://docs.dask.org/en/latest/remote-data-services.html#optional-parameters
            load_args: Additional loading options `dask.dataframe.read_parquet`:
                https://docs.dask.org/en/latest/dataframe-api.html#dask.dataframe.read_parquet
            save_args: Additional saving options for `dask.dataframe.to_parquet`:
                https://docs.dask.org/en/latest/dataframe-api.html#dask.dataframe.to_parquet
        """
        self._filepath = filepath
        self._protocol = infer_storage_options(self._filepath)["protocol"]
        self._storage_options = deepcopy(storage_options) or {}
        super().__init__(load_args, save_args)

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def _load(self) -> dd.DataFrame:
        return dd.read_parquet(
            self._filepath, storage_options=self._storage_options, **self._load_args
        )

    def _save(self, data: dd.DataFrame) -> None:
        data.to_parquet(
            self._filepath, storage_options=self._storage_options, **self._save_args
        )

    def _exists(self) -> bool:
        path = self._extract_path()
        file_system = fsspec.filesystem(
            protocol=self._protocol, **self._storage_options
        )
        return file_system.exists(path)

    def _extract_path(self) -> str:
        split_path = self._filepath.split(_PROTOCOL_DELIM, 1)
        if len(split_path) > 1:
            return split_path[1]
        return self._filepath  # If the length is 1, then it is local path
