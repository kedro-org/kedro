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
from pathlib import PurePosixPath

import geopandas as gpd
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from pandas.util.testing import assert_frame_equal
from s3fs import S3FileSystem
from shapely.geometry import Point

from kedro.extras.datasets.geopandas import GeoJSONDataSet
from kedro.io import DataSetError
from kedro.io.core import Version, generate_timestamp


@pytest.fixture(params=[None])
def load_version(request):
    return request.param


@pytest.fixture(params=[None])
def save_version(request):
    return request.param or generate_timestamp()


@pytest.fixture
def filepath(tmp_path):
    return str(tmp_path / "test.geojson")


@pytest.fixture(params=[None])
def load_args(request):
    return request.param


@pytest.fixture(params=[{"driver": "GeoJSON"}])
def save_args(request):
    return request.param


@pytest.fixture
def dummy_dataframe():
    return gpd.GeoDataFrame(
        {"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]},
        geometry=[Point(1, 1), Point(2, 2)],
    )


@pytest.fixture
def geojson_data_set(filepath, load_args, save_args):
    return GeoJSONDataSet(filepath=filepath, load_args=load_args, save_args=save_args)


@pytest.fixture
def versioned_geojson_data_set(filepath, load_version, save_version):
    return GeoJSONDataSet(
        filepath=filepath, version=Version(load_version, save_version)
    )


class TestGeoJSONDataSet:
    def test_save_and_load(self, geojson_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one."""
        geojson_data_set.save(dummy_dataframe)
        reloaded_df = geojson_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    @pytest.mark.parametrize("geojson_data_set", [{"index": False}], indirect=True)
    def test_load_missing_file(self, geojson_data_set):
        """Check the error while trying to load from missing source."""
        pattern = r"Failed while loading data from data set GeoJSONDataSet"
        with pytest.raises(DataSetError, match=pattern):
            geojson_data_set.load()

    def test_exists(self, geojson_data_set, dummy_dataframe):
        """Test `exists` method invocation for both cases."""
        assert not geojson_data_set.exists()
        geojson_data_set.save(dummy_dataframe)
        assert geojson_data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"crs": "init:4326"}, {"crs": "init:2154", "driver": "GeoJSON"}]
    )
    def test_load_extra_params(self, geojson_data_set, load_args):
        """Test overriding default save args"""
        for k, v in load_args.items():
            assert geojson_data_set._load_args[k] == v

    @pytest.mark.parametrize(
        "save_args", [{"driver": "ESRI Shapefile"}, {"driver": "GPKG", "layer": "test"}]
    )
    def test_save_extra_params(self, geojson_data_set, save_args):
        """Test overriding default save args"""
        for k, v in save_args.items():
            assert geojson_data_set._save_args[k] == v

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.geojson", S3FileSystem),
            ("/tmp/test.geojson", LocalFileSystem),
            ("gcs://bucket/file.geojson", GCSFileSystem),
            ("file:///tmp/file.geojson", LocalFileSystem),
            ("https://example.com/file.geojson", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        geojson_data_set = GeoJSONDataSet(filepath=filepath)
        assert isinstance(geojson_data_set._fs, instance_type)

        if geojson_data_set._protocol == "https":
            path = filepath.split("://")[-1]
        else:
            path = geojson_data_set._fs._strip_protocol(filepath)

        assert str(geojson_data_set._filepath) == path
        assert isinstance(geojson_data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.geojson"
        geojson_data_set = GeoJSONDataSet(filepath=filepath)
        geojson_data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestGeoJSONDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.geojson"
        ds = GeoJSONDataSet(filepath=filepath)
        ds_versioned = GeoJSONDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
        assert "GeoJSONDataSet" in str(ds_versioned)
        assert "GeoJSONDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)

    def test_save_and_load(self, versioned_geojson_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_geojson_data_set.save(dummy_dataframe)
        reloaded_df = versioned_geojson_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_no_versions(self, versioned_geojson_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for GeoJSONDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_geojson_data_set.load()

    def test_exists(self, versioned_geojson_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_geojson_data_set.exists()
        versioned_geojson_data_set.save(dummy_dataframe)
        assert versioned_geojson_data_set.exists()

    def test_prevent_override(self, versioned_geojson_data_set, dummy_dataframe):
        """Check the error when attempt to override the same data set
        version."""
        versioned_geojson_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for GeoJSONDataSet\(.+\) must not "
            r"exist if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_geojson_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_geojson_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for GeoJSONDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_geojson_data_set.save(dummy_dataframe)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            GeoJSONDataSet(
                filepath="https://example/file.geojson", version=Version(None, None)
            )
