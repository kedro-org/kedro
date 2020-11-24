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

"""``AVRODataSet`` loads/saves data from/to a AVRO file using an underlying
filesystem (e.g.: local, S3, GCS) to/from a pandas.DataFrame.
It uses avro library to handle the AVRO file.See details here: https://avro.apache.org/
"""
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from kedro.extras.datasets.avro import AVRODataSet as BaseAVRODataSet  # type: ignore
from kedro.io.core import Version  # type: ignore


def infer_pandas_dtype_to_avro_type(dtype: np.dtype) -> Dict[str, Any]:
    """Convert numpy dtype into AVRO type.

    Args:
        dtype: numpy dtype of the dataframe columns values.

    Returns:
        AVRO field's type definition. See details here:
        https://avro.apache.org/docs/current/spec.html#schemas

    Raises:
        TypeError: raised when unknown dtype provided.
    """
    types = {
        np.dtype("bool"): "boolean",
        np.dtype("O"): "string",
        np.bool_: "boolean",
        np.int8: "int",
        np.int16: "int",
        np.int32: "int",
        np.uint8: "int",
        np.uint16: "int",
        np.uint32: "int",
        np.int64: "long",
        np.uint64: "long",
        np.object_: "string",
        np.unicode_: "string",
        np.float32: "float",
        np.float64: "double",
        np.datetime64: {"type": "long", "logicalType": "timestamp-micros"},
        pd.DatetimeTZDtype: {"type": "long", "logicalType": "timestamp-micros"},
        pd.Timestamp: {"type": "long", "logicalType": "timestamp-micros"},
        np.nan: "string",
    }

    if hasattr(dtype, "type"):
        return infer_pandas_dtype_to_avro_type(dtype.type)

    avro_type = types.get(dtype, None)
    if not avro_type:
        raise TypeError(f"Invalid type: {dtype}.")

    if isinstance(avro_type, dict):
        avro_type = avro_type.copy()

    return {"type": ["null", avro_type]}


class AVRODataSet(BaseAVRODataSet):
    """``AVRODataSet`` loads/saves data from/to an AVRO file using an underlying
    filesystem (e.g.: local, S3, GCS). It uses avro library to handle the AVRO file.

    Example:
    ::

        >>> from kedro.extras.datasets.pandas import AVRODataSet
        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>>
        >>> # data_set = AVRODataSet(filepath="gcs://bucket/test.avro")
        >>> data_set = AVRODataSet(filepath="test.avro")
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>> assert data.equals(reloaded)

    """

    def __init__(
        self,
        filepath: str,
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
        super().__init__(
            filepath=filepath,
            version=version,
            credentials=credentials,
            fs_args=fs_args,
        )

    def _describe(self) -> Dict[str, Any]:
        return dict(filepath=self._filepath, version=self._version,)

    def _load(self) -> pd.DataFrame:
        data: List[Dict[str, Any]] = BaseAVRODataSet._load(self)
        return pd.DataFrame.from_dict(data)

    @staticmethod
    def _schema_from_dataframe(data: pd.DataFrame) -> Dict[str, Any]:
        """Extract AVRO schema using pandas/numpy data types.

        Args:
            data: data values as dataframe.

        Returns:
            AVRO json schema as dict. See details about AVRO schema here:
            https://avro.apache.org/docs/current/spec.html#schemas
        """
        fields: List[Dict[str, Any]] = [
            {"name": k, **infer_pandas_dtype_to_avro_type(v.dtype)}
            for k, v in data.items()
        ]

        return {
            "namespace": "kedro.autogenerated.avro",
            "type": "array",
            "name": "kedro.pandas.avro.list",
            "items": {
                "type": "record",
                "name": "kedro.pandas.avro.item",
                "fields": fields,
            },
        }

    def _save(self, data: pd.DataFrame) -> None:
        data_dict: List[Dict[str, Any]] = data.to_dict(orient="records")
        if not self._schema:
            self._schema = AVRODataSet._schema_from_dataframe(data)
        BaseAVRODataSet._save(self, data_dict)
