# pylint: disable=no-member
from pathlib import PosixPath
from unittest.mock import ANY

import pandas as pd
import pytest
import sqlalchemy

from kedro.extras.datasets.pandas import SQLQueryDataSet, SQLTableDataSet
from kedro.io import DatasetError

TABLE_NAME = "table_a"
CONNECTION = "sqlite:///kedro.db"
SQL_QUERY = "SELECT * FROM table_a"
EXECUTION_OPTIONS = {"stream_results": True}
FAKE_CONN_STR = "some_sql://scott:tiger@localhost/foo"
ERROR_PREFIX = (
    r"A module\/driver is missing when connecting to your SQL server\.(.|\n)*"
)


@pytest.fixture(autouse=True)
def cleanup_engines():
    yield
    SQLTableDataSet.engines = {}
    SQLQueryDataSet.engines = {}


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def sql_file(tmp_path: PosixPath):
    file = tmp_path / "test.sql"
    file.write_text(SQL_QUERY)
    return file.as_posix()


@pytest.fixture(params=[{}])
def table_data_set(request):
    kwargs = {"table_name": TABLE_NAME, "credentials": {"con": CONNECTION}}
    kwargs.update(request.param)
    return SQLTableDataSet(**kwargs)


@pytest.fixture(params=[{}])
def query_data_set(request):
    kwargs = {"sql": SQL_QUERY, "credentials": {"con": CONNECTION}}
    kwargs.update(request.param)
    return SQLQueryDataSet(**kwargs)


@pytest.fixture(params=[{}])
def query_file_data_set(request, sql_file):
    kwargs = {"filepath": sql_file, "credentials": {"con": CONNECTION}}
    kwargs.update(request.param)
    return SQLQueryDataSet(**kwargs)


class TestSQLTableDataSet:
    _unknown_conn = "mysql+unknown_module://scott:tiger@localhost/foo"

    @staticmethod
    def _assert_sqlalchemy_called_once(*args):
        _callable = sqlalchemy.engine.Engine.table_names
        if args:
            _callable.assert_called_once_with(*args)
        else:
            assert _callable.call_count == 1

    def test_empty_table_name(self):
        """Check the error when instantiating with an empty table"""
        pattern = r"'table\_name' argument cannot be empty\."
        with pytest.raises(DatasetError, match=pattern):
            SQLTableDataSet(table_name="", credentials={"con": CONNECTION})

    def test_empty_connection(self):
        """Check the error when instantiating with an empty
        connection string"""
        pattern = (
            r"'con' argument cannot be empty\. "
            r"Please provide a SQLAlchemy connection string\."
        )
        with pytest.raises(DatasetError, match=pattern):
            SQLTableDataSet(table_name=TABLE_NAME, credentials={"con": ""})

    def test_driver_missing(self, mocker):
        """Check the error when the sql driver is missing"""
        mocker.patch(
            "kedro.extras.datasets.pandas.sql_dataset.create_engine",
            side_effect=ImportError("No module named 'mysqldb'"),
        )
        with pytest.raises(DatasetError, match=ERROR_PREFIX + "mysqlclient"):
            SQLTableDataSet(table_name=TABLE_NAME, credentials={"con": CONNECTION})

    def test_unknown_sql(self):
        """Check the error when unknown sql dialect is provided;
        this means the error is raised on catalog creation, rather
        than on load or save operation.
        """
        pattern = r"The SQL dialect in your connection is not supported by SQLAlchemy"
        with pytest.raises(DatasetError, match=pattern):
            SQLTableDataSet(table_name=TABLE_NAME, credentials={"con": FAKE_CONN_STR})

    def test_unknown_module(self, mocker):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        mocker.patch(
            "kedro.extras.datasets.pandas.sql_dataset.create_engine",
            side_effect=ImportError("No module named 'unknown_module'"),
        )
        pattern = ERROR_PREFIX + r"No module named \'unknown\_module\'"
        with pytest.raises(DatasetError, match=pattern):
            SQLTableDataSet(table_name=TABLE_NAME, credentials={"con": CONNECTION})

    def test_str_representation_table(self, table_data_set):
        """Test the data set instance string representation"""
        str_repr = str(table_data_set)
        assert (
            "SQLTableDataSet(load_args={}, save_args={'index': False}, "
            f"table_name={TABLE_NAME})" in str_repr
        )
        assert CONNECTION not in str(str_repr)

    def test_table_exists(self, mocker, table_data_set):
        """Test `exists` method invocation"""
        mocker.patch("sqlalchemy.engine.Engine.table_names")
        assert not table_data_set.exists()
        self._assert_sqlalchemy_called_once()

    @pytest.mark.parametrize(
        "table_data_set", [{"load_args": {"schema": "ingested"}}], indirect=True
    )
    def test_table_exists_schema(self, mocker, table_data_set):
        """Test `exists` method invocation with DB schema provided"""
        mocker.patch("sqlalchemy.engine.Engine.table_names")
        assert not table_data_set.exists()
        self._assert_sqlalchemy_called_once("ingested")

    def test_table_exists_mocked(self, mocker, table_data_set):
        """Test `exists` method invocation with mocked list of tables"""
        mocker.patch("sqlalchemy.engine.Engine.table_names", return_value=[TABLE_NAME])
        assert table_data_set.exists()
        self._assert_sqlalchemy_called_once()

    def test_load_sql_params(self, mocker, table_data_set):
        """Test `load` method invocation"""
        mocker.patch("pandas.read_sql_table")
        table_data_set.load()
        pd.read_sql_table.assert_called_once_with(
            table_name=TABLE_NAME, con=table_data_set.engines[CONNECTION]
        )

    def test_save_default_index(self, mocker, table_data_set, dummy_dataframe):
        """Test `save` method invocation"""
        mocker.patch.object(dummy_dataframe, "to_sql")
        table_data_set.save(dummy_dataframe)
        dummy_dataframe.to_sql.assert_called_once_with(
            name=TABLE_NAME, con=table_data_set.engines[CONNECTION], index=False
        )

    @pytest.mark.parametrize(
        "table_data_set", [{"save_args": {"index": True}}], indirect=True
    )
    def test_save_overwrite_index(self, mocker, table_data_set, dummy_dataframe):
        """Test writing DataFrame index as a column"""
        mocker.patch.object(dummy_dataframe, "to_sql")
        table_data_set.save(dummy_dataframe)
        dummy_dataframe.to_sql.assert_called_once_with(
            name=TABLE_NAME, con=table_data_set.engines[CONNECTION], index=True
        )

    @pytest.mark.parametrize(
        "table_data_set", [{"save_args": {"name": "TABLE_B"}}], indirect=True
    )
    def test_save_ignore_table_name_override(
        self, mocker, table_data_set, dummy_dataframe
    ):
        """Test that putting the table name is `save_args` does not have any
        effect"""
        mocker.patch.object(dummy_dataframe, "to_sql")
        table_data_set.save(dummy_dataframe)
        dummy_dataframe.to_sql.assert_called_once_with(
            name=TABLE_NAME, con=table_data_set.engines[CONNECTION], index=False
        )


class TestSQLTableDataSetSingleConnection:
    def test_single_connection(self, dummy_dataframe, mocker):
        """Test to make sure multiple instances use the same connection object."""
        mocker.patch("pandas.read_sql_table")
        dummy_to_sql = mocker.patch.object(dummy_dataframe, "to_sql")
        kwargs = {"table_name": TABLE_NAME, "credentials": {"con": CONNECTION}}

        first = SQLTableDataSet(**kwargs)
        unique_connection = first.engines[CONNECTION]
        datasets = [SQLTableDataSet(**kwargs) for _ in range(10)]

        for ds in datasets:
            ds.save(dummy_dataframe)
            engine = ds.engines[CONNECTION]
            assert engine is unique_connection

        expected_call = mocker.call(name=TABLE_NAME, con=unique_connection, index=False)
        dummy_to_sql.assert_has_calls([expected_call] * 10)

        for ds in datasets:
            ds.load()
            engine = ds.engines[CONNECTION]
            assert engine is unique_connection

    def test_create_connection_only_once(self, mocker):
        """Test that two datasets that need to connect to the same db
        (but different tables, for example) only create a connection once.
        """
        mock_engine = mocker.patch(
            "kedro.extras.datasets.pandas.sql_dataset.create_engine"
        )
        first = SQLTableDataSet(table_name=TABLE_NAME, credentials={"con": CONNECTION})
        assert len(first.engines) == 1

        second = SQLTableDataSet(
            table_name="other_table", credentials={"con": CONNECTION}
        )
        assert len(second.engines) == 1
        assert len(first.engines) == 1

        mock_engine.assert_called_once_with(CONNECTION)

    def test_multiple_connections(self, mocker):
        """Test that two datasets that need to connect to different dbs
        only create one connection per db.
        """
        mock_engine = mocker.patch(
            "kedro.extras.datasets.pandas.sql_dataset.create_engine"
        )
        first = SQLTableDataSet(table_name=TABLE_NAME, credentials={"con": CONNECTION})
        assert len(first.engines) == 1

        second_con = f"other_{CONNECTION}"
        second = SQLTableDataSet(table_name=TABLE_NAME, credentials={"con": second_con})
        assert len(second.engines) == 2
        assert len(first.engines) == 2

        expected_calls = [mocker.call(CONNECTION), mocker.call(second_con)]
        assert mock_engine.call_args_list == expected_calls


class TestSQLQueryDataSet:
    def test_empty_query_error(self):
        """Check the error when instantiating with empty query or file"""
        pattern = (
            r"'sql' and 'filepath' arguments cannot both be empty\."
            r"Please provide a sql query or path to a sql query file\."
        )
        with pytest.raises(DatasetError, match=pattern):
            SQLQueryDataSet(sql="", filepath="", credentials={"con": CONNECTION})

    def test_empty_con_error(self):
        """Check the error when instantiating with empty connection string"""
        pattern = (
            r"'con' argument cannot be empty\. Please provide "
            r"a SQLAlchemy connection string"
        )
        with pytest.raises(DatasetError, match=pattern):
            SQLQueryDataSet(sql=SQL_QUERY, credentials={"con": ""})

    @pytest.mark.parametrize(
        "query_data_set, has_execution_options",
        [
            ({"execution_options": EXECUTION_OPTIONS}, True),
            ({"execution_options": {}}, False),
            ({}, False),
        ],
        indirect=["query_data_set"],
    )
    def test_load(self, mocker, query_data_set, has_execution_options):
        """Test `load` method invocation"""
        mocker.patch("pandas.read_sql_query")
        query_data_set.load()

        # Check that data was loaded with the expected query, connection string and
        # execution options:
        pd.read_sql_query.assert_called_once_with(sql=SQL_QUERY, con=ANY)
        con_arg = pd.read_sql_query.call_args_list[0][1]["con"]
        assert str(con_arg.url) == CONNECTION
        assert len(con_arg.get_execution_options()) == bool(has_execution_options)
        if has_execution_options:
            assert con_arg.get_execution_options() == EXECUTION_OPTIONS

    @pytest.mark.parametrize(
        "query_file_data_set, has_execution_options",
        [
            ({"execution_options": EXECUTION_OPTIONS}, True),
            ({"execution_options": {}}, False),
            ({}, False),
        ],
        indirect=["query_file_data_set"],
    )
    def test_load_query_file(self, mocker, query_file_data_set, has_execution_options):
        """Test `load` method with a query file"""
        mocker.patch("pandas.read_sql_query")
        query_file_data_set.load()

        # Check that data was loaded with the expected query, connection string and
        # execution options:
        pd.read_sql_query.assert_called_once_with(sql=SQL_QUERY, con=ANY)
        con_arg = pd.read_sql_query.call_args_list[0][1]["con"]
        assert str(con_arg.url) == CONNECTION
        assert len(con_arg.get_execution_options()) == bool(has_execution_options)
        if has_execution_options:
            assert con_arg.get_execution_options() == EXECUTION_OPTIONS

    def test_load_driver_missing(self, mocker):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        _err = ImportError("No module named 'mysqldb'")
        mocker.patch(
            "kedro.extras.datasets.pandas.sql_dataset.create_engine", side_effect=_err
        )
        with pytest.raises(DatasetError, match=ERROR_PREFIX + "mysqlclient"):
            SQLQueryDataSet(sql=SQL_QUERY, credentials={"con": CONNECTION})

    def test_invalid_module(self, mocker):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        _err = ImportError("Invalid module some_module")
        mocker.patch(
            "kedro.extras.datasets.pandas.sql_dataset.create_engine", side_effect=_err
        )
        pattern = ERROR_PREFIX + r"Invalid module some\_module"
        with pytest.raises(DatasetError, match=pattern):
            SQLQueryDataSet(sql=SQL_QUERY, credentials={"con": CONNECTION})

    def test_load_unknown_module(self, mocker):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        _err = ImportError("No module named 'unknown_module'")
        mocker.patch(
            "kedro.extras.datasets.pandas.sql_dataset.create_engine", side_effect=_err
        )
        pattern = ERROR_PREFIX + r"No module named \'unknown\_module\'"
        with pytest.raises(DatasetError, match=pattern):
            SQLQueryDataSet(sql=SQL_QUERY, credentials={"con": CONNECTION})

    def test_load_unknown_sql(self):
        """Check the error when unknown SQL dialect is provided
        in the connection string"""
        pattern = r"The SQL dialect in your connection is not supported by SQLAlchemy"
        with pytest.raises(DatasetError, match=pattern):
            SQLQueryDataSet(sql=SQL_QUERY, credentials={"con": FAKE_CONN_STR})

    def test_save_error(self, query_data_set, dummy_dataframe):
        """Check the error when trying to save to the data set"""
        pattern = r"'save' is not supported on SQLQueryDataSet"
        with pytest.raises(DatasetError, match=pattern):
            query_data_set.save(dummy_dataframe)

    def test_str_representation_sql(self, query_data_set, sql_file):
        """Test the data set instance string representation"""
        str_repr = str(query_data_set)
        assert (
            "SQLQueryDataSet(execution_options={}, filepath=None, "
            f"load_args={{}}, sql={SQL_QUERY})" in str_repr
        )
        assert CONNECTION not in str_repr
        assert sql_file not in str_repr

    def test_str_representation_filepath(self, query_file_data_set, sql_file):
        """Test the data set instance string representation with filepath arg."""
        str_repr = str(query_file_data_set)
        assert (
            f"SQLQueryDataSet(execution_options={{}}, filepath={str(sql_file)}, "
            "load_args={}, sql=None)" in str_repr
        )
        assert CONNECTION not in str_repr
        assert SQL_QUERY not in str_repr

    def test_sql_and_filepath_args(self, sql_file):
        """Test that an error is raised when both `sql` and `filepath` args are given."""
        pattern = (
            r"'sql' and 'filepath' arguments cannot both be provided."
            r"Please only provide one."
        )
        with pytest.raises(DatasetError, match=pattern):
            SQLQueryDataSet(sql=SQL_QUERY, filepath=sql_file)

    def test_create_connection_only_once(self, mocker):
        """Test that two datasets that need to connect to the same db (but different
        tables and execution options, for example) only create a connection once.
        """
        mock_engine = mocker.patch(
            "kedro.extras.datasets.pandas.sql_dataset.create_engine"
        )
        first = SQLQueryDataSet(sql=SQL_QUERY, credentials={"con": CONNECTION})
        assert len(first.engines) == 1

        # second engine has identical params to the first one
        # => no new engine should be created
        second = SQLQueryDataSet(sql=SQL_QUERY, credentials={"con": CONNECTION})
        mock_engine.assert_called_once_with(CONNECTION)
        assert second.engines == first.engines
        assert len(first.engines) == 1

        # third engine only differs by its query execution options
        # => no new engine should be created
        third = SQLQueryDataSet(
            sql="a different query",
            credentials={"con": CONNECTION},
            execution_options=EXECUTION_OPTIONS,
        )
        assert mock_engine.call_count == 1
        assert third.engines == first.engines
        assert len(first.engines) == 1

        # fourth engine has a different connection string
        # => a new engine has to be created
        fourth = SQLQueryDataSet(
            sql=SQL_QUERY, credentials={"con": "an other connection string"}
        )
        assert mock_engine.call_count == 2
        assert fourth.engines == first.engines
        assert len(first.engines) == 2
