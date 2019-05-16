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
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

""" ``AbstractDataSet`` implementation to access CSV files directly from
Microsoft's Azure blob storage.
"""
import io
from typing import Any, Dict, Optional

import pandas as pd
from azure.storage.blob import BlockBlobService

from kedro.io import AbstractDataSet


class CSVBlobDataSet(AbstractDataSet):
    """``CSVBlobDataSet`` loads and saves csv files in Microsoft's Azure
    blob storage. It uses azure storage SDK to read and write in azure and
    pandas to handle the csv file locally.

    Example:
    ::

        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>>
        >>> data_set = CSVBlobDataSet(filepath="test.csv",
        >>>                            bucket_name="test_bucket",
        >>>                            load_args=None,
        >>>                            save_args={"index": False})
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.equals(reloaded)
    """

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            container_name=self._container_name,
            blob_to_text_args=self._blob_to_text_args,
            blob_from_text_args=self._blob_from_text_args,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        container_name: str,
        credentials: Dict[str, Any],
        blob_to_text_args: Optional[Dict[str, Any]] = None,
        blob_from_text_args: Optional[Dict[str, Any]] = None,
        load_args: Optional[Dict[str, Any]] = None,
        save_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Creates a new instance of ``CSVBlobDataSet`` pointing to a
        concrete csv file on Azure blob storage.

        Args:
            filepath: path to a azure blob of a csv file.
            container_name: Azure container name.
            credentials: Credentials (``account_name`` and
                ``account_key`` or ``sas_token``)to access the azure blob
            blob_to_text_args: Any additional arguments to pass to azure's
                ``get_blob_to_text`` method:
                https://docs.microsoft.com/en-us/python/api/azure.storage.blob.baseblobservice.baseblobservice?view=azure-python#get-blob-to-text
            blob_from_text_args: Any additional arguments to pass to azure's
                ``create_blob_from_text`` method:
                https://docs.microsoft.com/en-us/python/api/azure.storage.blob.blockblobservice.blockblobservice?view=azure-python#create-blob-from-text
            load_args: Pandas options for loading csv files.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_csv.html
                All defaults are preserved.
            save_args: Pandas options for saving csv files.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.to_csv.html
                All defaults are preserved, but "index", which is set to False.

        """
        default_save_args = {"index": False}
        self._save_args = (
            {**default_save_args, **save_args} if save_args else default_save_args
        )
        self._load_args = load_args if load_args else {}
        self._filepath = filepath
        self._container_name = container_name
        self._credentials = credentials if credentials else {}
        self._blob_to_text_args = blob_to_text_args if blob_to_text_args else {}
        self._blob_from_text_args = blob_from_text_args if blob_from_text_args else {}

    def _load(self) -> pd.DataFrame:
        blob_service = BlockBlobService(**self._credentials)
        blob = blob_service.get_blob_to_text(
            container_name=self._container_name,
            blob_name=self._filepath,
            **self._blob_to_text_args
        )
        csv_content = io.StringIO(blob.content)
        return pd.read_csv(csv_content, **self._load_args)

    def _save(self, data: pd.DataFrame) -> None:
        blob_service = BlockBlobService(**self._credentials)
        blob_service.create_blob_from_text(
            container_name=self._container_name,
            blob_name=self._filepath,
            text=data.to_csv(**self._save_args),
            **self._blob_from_text_args
        )
