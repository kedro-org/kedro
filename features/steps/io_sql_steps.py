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
"""Behave step definitions for the io core features."""

from pathlib import Path

import pandas as pd
from behave import given, then, when

from kedro.io import SQLQueryDataSet, SQLTableDataSet

TABLE_A = "A"
TABLE_B = "B"
TABLE_C = "C"


def _get_sample_data():
    data = {"id": [1, 2], "name": ["me", "you"]}
    return pd.DataFrame(data)


def _get_test_sql_con():
    return "sqlite:///kedro.db"


def _clear_db_():
    try:
        Path("kedro.db").unlink()
    except FileNotFoundError:
        pass


def _prepare_read_samples():
    _clear_db_()
    data_set = SQLTableDataSet(
        table_name=TABLE_A, credentials=dict(con=_get_test_sql_con())
    )
    data_set.save(_get_sample_data())


@given("I have defined an SQL data set with tables A and B")
def prepare_sql_data(context):
    _prepare_read_samples()
    context.data_set_a = SQLTableDataSet(
        table_name=TABLE_A, credentials=dict(con=_get_test_sql_con())
    )
    context.data_set_b = SQLTableDataSet(
        table_name=TABLE_B, credentials=dict(con=_get_test_sql_con())
    )


@given("I have defined an SQL query data set with filtered query to table C")
def prepare_sql_query(context):
    sample_data = _get_sample_data()
    table_data_set = SQLTableDataSet(
        table_name=TABLE_C, credentials=dict(con=_get_test_sql_con())
    )

    table_data_set.save(sample_data)
    sql = "SELECT * FROM C WHERE name='me'"
    context.query_data_set = SQLQueryDataSet(
        sql=sql, credentials=dict(con=_get_test_sql_con())
    )


@when("I load from table A")
def read_from_sql_data_set(context):
    context.result = context.data_set_a.load()


@when("I save to table B")
def write_to_sql_data_set(context):
    context.data_set_b.save(data=_get_sample_data())


@when("I query table C")
def read_query_data_set(context):
    context.filtered_query_data = context.query_data_set.load()


@then("I should get the expected number of rows back")
def expected_number_of_rows(context):
    assert len(context.result) == 2


@then("I should get the filtered rows back")
def expected_number_filtered_rows(context):
    assert len(context.filtered_query_data) == 1


@then("I should get the written data back")
def read_written_data(context):
    # pylint: disable=unused-argument

    data_set = SQLTableDataSet(
        table_name=TABLE_B, credentials=dict(con=_get_test_sql_con())
    )
    result = data_set.load()
    assert result.equals(_get_sample_data())
