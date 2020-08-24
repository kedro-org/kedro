# Copyright 2020 QuantumBlack Visual Analytics Limited
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

"""SparkJDBCDataSet to load and save a PySpark DataFrame via JDBC."""

from copy import deepcopy
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession  # pylint: disable=import-error

from kedro.io.core import AbstractDataSet, DataSetError

__all__ = ["SparkJDBCDataSet"]


class SparkJDBCDataSet(AbstractDataSet):
    """``SparkJDBCDataSet`` loads data from a database table accessible
    via JDBC URL url and connection properties and saves the content of
    a PySpark DataFrame to an external database table via JDBC.  It uses
    ``pyspark.sql.DataFrameReader`` and ``pyspark.sql.DataFrameWriter``
    internally, so it supports all allowed PySpark options on ``jdbc``.


    Example:
    ::

        >>> import pandas as pd
        >>>
        >>> from pyspark.sql import SparkSession
        >>>
        >>> spark = SparkSession.builder.getOrCreate()
        >>> data = spark.createDataFrame(pd.DataFrame({'col1': [1, 2],
        >>>                                            'col2': [4, 5],
        >>>                                            'col3': [5, 6]}))
        >>> url = 'jdbc:postgresql://localhost/test'
        >>> table = 'table_a'
        >>> connection_properties = {'driver': 'org.postgresql.Driver'}
        >>> data_set = SparkJDBCDataSet(
        >>>     url=url, table=table, credentials={'user': 'scott',
        >>>                                        'password': 'tiger'},
        >>>     load_args={'properties': connection_properties},
        >>>     save_args={'properties': connection_properties})
        >>>
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.toPandas().equals(reloaded.toPandas())

    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        url: str,
        table: str,
        credentials: Dict[str, Any] = None,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new ``SparkJDBCDataSet``.

        Args:
            url: A JDBC URL of the form ``jdbc:subprotocol:subname``.
            table: The name of the table to load or save data to.
            credentials: A dictionary of JDBC database connection arguments.
                Normally at least properties ``user`` and ``password`` with
                their corresponding values.  It updates ``properties``
                parameter in ``load_args`` and ``save_args`` in case it is
                provided.
            load_args: Provided to underlying PySpark ``jdbc`` function along
                with the JDBC URL and the name of the table. To find all
                supported arguments, see here:
                https://spark.apache.org/docs/latest/api/python/pyspark.sql.html?highlight=jdbc#pyspark.sql.DataFrameReader.jdbc
            save_args: Provided to underlying PySpark ``jdbc`` function along
                with the JDBC URL and the name of the table. To find all
                supported arguments, see here:
                https://spark.apache.org/docs/latest/api/python/pyspark.sql.html?highlight=jdbc#pyspark.sql.DataFrameWriter.jdbc

        Raises:
            DataSetError: When either ``url`` or ``table`` is empty or
                when a property is provided with a None value.
        """

        if not url:
            raise DataSetError(
                "`url` argument cannot be empty. Please "
                "provide a JDBC URL of the form "
                "``jdbc:subprotocol:subname``."
            )

        if not table:
            raise DataSetError(
                "`table` argument cannot be empty. Please "
                "provide the name of the table to load or save "
                "data to."
            )

        self._url = url
        self._table = table

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

        # Update properties in load_args and save_args with credentials.
        if credentials is not None:

            # Check credentials for bad inputs.
            for cred_key, cred_value in credentials.items():
                if cred_value is None:
                    raise DataSetError(
                        "Credential property `{}` cannot be None. "
                        "Please provide a value.".format(cred_key)
                    )

            load_properties = self._load_args.get("properties", {})
            save_properties = self._save_args.get("properties", {})
            self._load_args["properties"] = {**load_properties, **credentials}
            self._save_args["properties"] = {**save_properties, **credentials}

    def _describe(self) -> Dict[str, Any]:
        load_args = self._load_args
        save_args = self._save_args

        # Remove user and password values from load and save properties.
        if "properties" in load_args:
            load_properties = load_args["properties"].copy()
            load_properties.pop("user", None)
            load_properties.pop("password", None)
            load_args = {**load_args, "properties": load_properties}
        if "properties" in save_args:
            save_properties = save_args["properties"].copy()
            save_properties.pop("user", None)
            save_properties.pop("password", None)
            save_args = {**save_args, "properties": save_properties}

        return dict(
            url=self._url, table=self._table, load_args=load_args, save_args=save_args
        )

    @staticmethod
    def _get_spark():
        return SparkSession.builder.getOrCreate()

    def _load(self) -> DataFrame:
        return self._get_spark().read.jdbc(self._url, self._table, **self._load_args)

    def _save(self, data: DataFrame) -> None:
        return data.write.jdbc(self._url, self._table, **self._save_args)
