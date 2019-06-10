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

import tempfile
from os import listdir
from os.path import exists, join

import pandas as pd
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col  # pylint: disable=no-name-in-module
from pyspark.sql.types import IntegerType, StringType, StructField, StructType
from pyspark.sql.utils import AnalysisException

from kedro.contrib.io.pyspark import SparkDataSet
from kedro.io import CSVLocalDataSet, DataSetError, ParquetLocalDataSet


# all the tests in this file require Spark
@pytest.fixture(autouse=True)
def spark_session(spark_session):
    return spark_session


def _get_sample_pandas_data_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {"Name": ["Alex", "Bob", "Clarke", "Dave"], "Age": [31, 12, 65, 29]}
    )


def _get_sample_spark_data_frame():
    schema = StructType(
        [
            StructField("name", StringType(), True),
            StructField("age", IntegerType(), True),
        ]
    )

    data = [("Alex", 31), ("Bob", 12), ("Clarke", 65), ("Dave", 29)]

    return SparkSession.builder.getOrCreate().createDataFrame(data, schema)


def test_load_parquet(tmpdir):
    temp_path = str(tmpdir.join("data"))
    pandas_df = _get_sample_pandas_data_frame()
    local_parquet_set = ParquetLocalDataSet(filepath=temp_path)
    local_parquet_set.save(pandas_df)
    spark_data_set = SparkDataSet(filepath=temp_path)
    spark_df = spark_data_set.load()
    assert spark_df.count() == 4


def test_save_parquet():
    # To cross check the correct Spark save operation we save to
    # a single spark partition and retrieve it with Kedro
    # ParquetLocalDataSet
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = join(temp_dir, "test_data")
        spark_data_set = SparkDataSet(
            filepath=temp_path, save_args={"compression": "none"}
        )
        spark_df = _get_sample_spark_data_frame().coalesce(1)
        spark_data_set.save(spark_df)

        single_parquet = [
            join(temp_path, f) for f in listdir(temp_path) if f.startswith("part")
        ][0]

        local_parquet_data_set = ParquetLocalDataSet(filepath=single_parquet)

        pandas_df = local_parquet_data_set.load()

        assert pandas_df[pandas_df["name"] == "Bob"]["age"].iloc[0] == 12


def test_load_options_csv(tmpdir):
    temp_path = str(tmpdir.join("data"))
    pandas_df = _get_sample_pandas_data_frame()
    local_csv_data_set = CSVLocalDataSet(filepath=temp_path)
    local_csv_data_set.save(pandas_df)
    spark_data_set = SparkDataSet(
        filepath=temp_path, file_format="csv", load_args={"header": True}
    )
    spark_df = spark_data_set.load()
    assert spark_df.filter(col("Name") == "Alex").count() == 1


def test_save_options_csv():
    # To cross check the correct Spark save operation we save to
    # a single spark partition with csv format and retrieve it with Kedro
    # CSVLocalDataSet
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = join(temp_dir, "test_data")
        spark_data_set = SparkDataSet(
            filepath=temp_path,
            file_format="csv",
            save_args={"sep": "|", "header": True},
        )
        spark_df = _get_sample_spark_data_frame().coalesce(1)
        spark_data_set.save(spark_df)

        single_csv_file = [
            join(temp_path, f) for f in listdir(temp_path) if f.endswith("csv")
        ][0]

        csv_local_data_set = CSVLocalDataSet(
            filepath=single_csv_file, load_args={"sep": "|"}
        )
        pandas_df = csv_local_data_set.load()

        assert pandas_df[pandas_df["name"] == "Alex"]["age"][0] == 31


def test_str_representation():
    with tempfile.NamedTemporaryFile() as temp_data_file:
        spark_data_set = SparkDataSet(
            filepath=temp_data_file.name, file_format="csv", load_args={"header": True}
        )
        assert "SparkDataSet" in str(spark_data_set)
        assert "filepath={}".format(temp_data_file.name) in str(spark_data_set)


def test_save_overwrite():
    # This test is split into two sections.
    # Firstly, it writes a data frame twice and expects it to fail.
    # Secondly, it writes a data frame with overwrite mode.

    with pytest.raises(DataSetError):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = join(temp_dir, "test_data")
            spark_data_set = SparkDataSet(filepath=temp_path)

            spark_df = _get_sample_spark_data_frame()
            spark_data_set.save(spark_df)
            spark_data_set.save(spark_df)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = join(temp_dir, "test_data")
        spark_data_set = SparkDataSet(
            filepath=temp_path, save_args={"mode": "overwrite"}
        )

        spark_df = _get_sample_spark_data_frame()
        spark_data_set.save(spark_df)
        spark_data_set.save(spark_df)


def test_save_partition():
    # To verify partitioning this test with partition data
    # and checked whether paritioned column is added to the
    # path

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = join(temp_dir, "test_data")
        spark_data_set = SparkDataSet(
            filepath=temp_path, save_args={"mode": "overwrite", "partitionBy": ["name"]}
        )

        spark_df = _get_sample_spark_data_frame()
        spark_data_set.save(spark_df)

        expected_path = join(temp_path, "name=Alex")

        assert exists(expected_path)


@pytest.mark.parametrize("file_format", ["csv", "parquet"])
def test_exists(file_format):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = join(temp_dir, "test_data")
        spark_data_set = SparkDataSet(filepath=temp_path, file_format=file_format)
        spark_df = _get_sample_spark_data_frame().coalesce(1)

        assert not spark_data_set.exists()

        spark_data_set.save(spark_df)
        assert spark_data_set.exists()


def test_exists_raises_error(monkeypatch):
    # exists should raise all errors except for
    # AnalysisExceptions clearly indicating a missing file
    def faulty_get_spark():
        raise AnalysisException("Other Exception", [])

    spark_data_set = SparkDataSet(filepath="")
    monkeypatch.setattr(spark_data_set, "_get_spark", faulty_get_spark)

    with pytest.raises(DataSetError) as error:
        spark_data_set.exists()
    assert "Other Exception" in str(error.value)


def test_cant_pickle():
    import pickle

    with pytest.raises(pickle.PicklingError):
        pickle.dumps(SparkDataSet("bob"))
