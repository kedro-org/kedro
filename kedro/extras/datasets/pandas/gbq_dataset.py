"""``GBQTableDataSet`` loads and saves data from/to Google BigQuery. It uses pandas-gbq
to read and write from/to BigQuery table.
"""

import copy
from pathlib import PurePosixPath
from typing import Any, Dict, Union

import fsspec
import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.oauth2.credentials import Credentials

from kedro.io.core import (
    AbstractDataSet,
    DataSetError,
    get_filepath_str,
    get_protocol_and_path,
    validate_on_forbidden_chars,
)


class GBQTableDataSet(AbstractDataSet):
    """``GBQTableDataSet`` loads and saves data from/to Google BigQuery.
    It uses pandas-gbq to read and write from/to BigQuery table.

    Example adding a catalog entry with
    `YAML API <https://kedro.readthedocs.io/en/stable/05_data/\
        01_data_catalog.html#using-the-data-catalog-with-the-yaml-api>`_:

    .. code-block:: yaml

        >>> vehicles:
        >>>   type: pandas.GBQTableDataSet
        >>>   dataset: big_query_dataset
        >>>   table_name: big_query_table
        >>>   project: my-project
        >>>   credentials: gbq-creds
        >>>   load_args:
        >>>     reauth: True
        >>>   save_args:
        >>>     chunk_size: 100


    Example using Python API:
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


class GBQQueryDataSet(AbstractDataSet):
    """``GBQQueryDataSet`` loads data from a provided SQL query from Google
    BigQuery. It uses ``pandas.read_gbq`` which itself uses ``pandas-gbq``
    internally to read from BigQuery table. Therefore it supports all allowed
    pandas options on ``read_gbq``.

    Example adding a catalog entry with
    `YAML API <https://kedro.readthedocs.io/en/stable/05_data/\
        01_data_catalog.html#using-the-data-catalog-with-the-yaml-api>`_:

    .. code-block:: yaml

        >>> vehicles:
        >>>   type: pandas.GBQQueryDataSet
        >>>   sql: "select shuttle, shuttle_id from spaceflights.shuttles;"
        >>>   project: my-project
        >>>   credentials: gbq-creds
        >>>   load_args:
        >>>     reauth: True


    Example using Python API:
    ::

        >>> from kedro.extras.datasets.pandas import GBQQueryDataSet
        >>>
        >>> sql = "SELECT * FROM dataset_1.table_a"
        >>>
        >>> data_set = GBQQueryDataSet(sql, project='my-project')
        >>>
        >>> sql_data = data_set.load()
        >>>
    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        sql: str = None,
        project: str = None,
        credentials: Union[Dict[str, Any], Credentials] = None,
        load_args: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
        filepath: str = None,
    ) -> None:
        """Creates a new instance of ``GBQQueryDataSet``.

        Args:
            sql: The sql query statement.
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
            fs_args: Extra arguments to pass into underlying filesystem class constructor
                (e.g. `{"project": "my-project"}` for ``GCSFileSystem``) used for reading the
                SQL query from filepath.
            filepath: A path to a file with a sql query statement.

        Raises:
            DataSetError: When ``sql`` and ``filepath`` parameters are either both empty
                or both provided, as well as when the `save()` method is invoked.
        """
        if sql and filepath:
            raise DataSetError(
                "`sql` and `filepath` arguments cannot both be provided."
                "Please only provide one."
            )

        if not (sql or filepath):
            raise DataSetError(
                "`sql` and `filepath` arguments cannot both be empty."
                "Please provide a sql query or path to a sql query file."
            )

        # Handle default load arguments
        self._load_args = copy.deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)

        self._project_id = project

        if isinstance(credentials, dict):
            credentials = Credentials(**credentials)

        self._credentials = credentials
        self._client = bigquery.Client(
            project=self._project_id,
            credentials=self._credentials,
            location=self._load_args.get("location"),
        )

        # load sql query from arg or from file
        if sql:
            self._load_args["query"] = sql
            self._filepath = None
        else:
            # filesystem for loading sql file
            _fs_args = copy.deepcopy(fs_args) or {}
            _fs_credentials = _fs_args.pop("credentials", {})
            protocol, path = get_protocol_and_path(str(filepath))

            self._protocol = protocol
            self._fs = fsspec.filesystem(self._protocol, **_fs_credentials, **_fs_args)
            self._filepath = path

    def _describe(self) -> Dict[str, Any]:
        load_args = copy.deepcopy(self._load_args)
        desc = {}
        desc["sql"] = str(load_args.pop("query", None))
        desc["filepath"] = str(self._filepath)
        desc["load_args"] = str(load_args)

        return desc

    def _load(self) -> pd.DataFrame:
        load_args = copy.deepcopy(self._load_args)

        if self._filepath:
            load_path = get_filepath_str(PurePosixPath(self._filepath), self._protocol)
            with self._fs.open(load_path, mode="r") as fs_file:
                load_args["query"] = fs_file.read()

        return pd.read_gbq(
            project_id=self._project_id,
            credentials=self._credentials,
            **load_args,
        )

    def _save(self, data: pd.DataFrame) -> None:
        raise DataSetError("`save` is not supported on GBQQueryDataSet")
