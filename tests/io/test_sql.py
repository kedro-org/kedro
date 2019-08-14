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

# pylint: disable=no-member

from typing import Any

import pandas as pd
import pytest
import sqlalchemy

from kedro.io import DataSetError, SQLQueryDataSet, SQLTableDataSet

TABLE_NAME = "table_a"
CONNECTION = "sqlite:///kedro.db"
SQL_QUERY = "SELECT * FROM table_a"
FAKE_CONN_STR = "some_sql://scott:tiger@localhost/foo"
ERROR_PREFIX = (
    r"A module\/driver is missing when connecting to your " r"SQL server\.(.|\n)*"
)


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture(params=[dict()])
def table_data_set(request):
    kwargs = dict(table_name=TABLE_NAME, credentials=dict(con=CONNECTION))
    kwargs.update(request.param)
    return SQLTableDataSet(**kwargs)


@pytest.fixture(params=[dict()])
def query_data_set(request):
    kwargs = dict(sql=SQL_QUERY, credentials=dict(con=CONNECTION))
    kwargs.update(request.param)
    return SQLQueryDataSet(**kwargs)


class TestSQLTableDataSetLoad:
    @staticmethod
    def _assert_pd_called_once():
        pd.read_sql_table.assert_called_once_with(table_name=TABLE_NAME, con=CONNECTION)

    def test_empty_table_name(self):
        """Check the error when instantiating with an empty table"""
        pattern = r"`table\_name` argument cannot be empty\."
        with pytest.raises(DataSetError, match=pattern):
            SQLTableDataSet(table_name="", credentials=dict(con=CONNECTION))

    def test_empty_connection(self):
        """Check the error when instantiating with an empty
        connection string"""
        pattern = (
            r"`con` argument cannot be empty\. "
            r"Please provide a SQLAlchemy connection string\."
        )
        with pytest.raises(DataSetError, match=pattern):
            SQLTableDataSet(table_name=TABLE_NAME, credentials=dict(con=""))

    def test_load_sql_params(self, mocker, table_data_set):
        """Test `load` method invocation"""
        mocker.patch("pandas.read_sql_table")
        table_data_set.load()
        self._assert_pd_called_once()

    def test_load_driver_missing(self, mocker, table_data_set):
        """Check the error when the sql driver is missing"""
        mocker.patch(
            "pandas.read_sql_table",
            side_effect=ImportError("No module named 'mysqldb'"),
        )
        with pytest.raises(DataSetError, match=ERROR_PREFIX + "mysqlclient"):
            table_data_set.load()
        self._assert_pd_called_once()

    def test_invalid_module(self, mocker, table_data_set):
        """Test that if an invalid module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        _err = ImportError("Invalid module some_module")
        mocker.patch("pandas.read_sql_table", side_effect=_err)
        pattern = ERROR_PREFIX + r"Invalid module some\_module"
        with pytest.raises(DataSetError, match=pattern):
            table_data_set.load()
        self._assert_pd_called_once()

    def test_load_unknown_module(self, mocker, table_data_set):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        mocker.patch(
            "pandas.read_sql_table",
            side_effect=ImportError("No module named 'unknown_module'"),
        )
        pattern = ERROR_PREFIX + r"No module named \'unknown\_module\'"
        with pytest.raises(DataSetError, match=pattern):
            table_data_set.load()

    @pytest.mark.parametrize(
        "table_data_set", [{"credentials": dict(con=FAKE_CONN_STR)}], indirect=True
    )
    def test_load_unknown_sql(self, table_data_set):
        """Check the error when unknown sql dialect is provided"""
        pattern = (
            r"The SQL dialect in your connection is not supported " r"by SQLAlchemy"
        )
        with pytest.raises(DataSetError, match=pattern):
            table_data_set.load()


class TestSQLTableDataSetSave:
    _unknown_conn = "mysql+unknown_module://scott:tiger@localhost/foo"

    @staticmethod
    def _assert_to_sql_called_once(df: Any, index: bool = False):
        df.to_sql.assert_called_once_with(name=TABLE_NAME, con=CONNECTION, index=index)

    def test_save_default_index(self, mocker, table_data_set, dummy_dataframe):
        """Test `save` method invocation"""
        mocker.patch.object(dummy_dataframe, "to_sql")
        table_data_set.save(dummy_dataframe)
        self._assert_to_sql_called_once(dummy_dataframe)

    @pytest.mark.parametrize(
        "table_data_set", [{"save_args": dict(index=True)}], indirect=True
    )
    def test_save_overwrite_index(self, mocker, table_data_set, dummy_dataframe):
        """Test writing DataFrame index as a column"""
        mocker.patch.object(dummy_dataframe, "to_sql")
        table_data_set.save(dummy_dataframe)
        self._assert_to_sql_called_once(dummy_dataframe, True)

    def test_save_driver_missing(self, mocker, table_data_set, dummy_dataframe):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        _err = ImportError("No module named 'mysqldb'")
        mocker.patch.object(dummy_dataframe, "to_sql", side_effect=_err)
        with pytest.raises(DataSetError, match=ERROR_PREFIX + "mysqlclient"):
            table_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "table_data_set", [{"credentials": dict(con=FAKE_CONN_STR)}], indirect=True
    )
    def test_save_unknown_sql(self, table_data_set, dummy_dataframe):
        """Check the error when unknown sql dialect is provided"""
        pattern = (
            r"The SQL dialect in your connection is not supported " r"by SQLAlchemy"
        )
        with pytest.raises(DataSetError, match=pattern):
            table_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "table_data_set", [{"credentials": dict(con=_unknown_conn)}], indirect=True
    )
    def test_save_unknown_module(self, mocker, table_data_set, dummy_dataframe):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        _err = ImportError("No module named 'unknown_module'")
        mocker.patch.object(dummy_dataframe, "to_sql", side_effect=_err)
        pattern = r"No module named \'unknown_module\'"
        with pytest.raises(DataSetError, match=pattern):
            table_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "table_data_set", [{"save_args": dict(name="TABLE_B")}], indirect=True
    )
    def test_save_ignore_table_name_override(
        self, mocker, table_data_set, dummy_dataframe
    ):
        """Test that putting the table name is `save_args` does not have any
        effect"""
        mocker.patch.object(dummy_dataframe, "to_sql")
        table_data_set.save(dummy_dataframe)
        self._assert_to_sql_called_once(dummy_dataframe)


class TestSQLTableDataSet:
    @staticmethod
    def _assert_sqlalchemy_called_once(*args):
        _callable = sqlalchemy.engine.Engine.table_names
        if args:
            _callable.assert_called_once_with(*args)
        else:
            assert _callable.call_count == 1

    def test_str_representation_table(self, table_data_set):
        """Test the data set instance string representation"""
        str_repr = str(table_data_set)
        assert (
            "SQLTableDataSet(save_args={'index': False}, table_name=%s)" % TABLE_NAME
            in str_repr
        )
        assert CONNECTION not in str(str_repr)

    def test_table_exists(self, mocker, table_data_set):
        """Test `exists` method invocation"""
        mocker.patch("sqlalchemy.engine.Engine.table_names")
        assert not table_data_set.exists()
        self._assert_sqlalchemy_called_once()

    @pytest.mark.parametrize(
        "table_data_set", [{"load_args": dict(schema="ingested")}], indirect=True
    )
    def test_able_exists_schema(self, mocker, table_data_set):
        """Test `exists` method invocation with DB schema provided"""
        mocker.patch("sqlalchemy.engine.Engine.table_names")
        assert not table_data_set.exists()
        self._assert_sqlalchemy_called_once("ingested")

    def test_table_exists_mocked(self, mocker, table_data_set):
        """Test `exists` method invocation with mocked list of tables"""
        mocker.patch("sqlalchemy.engine.Engine.table_names", return_value=[TABLE_NAME])
        assert table_data_set.exists()
        self._assert_sqlalchemy_called_once()


class TestSQLQueryDataSet:
    @staticmethod
    def _assert_pd_called_once():
        _callable = pd.read_sql_query
        _callable.assert_called_once_with(sql=SQL_QUERY, con=CONNECTION)

    def test_empty_query_error(self):
        """Check the error when instantiating with empty query"""
        pattern = r"`sql` argument cannot be empty\. " r"Please provide a sql query"
        with pytest.raises(DataSetError, match=pattern):
            SQLQueryDataSet(sql="", credentials=dict(con=CONNECTION))

    def test_empty_con_error(self):
        """Check the error when instantiating with empty connection string"""
        pattern = (
            r"`con` argument cannot be empty\. Please provide "
            r"a SQLAlchemy connection string"
        )
        with pytest.raises(DataSetError, match=pattern):
            SQLQueryDataSet(sql=SQL_QUERY, credentials=dict(con=""))

    def test_load(self, mocker, query_data_set):
        """Test `load` method invocation"""
        mocker.patch("pandas.read_sql_query")
        query_data_set.load()
        self._assert_pd_called_once()

    def test_load_driver_missing(self, mocker, query_data_set):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        _err = ImportError("No module named 'mysqldb'")
        mocker.patch("pandas.read_sql_query", side_effect=_err)
        with pytest.raises(DataSetError, match=ERROR_PREFIX + "mysqlclient"):
            query_data_set.load()

    def test_invalid_module(self, mocker, query_data_set):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        _err = ImportError("Invalid module some_module")
        mocker.patch("pandas.read_sql_query", side_effect=_err)
        pattern = ERROR_PREFIX + r"Invalid module some\_module"
        with pytest.raises(DataSetError, match=pattern):
            query_data_set.load()

    def test_load_unknown_module(self, mocker, query_data_set):
        """Test that if an unknown module/driver is encountered by SQLAlchemy
        then the error should contain the original error message"""
        _err = ImportError("No module named 'unknown_module'")
        mocker.patch("pandas.read_sql_query", side_effect=_err)
        pattern = ERROR_PREFIX + r"No module named \'unknown\_module\'"
        with pytest.raises(DataSetError, match=pattern):
            query_data_set.load()

    @pytest.mark.parametrize(
        "query_data_set", [{"credentials": dict(con=FAKE_CONN_STR)}], indirect=True
    )
    def test_load_unknown_sql(self, query_data_set):
        """Check the error when unknown SQL dialect is provided
        in the connection string"""
        pattern = (
            r"The SQL dialect in your connection is not supported " r"by SQLAlchemy"
        )
        with pytest.raises(DataSetError, match=pattern):
            query_data_set.load()

    def test_save_error(self, query_data_set, dummy_dataframe):
        """Check the error when trying to save to the data set"""
        pattern = r"`save` is not supported on SQLQueryDataSet"
        with pytest.raises(DataSetError, match=pattern):
            query_data_set.save(dummy_dataframe)

    def test_str_representation_sql(self, query_data_set):
        """Test the data set instance string representation"""
        str_repr = str(query_data_set)
        assert "SQLQueryDataSet(sql={})".format(SQL_QUERY) in str_repr
        assert CONNECTION not in str_repr
