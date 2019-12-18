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

"""GeoJSONLocalDataSet loads and saves data to a local geojson file. The
underlying functionality is supported by geopandas, so it supports all
allowed geopandas (pandas) options for loading and saving geosjon files.
"""
import copy
from pathlib import Path
from typing import Any, Dict, Union

import geopandas as gpd

from kedro.io.core import AbstractVersionedDataSet, Version, is_remote_path


class GeoJSONLocalDataSet(AbstractVersionedDataSet):
    """``GeoJSONLocalDataSet`` loads and saves data to a local geojson file. The
    underlying functionality is supported by geopandas, so it supports all
    allowed geopandas (pandas) options for loading and saving geosjon files.

    Example:
    ::

        >>> import geopandas as gpd
        >>> from shapely.geometry import Point
        >>>
        >>> data = gpd.GeoDataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]}, geometry=[Point(1,1), Point(2,4)])
        >>> data_set = GeoJSONLocalDataSet(filepath="test.geojson",
        >>>                                save_args=None)
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.equals(reloaded)

    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {"driver": "GeoJSON"}  # type: Dict[str, Any]

    def __init__(
        self,
        filepath: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
    ) -> None:
        """Creates a new instance of ``GeoJSONLocalDataSet`` pointing to a concrete
        filepath.

        Args:

            filepath: path to a geojson file.

            load_args: GeoPandas options for loading GeoJSON files.
                Here you can find all available arguments:

            save_args: GeoPandas options for saving geojson files.
                Here you can find all available arguments:
                The default_save_arg driver is 'GeoJSON', all others preserved.

            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``

        Raises:
            ValueError: If 'filepath' looks like a remote path.


        """
        super().__init__(Path(filepath), version)

        if is_remote_path(filepath):
            raise ValueError(
                "{} seems to be a remote file, which is not supported by {}".format(
                    filepath, self.__class__.__name__
                )
            )
            # Handle default load and save arguments
        self._load_args = copy.deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)

        self._save_args = copy.deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

    def _load(self) -> Union[gpd.GeoDataFrame, Dict[str, gpd.GeoDataFrame]]:
        load_path = Path(self._get_load_path())
        return gpd.read_file(load_path, **self._load_args)

    def _save(self, data: gpd.GeoDataFrame) -> None:
        save_path = Path(self._get_save_path())
        save_path.parent.mkdir(parents=True, exist_ok=True)
        data.to_file(save_path, **self._save_args)

    def _exists(self) -> bool:
        path = self._get_load_path()
        return Path(path).is_file()

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            load_args=self._load_args,
            save_args=self._save_args,
            version=self._version,
        )
