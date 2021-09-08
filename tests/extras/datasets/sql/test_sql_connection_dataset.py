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

# pylint: disable=no-member

import pytest
import sqlalchemy

from kedro.extras.datasets.sql import SQLConnectionDataSet
from kedro.io.core import DataSetError

CONNECTION = "sqlite:///kedro.db"
FAKE_CONNECTION = "foo:///user:pass@localhost/bar"


@pytest.fixture(params=[{}])
def connection_data_set(request):
    kwargs = dict(credentials=dict(con=CONNECTION))
    kwargs.update(request.param)
    return SQLConnectionDataSet(**kwargs)


@pytest.fixture
def fake_connection_data_set():
    return SQLConnectionDataSet(credentials=dict(con=FAKE_CONNECTION))


class TestSQLConnectionDataSetLoad:
    @staticmethod
    def _assert_engine_created():
        _callable = sqlalchemy.create_engine
        _callable.assert_called_once_with(CONNECTION)

    @staticmethod
    def _assert_engine_connect_called():
        _callable = sqlalchemy.engine.Engine.connect
        _callable.assert_called_once()

    def test_no_credentials(self):
        """Check the error when instantiating with no credentials."""
        pattern = (
            r"`con` argument cannot be empty. Please provide a SQLAlchemy"
            r"connection string."
        )
        with pytest.raises(DataSetError, match=pattern):
            SQLConnectionDataSet(credentials=dict())

    def test_empty_connection(self):
        """Check the error when instantiating with an empty connection string."""
        pattern = (
            r"`con` argument cannot be empty. Please provide a SQLAlchemy"
            r"connection string."
        )
        with pytest.raises(DataSetError, match=pattern):
            SQLConnectionDataSet(credentials=dict(con=""))

    def test_invalid_connection(self, fake_connection_data_set):
        """Check the error when instantiating with an invalid connection string."""
        pattern = r"Provided connection string is invalid. Please check credentials\."
        with pytest.raises(DataSetError, match=pattern):
            fake_connection_data_set.load()

    def test_load_connection(self, mocker, connection_data_set):
        """Check that the connection is correctly loaded"""
        mocker.patch("sqlalchemy.engine.Engine.connect")
        connection_data_set.load()
        self._assert_engine_connect_called()

    def test_load_returns_conn(self, connection_data_set):
        """Check that the connection is correctly loaded and returned with
        the correct connection string"""
        conn = connection_data_set.load()
        engine = conn.engine
        assert CONNECTION in str(engine)
