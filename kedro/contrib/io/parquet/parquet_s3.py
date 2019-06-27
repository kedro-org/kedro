#Copyright 2018-2019 QuantumBlack Visual Analytics Limited
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

"""``ParquetS3DataSet`` is a data set used to load and save
data to parquet files on S3
"""

from typing import Any, Dict, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from s3fs.core import S3FileSystem

from kedro.io.core import (
    AbstractDataSet,
    DataSetError,
    S3PathVersionMixIn,
)


class ParquetS3DataSet(AbstractDataSet, S3PathVersionMixIn):
    """``ParquetS3DataSet`` loads and saves data to a file in S3. It uses s3fs
    to read and write from S3 and pandas to handle the parquet file.
    Example:
    ::
        >>> from kedro.contrib.io.parquet.parquet_s3 import ParquetS3DataSet
        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>>
        >>> data_set = ParquetS3DataSet(
        >>>                         filepath="temp3.parquet",
        >>>                         bucket_name="test_bucket",
        >>>                         credentials={
        >>>                             'aws_access_key_id': 'YOUR_KEY',
        >>>                             'aws_access_secredt_key': 'YOUR SECRET'},
        >>>                         save_args={"compression": "GZIP"})
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.equals(reloaded)
    """

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            bucket_name=self._bucket_name,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        bucket_name: str,
        engine: str = "auto",
        credentials: Optional[Dict[str, Any]] = None,
        load_args: Optional[Dict[str, Any]] = None,
        save_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Creates a new instance of ``ParquetS3DataSet`` pointing to a concrete
        parquet file on S3.
        Args:
            filepath: Path to a parquet file
                parquet collection or the directory of a multipart parquet.

            bucket_name: S3 bucket name.

            credentials: Credentials to access the S3 bucket, such as
                ``aws_access_key_id``, ``aws_secret_access_key``.

            engine: The engine to use, one of: `auto`, `fastparquet`,
                `pyarrow`. If `auto`, then the default behavior is to try
                `pyarrow`, falling back to `fastparquet` if `pyarrow` is
                unavailable.

            load_args: Additional loading options `pyarrow`:
                https://arrow.apache.org/docs/python/generated/pyarrow.parquet.read_table.html
                or `fastparquet`:
                https://fastparquet.readthedocs.io/en/latest/api.html#fastparquet.ParquetFile.to_pandas

            save_args: Additional saving options for `pyarrow`:
                https://arrow.apache.org/docs/python/generated/pyarrow.Table.html#pyarrow.Table.from_pandas
                or `fastparquet`:
                https://fastparquet.readthedocs.io/en/latest/api.html#fastparquet.write
        """
        default_save_args = {"compression": None}
        default_load_args = {}

        self._filepath = filepath
        self._engine = engine

        self._load_args = (
            {**default_load_args, **load_args}
            if load_args is not None
            else default_load_args
        )
        self._save_args = (
            {**default_save_args, **save_args}
            if save_args is not None
            else default_save_args
        )

        self._bucket_name = bucket_name
        self._credentials = credentials if credentials else {}
        self._s3 = S3FileSystem(client_kwargs=self._credentials)

    @property
    def _client(self):
        return self._s3.s3

    def _load(self) -> pd.DataFrame:
        load_key = self._get_load_path(
            self._client, self._bucket_name, self._filepath
        )

        with self._s3.open(
            f"s3://{self._bucket_name}/{load_key}", mode="rb"
        ) as s3_file:
            return pd.read_parquet(s3_file, engine=self._engine, **self._load_args)

    def _save(self, data: pd.DataFrame) -> None:
        save_key = self._get_save_path(
            self._client, self._bucket_name, self._filepath
        )

        output_file = f"s3://{self._bucket_name}/{self._filepath}"
        pq.write_table(pa.Table.from_pandas(data), output_file, filesystem=self._s3)

        load_key = self._get_load_path(
            self._client, self._bucket_name, self._filepath
        )
        self._check_paths_consistency(load_key, save_key)

    def _exists(self) -> bool:
        try:
            load_key = self._get_load_path(
                self._client, self._bucket_name, self._filepath
            )
        except DataSetError:
            return False
        args = (self._client, self._bucket_name, load_key)
        return any(key == load_key for key in self._list_objects(*args))
