# Copyright 2021 QuantumBlack Visual Analytics Limited
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
"""Databricks specific DataSets"""
import functools
from typing import Any, Dict, Union

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, DataFrameWriter

from kedro.extras.datasets.spark import SparkDataSet
from kedro.io.core import Version, DataSetError, NodeStatus


class DeltaTableDataset(SparkDataSet):
    """
    Schema validation: https://docs.databricks.com/delta/delta-batch.html#schema-validation-1
    """
    def __init__(  # pylint: disable=too-many-arguments
        self,
        filepath: str,
        delta_options: Dict[str, Any] = None,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
        credentials: Dict[str, Any] = None,
    ) -> None:
        super().__init__(
            filepath=filepath,
            file_format="delta",
            load_args=load_args,
            save_args=save_args,
            version=version,
            credentials=credentials,
        )
        self._read_mode = delta_options.pop("read_mode")  # better impl?
        self._write_mode = delta_options.pop("write_mode")  # this one can be a first-class arg as well
        self._delta_options = delta_options

    def _add_options(self, df: DataFrame) -> DataFrameWriter:
        # DeltaTable specific opts, such as `schemaValidation`
        if self._delta_options:
            df_writer = df.write
            return functools.reduce(
                lambda dfw, opt: df_writer.option(opt, self._delta_options[opt]),
                self._delta_options,
                df_writer,
            )
        return df.write

    def _load(self):
        # align the Spark and DeltaTable APIs
        # allow the user to provide
        # 1. a parquet to be converted (but this is a one-off)??
        # 2. a delta table
        load_path = self._fs_prefix + str(self._get_load_path())
        return DeltaTable.forPath(self._get_spark(), load_path)

    def _save(self, io: Union[DataFrame, NodeStatus]):
        # align the Spark and DeltaTable APIs
        if isinstance(io, DataFrame):
            super()._save(data=io)  # there is still `_strip_dbfs_prefix` -- will this work?
        # allow the user to handle DeltaTable IO in node and return success status
        elif isinstance(io, NodeStatus):
            if io != NodeStatus.SUCCESS:
                raise DataSetError("`NodeStatus` returned something other than SUCCESS")
        else:
            raise DataSetError("Incorrect return from node func.")
