from unittest import mock

import pytest

from kedro.extras.datasets.spark import SparkJDBCDataSet
from kedro.io import DataSetError


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


def test_missing_url():
    error_message = (
        "`url` argument cannot be empty. Please provide a JDBC"
        " URL of the form ``jdbc:subprotocol:subname``."
    )
    with pytest.raises(DataSetError, match=error_message):
        SparkJDBCDataSet(url=None, table="dummy_table")


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


def test_save(spark_jdbc_args):
    data = mock_save(spark_jdbc_args)
    data.write.jdbc.assert_called_with("dummy_url", "dummy_table")


def test_save_credentials(spark_jdbc_args_credentials):
    data = mock_save(spark_jdbc_args_credentials)
    data.write.jdbc.assert_called_with(
        "dummy_url",
        "dummy_table",
        properties={"user": "dummy_user", "password": "dummy_pw"},
    )


def test_save_args(spark_jdbc_args_save_load):
    data = mock_save(spark_jdbc_args_save_load)
    data.write.jdbc.assert_called_with(
        "dummy_url", "dummy_table", properties={"driver": "dummy_driver"}
    )


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


def test_load(spark_jdbc_args):
    # pylint: disable=no-value-for-parameter
    spark = mock_load(arg_dict=spark_jdbc_args)
    spark.read.jdbc.assert_called_with("dummy_url", "dummy_table")


def test_load_credentials(spark_jdbc_args_credentials):
    # pylint: disable=no-value-for-parameter
    spark = mock_load(arg_dict=spark_jdbc_args_credentials)
    spark.read.jdbc.assert_called_with(
        "dummy_url",
        "dummy_table",
        properties={"user": "dummy_user", "password": "dummy_pw"},
    )


def test_load_args(spark_jdbc_args_save_load):
    # pylint: disable=no-value-for-parameter
    spark = mock_load(arg_dict=spark_jdbc_args_save_load)
    spark.read.jdbc.assert_called_with(
        "dummy_url", "dummy_table", properties={"driver": "dummy_driver"}
    )
