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

"""``ParquetS3DaskDataSet`` is a data set used to load and save
data to parquet files using Dask on S3
"""
from typing import Any, Dict, Optional

import dask.dataframe as dd

from kedro.contrib.io import DefaultArgumentsMixIn
from kedro.io.core import AbstractDataSet, DataSetError


class ParquetS3DaskDataSet(DefaultArgumentsMixIn, AbstractDataSet):
    """``ParquetS3DaskDataSet`` loads and saves data to file(s) in S3. It uses s3fs
        to read and write from S3 and dask to handle the parquet file.

        Example:
        ::

            >>> from kedro.contrib.io.parquet.dask_parquet_s3 import ParquetS3DaskDataSet
            >>> import pandas as pd
            >>> import dask.dataframe as dd
            >>>
            >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
            >>>                      'col3': [5, 6]})
            >>> ddf = dd.from_pandas(data, npartitions=2)
            >>>
            >>> data_set = ParquetS3DaskDataSet(
            >>>                         filepath="temp_folder",
            >>>                         credentials={
            >>>                             'aws_access_key_id': 'YOUR_KEY',
            >>>                             'aws_secret_access_key': 'YOUR SECRET'},
            >>>                         save_args={"compression": "GZIP"})
            >>> data_set.save(data)
            >>> reloaded = data_set.load()
            >>>
            >>> assert ddf.compute().equals(reloaded.compute())
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        credentials: Optional[Dict[str, Any]] = None,
        load_args: Optional[Dict[str, Any]] = None,
        save_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Creates a new instance of ``ParquetS3DaskDataSet`` pointing to a concrete
        parquet file on S3.

        Args:
            filepath: Path to a parquet file
                parquet collection or the directory of a multipart parquet.
            bucket_name: S3 bucket name.
            credentials: Credentials to access the S3 bucket, such as
                ``aws_access_key_id``, ``aws_secret_access_key``.
            load_args: Additional loading options `pyarrow`:
                https://arrow.apache.org/docs/python/generated/pyarrow.parquet.read_table.html
                or `fastparquet`:
                https://fastparquet.readthedocs.io/en/latest/api.html#fastparquet.ParquetFile.to_pandas
            save_args: Additional saving options for `pyarrow`:
                https://arrow.apache.org/docs/python/generated/pyarrow.Table.html#pyarrow.Table.from_pandas
                or `fastparquet`:
                https://fastparquet.readthedocs.io/en/latest/api.html#fastparquet.write
        """

        self._filepath = filepath
        self._credentials = credentials if credentials else {}
        super().__init__(load_args, save_args)

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def _load(self) -> dd.DataFrame:
        return dd.read_parquet(self._filepath, **self._load_args)

    def _save(self, data: dd.DataFrame) -> None:
        data.to_parquet(self._filepath, **self._save_args)

    def _exists(self) -> bool:
        try:
            dd.read_parquet(self._filepath, **self._load_args)
        except DataSetError:
            return False
        return True
