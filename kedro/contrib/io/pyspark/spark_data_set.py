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
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""``AbstractDataSet`` implementation to access Spark data frames using
``pyspark``
"""

import pickle
from typing import Any, Dict, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.utils import AnalysisException

from kedro.io import AbstractDataSet, ExistsMixin


class SparkDataSet(AbstractDataSet, ExistsMixin):
    """``SparkDataSet`` loads and saves Spark data frames.

    Example:
    ::

        >>> from pyspark.sql import SparkSession
        >>> from pyspark.sql.types import (StructField, StringType,
        >>>                                IntegerType, StructType)
        >>>
        >>> from kedro.contrib.io.pyspark import SparkDataSet
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

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            file_format=self._file_format,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def __init__(
        self,
        filepath: str,
        file_format: str = "parquet",
        load_args: Optional[Dict[str, Any]] = None,
        save_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Creates a new instance of ``SparkDataSet``.

        Args:
            filepath: path to a Spark data frame.
            file_format: file format used during load and save
                operations. These are formats supported by the running
                SparkContext include parquet, csv. For a list of supported
                formats please refer to Apache Spark documentation at
                https://spark.apache.org/docs/latest/sql-programming-guide.html
            load_args: Load args passed to Spark DataFrameReader load method.
                It is dependent on the selected file format. You can find
                a list of read options for each supported format
                in Spark DataFrame read documentation:
                https://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.DataFrame
            save_args: Save args passed to Spark DataFrame write options.
                Similar to load_args this is dependent on the selected file
                format. You can pass ``mode`` and ``partitionBy`` to specify
                your overwrite mode and partitioning respectively. You can find
                a list of options for each format in Spark DataFrame
                write documentation:
                https://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.DataFrame
        """

        self._filepath = filepath
        self._file_format = file_format
        self._load_args = load_args if load_args is not None else {}
        self._save_args = save_args if save_args is not None else {}

    @staticmethod
    def _get_spark():
        return SparkSession.builder.getOrCreate()

    def _load(self) -> DataFrame:
        return self._get_spark().read.load(
            self._filepath, self._file_format, **self._load_args
        )

    def _save(self, data: DataFrame) -> None:
        data.write.save(self._filepath, self._file_format, **self._save_args)

    def _exists(self) -> bool:
        try:
            self._get_spark().read.load(self._filepath, self._file_format)
        except AnalysisException as exception:
            if exception.desc.startswith("Path does not exist:"):
                return False
            raise
        return True

    def __getstate__(self):
        raise pickle.PicklingError("PySpark datasets can't be serialized")
