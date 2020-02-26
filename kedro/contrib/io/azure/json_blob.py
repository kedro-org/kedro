# Copyright 2020 QuantumBlack Visual Analytics Limited
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

""" ``AbstractDataSet`` implementation to access JSON(L) files directly from
Microsoft's Azure blob storage.
"""
import io
from typing import Any, Dict, Optional

import pandas as pd
from azure.storage.blob import BlockBlobService

from kedro.io import AbstractDataSet


class JSONBlobDataSet(AbstractDataSet):
    # pylint: disable=too-many-instance-attributes
    """``JSONBlobDataSet`` loads and saves json(line-delimited) files in Microsoft's Azure
    blob storage. It uses Azure storage SDK to read and write in Azure and
    pandas to handle the json(l) file locally.

    Example:
    ::

        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>>
        >>> data_set = JSONBlobDataSet(filepath="test.jsonl", credentials={"sas_token":"1234"},
        >>>                            load_args={"lines":True}, container_name="test",
        >>>                            save_args={"orient":"records", "lines":True})
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.equals(reloaded)
    """

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            container_name=self._container_name,
            blob_to_bytes_args=self._blob_to_bytes_args,
            blob_from_bytes_args=self._blob_from_bytes_args,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        container_name: str,
        credentials: Dict[str, Any],
        encoding: str = "utf-8",
        blob_from_bytes_args: Optional[Dict[str, Any]] = None,
        blob_to_bytes_args: Optional[Dict[str, Any]] = None,
        load_args: Optional[Dict[str, Any]] = None,
        save_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Creates a new instance of ``JSONBlobDataSet`` pointing to a
        concrete json(l) file on Azure blob storage.

        Args:
            filepath: path to a azure blob of a json(l) file.
            container_name: Azure container name.
            credentials: Credentials (``account_name`` and
                ``account_key`` or ``sas_token``) to access the Azure blob storage
            encoding: Default utf-8. Defines encoding of json files downloaded as binary streams.
            blob_to_bytes_args: Any additional arguments to pass to Azure's
                ``get_blob_to_bytes`` method:
                https://docs.microsoft.com/en-us/python/api/azure.storage.blob.baseblobservice.baseblobservice?view=azure-python#get-blob-to-bytes
            blob_from_bytes_args: Any additional arguments to pass to Azure's
                ``create_blob_from_bytes`` method:
                https://docs.microsoft.com/en-us/python/api/azure.storage.blob.blockblobservice.blockblobservice?view=azure-python#create-blob-from-bytes
            load_args: Pandas options for loading json(l) files.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_json.html
                All defaults are preserved.
            save_args: Pandas options for saving json(l) files.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.to_json.html
                All defaults are preserved, but "index", which is set to False.

        """
        self._save_args = {**save_args} if save_args else {}
        self._load_args = load_args if load_args else {}
        self._filepath = filepath
        self._encoding = encoding
        self._container_name = container_name
        self._credentials = credentials if credentials else {}
        self._blob_to_bytes_args = blob_to_bytes_args if blob_to_bytes_args else {}
        self._blob_from_bytes_args = (
            blob_from_bytes_args if blob_from_bytes_args else {}
        )

    def _load(self) -> pd.DataFrame:
        blob_service = BlockBlobService(**self._credentials)
        blob = blob_service.get_blob_to_bytes(
            container_name=self._container_name,
            blob_name=self._filepath,
            **self._blob_to_bytes_args
        )
        bytes_stream = io.BytesIO(blob.content)
        return pd.read_json(bytes_stream, encoding=self._encoding, **self._load_args)

    def _save(self, data: pd.DataFrame) -> None:
        blob_service = BlockBlobService(**self._credentials)
        blob_service.create_blob_from_bytes(
            container_name=self._container_name,
            blob_name=self._filepath,
            blob=data.to_json(**self._save_args).encode(self._encoding),
            **self._blob_from_bytes_args
        )
