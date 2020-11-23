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

"""``GBQTableGCSAVRODataSet`` unload/load data from/to a GBQ table as/using an AVRO file
stored to a GCS bucket.
About AVRO format: https://avro.apache.org/
About GBQ data export: https://cloud.google.com/bigquery/docs/exporting-data
About GBQ data import: https://cloud.google.com/bigquery/docs/loading-data-cloud-storage-avro
"""

from copy import deepcopy
from typing import Any, Dict, Optional, Union

from google.cloud import bigquery  # type: ignore
from google.cloud.exceptions import NotFound  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore

from kedro.io.core import (  # type: ignore
    AbstractDataSet,
    DataSetError,
    validate_on_forbidden_chars,
)


class GBQTableGCSAVRODataSet(AbstractDataSet):
    """``GBQTableGCSAVRODataSet`` unload/load data from/to a GBQ table as/using an AVRO file
    stored to a GCS bucket.

    Example:
    ::

        >>> from kedro.extras.datasets.avro import GBQTableUnloadAVRODataSet
        >>>
        >>> data_unload = GBQTableUnloadAVRODataSet(project='my-project',
        >>>                                         dataset='dataset',
        >>>                                         table='table_name',
        >>>                                         bucket='bucket_name')
        >>> data_unload.save()
        >>>
        >>> data_load = GBQTableUnloadAVRODataSet(project='my-project',
        >>>                                       dataset='dataset',
        >>>                                       table='table_name',
        >>>                                       bucket='bucket_name',
        >>>                                       path_object='prefix/testdata.avro')
        >>> data_load.load()
    """

    DEFAULT_LOAD_ARGS = {
        "source_format": "AVRO",
        "use_avro_logical_types": True,
        "write_desposition": "WRITE_APPEND",
    }  # type: Dict[str, Any]

    DEFAULT_SAVE_ARGS = {
        "destination_format": "AVRO",
        "use_avro_logical_types": True,
    }  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        project: str,
        dataset: str,
        table_name: str,
        bucket: str,
        location: str = "US",
        path_object: Optional[str] = None,
        credentials: Union[Dict[str, Any], Credentials] = None,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``GBQTableGCSAVRODataSet``.

        Args:
            project: Google Account project ID.
                Optional when available from the environment.
                https://cloud.google.com/resource-manager/docs/creating-managing-projects
            dataset: Google BigQuery dataset.
            table_name: Google BigQuery table name.
            bucket: Google Cloud Storage bucket name.
            location: Google BigQuery Dataset location.
            path_object: Path to an object in the Google Cloud Storage bucket.
            credentials: Credentials for accessing Google APIs.
                Either ``google.auth.credentials.Credentials`` object or dictionary with
                parameters required to instantiate ``google.oauth2.credentials.Credentials``.
                Here you can find all the arguments:
                https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.credentials.html
            load_args: Options to import data to BigQuery table from Google Cloud Storage.
                Here you can find all available arguments:
                https://cloud.google.com/bigquery/docs/loading-data-cloud-storage-avro
                For options, please find details here:
                https://googleapis.dev/python/bigquery/latest/generated/google.cloud.bigquery.job.LoadJobConfig.html
                Defaults:
                `use_avro_logical_types` is set to True

                `write_desposition` is set to "WRITE_APPEND"
            save_args: Options to export data from BigQuery table to Google Cloud Storage.
                Here you can find all available arguments:
                https://cloud.google.com/bigquery/docs/exporting-data
                For options, please find details here:
                https://googleapis.dev/python/bigquery/latest/generated/google.cloud.bigquery.job.ExtractJobConfig.html
                Defaults:
                `use_avro_logical_types` is set to True
        """
        validate_on_forbidden_chars(dataset=dataset, table_name=table_name)

        if isinstance(credentials, dict):
            credentials = Credentials(**credentials)

        self._location = location

        self._client = bigquery.Client(
            project=project, credentials=credentials, location=location,
        )

        self._table_id = f"{project}.{dataset}.{table_name}"
        self._table_ref = self._client.dataset(dataset).table(table_name)

        path_object = path_object or f"{dataset}/{table_name}.avro"
        self._uri = f"""gs://{bucket}/{path_object}"""

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args:
            self._load_args.update(load_args)
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args:
            self._save_args.update(save_args)

    def _describe(self) -> Dict[str, Any]:
        return dict(
            table_id=self._table_id,
            bucket_uri=self._uri,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def _save(self) -> None:  # type: ignore # pylint: disable=arguments-differ
        job_config = bigquery.job.ExtractJobConfig(**self._save_args)

        self._client.extract_table(
            self._table_ref, self._uri, location=self._location, job_config=job_config,
        ).result()

    def save(self) -> None:  # type: ignore # pylint: disable=arguments-differ
        """Saves data by delegation to the provided save method.

        Raises:
            DataSetError: when underlying save method raises error.
        """
        try:
            self._logger.debug("Saving %s", str(self))
            self._save()
        except DataSetError:
            raise
        except Exception as exc:
            message = "Failed while saving data to data set {}.\n{}".format(
                str(self), str(exc)
            )
            raise DataSetError(message) from exc

    def _load(self) -> None:
        job_config = bigquery.job.LoadJobConfig(**self._load_args)

        self._client.load_table_from_uri(
            self._uri, self._table_id, job_config=job_config
        ).result()

    def _exists(self) -> bool:
        try:
            self._client.get_table(self._table_ref)
            return True
        except NotFound:
            return False
