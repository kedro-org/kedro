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

from pathlib import Path, PurePosixPath

import networkx
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.networkx import GPickleDataSet
from kedro.io import DataSetError, Version
from kedro.io.core import PROTOCOL_DELIMITER

ATTRS = {
    "source": "from",
    "target": "to",
    "name": "fake_id",
    "key": "fake_key",
    "link": "fake_link",
}


@pytest.fixture
def filepath_gpickle(tmp_path):
    return (tmp_path / "some_dir" / "test.gpickle").as_posix()


@pytest.fixture
def gpickle_data_set(filepath_gpickle):
    return GPickleDataSet(filepath=filepath_gpickle, save_args={"protocol": 4})


@pytest.fixture
def versioned_gpickle_data_set(filepath_gpickle, load_version, save_version):
    return GPickleDataSet(
        filepath=filepath_gpickle, version=Version(load_version, save_version)
    )


@pytest.fixture()
def dummy_graph_data():
    return networkx.complete_graph(3)


class TestGPickleDataSet:
    def test_save_and_load(self, gpickle_data_set, dummy_graph_data):
        """Test saving and reloading the data set."""
        gpickle_data_set.save(dummy_graph_data)
        reloaded = gpickle_data_set.load()
        assert dummy_graph_data.nodes(data=True) == reloaded.nodes(data=True)

    def test_load_missing_file(self, gpickle_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set GPickleDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            assert gpickle_data_set.load()

    def test_exists(self, gpickle_data_set, dummy_graph_data):
        """Test `exists` method invocation."""
        assert not gpickle_data_set.exists()
        gpickle_data_set.save(dummy_graph_data)
        assert gpickle_data_set.exists()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.gpickle", S3FileSystem),
            ("file:///tmp/test.gpickle", LocalFileSystem),
            ("/tmp/test.gpickle", LocalFileSystem),
            ("gcs://bucket/file.gpickle", GCSFileSystem),
            ("https://example.com/file.gpickle", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = GPickleDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.gpickle"
        data_set = GPickleDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestGPickleDataSetVersioned:
    def test_save_and_load(self, versioned_gpickle_data_set, dummy_graph_data):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_gpickle_data_set.save(dummy_graph_data)
        reloaded = versioned_gpickle_data_set.load()
        assert dummy_graph_data.nodes(data=True) == reloaded.nodes(data=True)

    def test_no_versions(self, versioned_gpickle_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for GPickleDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_gpickle_data_set.load()

    def test_exists(self, versioned_gpickle_data_set, dummy_graph_data):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_gpickle_data_set.exists()
        versioned_gpickle_data_set.save(dummy_graph_data)
        assert versioned_gpickle_data_set.exists()

    def test_prevent_override(self, versioned_gpickle_data_set, dummy_graph_data):
        """Check the error when attempt to override the same data set
        version."""
        versioned_gpickle_data_set.save(dummy_graph_data)
        pattern = (
            r"Save path \`.+\` for GPickleDataSet\(.+\) must not "
            r"exist if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_gpickle_data_set.save(dummy_graph_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_gpickle_data_set, load_version, save_version, dummy_graph_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for GPickleDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_gpickle_data_set.save(dummy_graph_data)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.gpickle"
        ds = GPickleDataSet(filepath=filepath)
        ds_versioned = GPickleDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "GPickleDataSet" in str(ds_versioned)
        assert "GPickleDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)

    def test_versioning_existing_dataset(
        self, gpickle_data_set, versioned_gpickle_data_set, dummy_graph_data
    ):
        """Check the error when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset."""
        gpickle_data_set.save(dummy_graph_data)
        assert gpickle_data_set.exists()
        assert gpickle_data_set._filepath == versioned_gpickle_data_set._filepath
        pattern = (
            f"(?=.*file with the same name already exists in the directory)"
            f"(?=.*{versioned_gpickle_data_set._filepath.parent.as_posix()})"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_gpickle_data_set.save(dummy_graph_data)

        # Remove non-versioned dataset and try again
        Path(gpickle_data_set._filepath.as_posix()).unlink()
        versioned_gpickle_data_set.save(dummy_graph_data)
        assert versioned_gpickle_data_set.exists()
