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
"""``SQLConnectionDataSet`` to create a live connection to a SQL database."""

from typing import Any, Dict

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.exc import NoSuchModuleError

from kedro.io.core import AbstractDataSet, DataSetError


# TODO: (BL) need to test this class, write docstrings
class SQLConnectionDataSet(AbstractDataSet):
    """``SQLConnectionDataSet`` provides an sqlalchemy connection object to a
    SQL database backend. The load method creates and returns the connection
    object, which can be used in a function as normally in Python.

    [TBD] Save function options:
        1. Not implemented
        2. Calls the `execute` method

    Example:
    ::
        # to be written

    """

    def __init__(
        self, credentials: Dict[str, Any], load_args: Dict[str, Any] = None
    ) -> None:
        """Creates a new ``SQLConnectionDataSet``.

        Args:
            credentials (Dict[str, Any]): [description]
            load_args (Dict[str, Any], optional): [description]. Defaults to None.

        Raises:
            DataSetError: When `credentials` parameter is empty or "con" not in `credentials`.
        """
        if not (credentials and "con" in credentials and credentials["con"]):
            raise DataSetError(
                "`con` argument cannot be empty. Please provide a SQLAlchemy"
                "connection string."
            )

        default_load_args = {}  # type: Dict[str, Any]

        self._load_args = (
            {**default_load_args, **load_args}
            if load_args is not None
            else default_load_args
        )
        self._load_args["con"] = credentials["con"]

    def _load(self) -> sqlalchemy.engine.Engine:
        try:
            engine = create_engine(self._load_args["con"])
            conn = engine.connect()
            return conn
        # TODO: (BL) Need to find out what the sqlalchemy exceptions are
        except (sqlalchemy.exc.ArgumentError, NoSuchModuleError) as exc:
            raise DataSetError(
                "Provided connection string is invalid. Please check credentials."
            ) from exc

    def _save(self, data: Any) -> None:
        raise DataSetError("`save` is not supported on a SQLConnectionDataSet.")

    def _describe(self) -> Dict[str, Any]:
        load_args = self._load_args.copy()
        con = load_args.pop("con")
        return dict(con=con, load_args=load_args)
