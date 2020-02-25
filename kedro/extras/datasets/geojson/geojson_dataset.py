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

"""GeoJSONDataSet loads and saves data to a local geojson file. The
underlying functionality is supported by geopandas, so it supports all
allowed geopandas (pandas) options for loading and saving geosjon files.
"""
import copy
from pathlib import PurePosixPath
from typing import Any, Dict, Union

import fsspec
import geopandas as gpd

from kedro.io.core import (
    AbstractVersionedDataSet,
    DataSetError,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)


class GeoJSONDataSet(AbstractVersionedDataSet):
    """``GeoJSONDataSet`` loads and saves data to a geojson file using an underlying filesystem
    (eg: local, S3, GCS).
    The underlying functionality is supported by geopandas, so it supports all
    allowed geopandas (pandas) options for loading and saving geosjon files.

    Example:
    ::

        >>> import geopandas as gpd
        >>> from shapely.geometry import Point
        >>> from kedro.io.contrib import GeoJSONDataSet
        >>> data = gpd.GeoDataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]}, geometry=[Point(1,1), Point(2,4)])
        >>> # data_set = GeoJSONDataSet(filepath="gcs://bucket/test.geojson",
        >>>                                save_args=None)
        >>> data_set = GeoJSONDataSet(filepath="test.geojson",
        >>>                                save_args=None)
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.equals(reloaded)

    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {"driver": "GeoJSON"}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``GeoJSONDataSet`` pointing to a fsspec
        filepath.

        Args:

            filepath: path to a geojson file. Should be a ``fsspec```
                protocol path
            load_args: GeoPandas options for loading GeoJSON files.
                Here you can find all available arguments:
            save_args: GeoPandas options for saving geojson files.
                Here you can find all available arguments:
                The default_save_arg driver is 'GeoJSON', all others preserved.
            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
            credentials: credentials required to access the underlying filesystem.
                Eg. for ``GCFileSystem`` it would look like `{'token': None}`.
            fs_args: Extra args to pass into the underlying filesystem
                Eg. for ``GCFileSystem`` it would look like `{'project': 'my-project' , ...}`.


        """
        _fs_args = copy.deepcopy(fs_args) or {}
        _credentials = copy.deepcopy(credentials) or {}
        protocol, path = get_protocol_and_path(filepath, version)
        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **_credentials, **_fs_args)

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            exists_function=self._fs.exists,
            glob_function=self._fs.glob,
        )

        self._load_args = copy.deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)

        self._save_args = copy.deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

    def _load(self) -> Union[gpd.GeoDataFrame, Dict[str, gpd.GeoDataFrame]]:
        load_path = get_filepath_str(self._get_load_path(), self._protocol)
        with self._fs.open(load_path, mode="rb") as fs_file:
            return gpd.read_file(fs_file, **self._load_args)

    def _save(self, data: gpd.GeoDataFrame) -> None:
        save_path = get_filepath_str(self._get_save_path(), self._protocol)
        with self._fs.open(save_path, mode="wb") as fs_file:
            data.to_file(fs_file, **self._save_args)
        self.invalidate_cache()

    def _exists(self) -> bool:
        try:
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
        except DataSetError:
            return False
        return self._fs.exists(load_path)

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            protocol=self._protocol,
            load_args=self._load_args,
            save_args=self._save_args,
            version=self._version,
        )

    def _release(self) -> None:
        self.invalidate_cache()

    def invalidate_cache(self) -> None:
        """Invalidate underlying filesystem cache."""
        filepath = get_filepath_str(self._filepath, self._protocol)
        self._fs.invalidate_cache(filepath)
