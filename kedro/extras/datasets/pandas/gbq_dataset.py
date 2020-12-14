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

"""``GBQTableDataSet`` loads and saves data from/to Google BigQuery. It uses pandas-gbq
to read and write from/to BigQuery table.
"""

import copy
from typing import Any, Dict, Union

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.oauth2.credentials import Credentials

from kedro.io.core import AbstractDataSet, DataSetError, validate_on_forbidden_chars


class GBQTableDataSet(AbstractDataSet):
    """``GBQTableDataSet`` loads and saves data from/to Google BigQuery.
    It uses pandas-gbq to read and write from/to BigQuery table.

    Example:
    ::

        >>> from kedro.extras.datasets.pandas import GBQTableDataSet
        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>>
        >>> data_set = GBQTableDataSet('dataset',
        >>>                            'table_name',
        >>>                            project='my-project')
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.equals(reloaded)

    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {"progress_bar": False}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        dataset: str,
        table_name: str,
        project: str = None,
        credentials: Union[Dict[str, Any], Credentials] = None,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``GBQTableDataSet``.

        Args:
            dataset: Google BigQuery dataset.
            table_name: Google BigQuery table name.
            project: Google BigQuery Account project ID.
                Optional when available from the environment.
                https://cloud.google.com/resource-manager/docs/creating-managing-projects
            credentials: Credentials for accessing Google APIs.
                Either ``google.auth.credentials.Credentials`` object or dictionary with
                parameters required to instantiate ``google.oauth2.credentials.Credentials``.
                Here you can find all the arguments:
                https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.credentials.html
            load_args: Pandas options for loading BigQuery table into DataFrame.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_gbq.html
                All defaults are preserved.
            save_args: Pandas options for saving DataFrame to BigQuery table.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_gbq.html
                All defaults are preserved, but "progress_bar", which is set to False.

        Raises:
            DataSetError: When ``load_args['location']`` and ``save_args['location']``
                are different.
        """
        # Handle default load and save arguments
        self._load_args = copy.deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = copy.deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

        self._validate_location()
        validate_on_forbidden_chars(dataset=dataset, table_name=table_name)

        if isinstance(credentials, dict):
            credentials = Credentials(**credentials)

        self._dataset = dataset
        self._table_name = table_name
        self._project_id = project
        self._credentials = credentials
        self._client = bigquery.Client(
            project=self._project_id,
            credentials=self._credentials,
            location=self._save_args.get("location"),
        )

    def _describe(self) -> Dict[str, Any]:
        return dict(
            dataset=self._dataset,
            table_name=self._table_name,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def _load(self) -> pd.DataFrame:
        sql = f"select * from {self._dataset}.{self._table_name}"  # nosec
        self._load_args.setdefault("query", sql)
        return pd.read_gbq(
            project_id=self._project_id,
            credentials=self._credentials,
            **self._load_args,
        )

    def _save(self, data: pd.DataFrame) -> None:
        data.to_gbq(
            f"{self._dataset}.{self._table_name}",
            project_id=self._project_id,
            credentials=self._credentials,
            **self._save_args,
        )

    def _exists(self) -> bool:
        table_ref = self._client.dataset(self._dataset).table(self._table_name)
        try:
            self._client.get_table(table_ref)
            return True
        except NotFound:
            return False

    def _validate_location(self):
        save_location = self._save_args.get("location")
        load_location = self._load_args.get("location")

        if save_location != load_location:
            raise DataSetError(
                "`load_args['location']` is different from `save_args['location']`. "
                "The `location` defines where BigQuery data is stored, therefore has "
                "to be the same for save and load args. "
                "Details: https://cloud.google.com/bigquery/docs/locations"
            )
