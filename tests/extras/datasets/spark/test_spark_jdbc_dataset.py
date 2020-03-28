# Copyright 2020 QuantumBlack Visual Analytics Limited
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
import sys
from unittest import mock

import pytest

from kedro.io import DataSetError
from tests.conftest import skip_if_py38

if sys.version_info < (3, 8):
    from kedro.extras.datasets.spark import (  # pylint: disable=import-error
        SparkJDBCDataSet,
    )
else:
    SparkJDBCDataSet = mock.ANY


@pytest.fixture
def spark_jdbc_args():
    return {"url": "dummy_url", "table": "dummy_table"}


@pytest.fixture
def spark_jdbc_args_credentials(spark_jdbc_args):
    args = spark_jdbc_args
    args.update({"credentials": {"user": "dummy_user", "password": "dummy_pw"}})
    return args


@pytest.fixture
def spark_jdbc_args_credentials_with_none_password(spark_jdbc_args):
    args = spark_jdbc_args
    args.update({"credentials": {"user": "dummy_user", "password": None}})
    return args


@pytest.fixture
def spark_jdbc_args_save_load(spark_jdbc_args):
    args = spark_jdbc_args
    connection_properties = {"properties": {"driver": "dummy_driver"}}
    args.update(
        {"save_args": connection_properties, "load_args": connection_properties}
    )
    return args


@skip_if_py38
def test_missing_url():
    error_message = (
        "`url` argument cannot be empty. Please provide a JDBC"
        " URL of the form ``jdbc:subprotocol:subname``."
    )
    with pytest.raises(DataSetError, match=error_message):
        SparkJDBCDataSet(url=None, table="dummy_table")


@skip_if_py38
def test_missing_table():
    error_message = (
        "`table` argument cannot be empty. Please provide"
        " the name of the table to load or save data to."
    )
    with pytest.raises(DataSetError, match=error_message):
        SparkJDBCDataSet(url="dummy_url", table=None)


def mock_save(arg_dict):
    mock_data = mock.Mock()
    data_set = SparkJDBCDataSet(**arg_dict)
    data_set.save(mock_data)
    return mock_data


@skip_if_py38
def test_save(spark_jdbc_args):
    data = mock_save(spark_jdbc_args)
    data.write.jdbc.assert_called_with("dummy_url", "dummy_table")


@skip_if_py38
def test_save_credentials(spark_jdbc_args_credentials):
    data = mock_save(spark_jdbc_args_credentials)
    data.write.jdbc.assert_called_with(
        "dummy_url",
        "dummy_table",
        properties={"user": "dummy_user", "password": "dummy_pw"},
    )


@skip_if_py38
def test_save_args(spark_jdbc_args_save_load):
    data = mock_save(spark_jdbc_args_save_load)
    data.write.jdbc.assert_called_with(
        "dummy_url", "dummy_table", properties={"driver": "dummy_driver"}
    )


@skip_if_py38
def test_except_bad_credentials(spark_jdbc_args_credentials_with_none_password):
    pattern = r"Credential property `password` cannot be None(.+)"
    with pytest.raises(DataSetError, match=pattern):
        mock_save(spark_jdbc_args_credentials_with_none_password)


@mock.patch(
    "kedro.extras.datasets.spark.spark_jdbc_dataset.SparkSession.builder.getOrCreate"
)
def mock_load(mock_get_or_create, arg_dict):
    spark = mock_get_or_create.return_value
    data_set = SparkJDBCDataSet(**arg_dict)
    data_set.load()
    return spark


@skip_if_py38
def test_load(spark_jdbc_args):
    # pylint: disable=no-value-for-parameter
    spark = mock_load(arg_dict=spark_jdbc_args)
    spark.read.jdbc.assert_called_with("dummy_url", "dummy_table")


@skip_if_py38
def test_load_credentials(spark_jdbc_args_credentials):
    # pylint: disable=no-value-for-parameter
    spark = mock_load(arg_dict=spark_jdbc_args_credentials)
    spark.read.jdbc.assert_called_with(
        "dummy_url",
        "dummy_table",
        properties={"user": "dummy_user", "password": "dummy_pw"},
    )


@skip_if_py38
def test_load_args(spark_jdbc_args_save_load):
    # pylint: disable=no-value-for-parameter
    spark = mock_load(arg_dict=spark_jdbc_args_save_load)
    spark.read.jdbc.assert_called_with(
        "dummy_url", "dummy_table", properties={"driver": "dummy_driver"}
    )
