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

"""``ParquetDataSet`` loads/saves data from/to a Parquet file using an underlying
filesystem (e.g.: local, S3, GCS). It uses pandas to handle the Parquet file.
"""
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Dict

import fsspec
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from kedro.io.core import (
    AbstractVersionedDataSet,
    DataSetError,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)


class ParquetDataSet(AbstractVersionedDataSet):
    """``ParquetDataSet`` loads/saves data from/to a Parquet file using an underlying
    filesystem (e.g.: local, S3, GCS). It uses pandas to handle the Parquet file.

    Example:
    ::

        >>> from kedro.extras.datasets.pandas import ParquetDataSet
        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>>
        >>> # data_set = ParquetDataSet(filepath="gcs://bucket/test.parquet")
        >>> data_set = ParquetDataSet(filepath="test.parquet")
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>> assert data.equals(reloaded)

    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``ParquetDataSet`` pointing to a concrete Parquet file
        on a specific filesystem.

        Args:
            filepath: Filepath in POSIX format to a Parquet file prefixed with a protocol like
                `s3://`. If prefix is not provided, `file` protocol (local filesystem) will be used.
                The prefix should be any protocol supported by ``fsspec``.
                It can also be a path to a directory. If the directory is
                provided then it can be used for reading partitioned parquet files.
                Note: `http(s)` doesn't support versioning.
            load_args: Additional options for loading Parquet file(s).
                Here you can find all available arguments when reading single file:
                https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_parquet.html
                Here you can find all available arguments when reading partitioned datasets:
                https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetDataset.html#pyarrow.parquet.ParquetDataset.read
                All defaults are preserved.
            save_args: Additional saving options for `pyarrow.parquet.write_table` and
                `pyarrow.Table.from_pandas`.
                Here you can find all available arguments for `write_table()`:
                https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html?highlight=write_table#pyarrow.parquet.write_table
                The arguments for `from_pandas()` should be passed through a nested
                key: `from_pandas`. E.g.: `save_args = {"from_pandas": {"preserve_index": False}}`
                Here you can find all available arguments for `from_pandas()`:
                https://arrow.apache.org/docs/python/generated/pyarrow.Table.html#pyarrow.Table.from_pandas
            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
                attribute is None, save version will be autogenerated.
            credentials: Credentials required to get access to the underlying filesystem.
                E.g. for ``GCSFileSystem`` it should look like `{"token": None}`.
            fs_args: Extra arguments to pass into underlying filesystem class constructor
                (e.g. `{"project": "my-project"}` for ``GCSFileSystem``), as well as
                to pass to the filesystem's `open` method through nested keys
                `open_args_load` and `open_args_save`.
                Here you can find all available arguments for `open`:
                https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.open
                All defaults are preserved.
        """
        _fs_args = deepcopy(fs_args) or {}
        self._fs_open_args_load = _fs_args.pop("open_args_load", {})
        _credentials = deepcopy(credentials) or {}

        protocol, path = get_protocol_and_path(filepath, version)

        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **_credentials, **_fs_args)

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            exists_function=self._fs.exists,
            glob_function=self._fs.glob,
        )

        self._from_pandas_args = {}  # type: Dict[str, Any]

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._from_pandas_args.update(save_args.pop("from_pandas", {}))
            self._save_args.update(save_args)

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            protocol=self._protocol,
            load_args=self._load_args,
            save_args=self._save_args,
            version=self._version,
        )

    def _load(self) -> pd.DataFrame:
        load_path = get_filepath_str(self._get_load_path(), self._protocol)

        if self._fs.isdir(load_path):
            # It doesn't work at least on S3 if root folder was created manually
            # https://issues.apache.org/jira/browse/ARROW-7867
            data = (
                pq.ParquetDataset(load_path, filesystem=self._fs)
                .read(**self._load_args)
                .to_pandas()
            )
        else:
            with self._fs.open(load_path, **self._fs_open_args_load) as fs_file:
                data = pd.read_parquet(fs_file, **self._load_args)

        return data

    def _save(self, data: pd.DataFrame) -> None:
        save_path = get_filepath_str(self._get_save_path(), self._protocol)

        if Path(save_path).is_dir():
            raise DataSetError(
                f"Saving {self.__class__.__name__} to a directory is not supported."
            )

        table = pa.Table.from_pandas(data, **self._from_pandas_args)
        pq.write_table(
            table=table, where=save_path, filesystem=self._fs, **self._save_args
        )

        self._invalidate_cache()

    def _exists(self) -> bool:
        try:
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
        except DataSetError:
            return False

        return self._fs.exists(load_path)

    def _release(self) -> None:
        super()._release()
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate underlying filesystem caches."""
        filepath = get_filepath_str(self._filepath, self._protocol)
        self._fs.invalidate_cache(filepath)
