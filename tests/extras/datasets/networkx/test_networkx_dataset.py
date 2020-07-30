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

from pathlib import PurePosixPath

import networkx
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.networkx import NetworkXDataSet
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
def filepath_json(tmp_path):
    return (tmp_path / "some_dir" / "test.json").as_posix()


@pytest.fixture
def networkx_data_set(filepath_json, fs_args):
    return NetworkXDataSet(filepath=filepath_json, fs_args=fs_args)


@pytest.fixture
def versioned_networkx_data_set(filepath_json, load_version, save_version):
    return NetworkXDataSet(
        filepath=filepath_json, version=Version(load_version, save_version)
    )


@pytest.fixture
def networkx_data_set_args(filepath_json):
    return NetworkXDataSet(
        filepath=filepath_json, load_args={"attrs": ATTRS}, save_args={"attrs": ATTRS}
    )


@pytest.fixture()
def dummy_graph_data():
    return networkx.complete_graph(3)


class TestNetworkXDataSet:
    def test_save_and_load(self, networkx_data_set, dummy_graph_data):
        """Test saving and reloading the data set."""
        networkx_data_set.save(dummy_graph_data)
        reloaded = networkx_data_set.load()
        assert dummy_graph_data.nodes(data=True) == reloaded.nodes(data=True)
        assert networkx_data_set._fs_open_args_load == {"mode": "r"}
        assert networkx_data_set._fs_open_args_save == {"mode": "w"}

    def test_load_missing_file(self, networkx_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set NetworkXDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            assert networkx_data_set.load()

    def test_load_args_save_args(
        self, mocker, networkx_data_set_args, dummy_graph_data
    ):
        """Test saving and reloading with save and load arguments."""
        patched_save = mocker.patch(
            "networkx.node_link_data", wraps=networkx.node_link_data
        )
        networkx_data_set_args.save(dummy_graph_data)
        patched_save.assert_called_once_with(dummy_graph_data, attrs=ATTRS)

        patched_load = mocker.patch(
            "networkx.node_link_graph", wraps=networkx.node_link_graph
        )
        # load args need to be the same attrs as the ones used for saving
        # in order to successfully retrieve data
        reloaded = networkx_data_set_args.load()

        patched_load.assert_called_once_with(
            {
                "directed": False,
                "multigraph": False,
                "graph": {},
                "nodes": [{"fake_id": 0}, {"fake_id": 1}, {"fake_id": 2}],
                "fake_link": [
                    {"from": 0, "to": 1},
                    {"from": 0, "to": 2},
                    {"from": 1, "to": 2},
                ],
            },
            attrs=ATTRS,
        )
        assert dummy_graph_data.nodes(data=True) == reloaded.nodes(data=True)

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, networkx_data_set, fs_args):
        assert networkx_data_set._fs_open_args_load == fs_args["open_args_load"]
        assert networkx_data_set._fs_open_args_save == {
            "mode": "w"
        }  # default unchanged

    def test_exists(self, networkx_data_set, dummy_graph_data):
        """Test `exists` method invocation."""
        assert not networkx_data_set.exists()
        networkx_data_set.save(dummy_graph_data)
        assert networkx_data_set.exists()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.json", S3FileSystem),
            ("file:///tmp/test.json", LocalFileSystem),
            ("/tmp/test.json", LocalFileSystem),
            ("gcs://bucket/file.json", GCSFileSystem),
            ("https://example.com/file.json", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = NetworkXDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.json"
        data_set = NetworkXDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestNetworkXDataSetVersioned:
    def test_save_and_load(self, versioned_networkx_data_set, dummy_graph_data):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_networkx_data_set.save(dummy_graph_data)
        reloaded = versioned_networkx_data_set.load()
        assert dummy_graph_data.nodes(data=True) == reloaded.nodes(data=True)

    def test_no_versions(self, versioned_networkx_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for NetworkXDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_networkx_data_set.load()

    def test_exists(self, versioned_networkx_data_set, dummy_graph_data):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_networkx_data_set.exists()
        versioned_networkx_data_set.save(dummy_graph_data)
        assert versioned_networkx_data_set.exists()

    def test_prevent_override(self, versioned_networkx_data_set, dummy_graph_data):
        """Check the error when attempt to override the same data set
        version."""
        versioned_networkx_data_set.save(dummy_graph_data)
        pattern = (
            r"Save path \`.+\` for NetworkXDataSet\(.+\) must not "
            r"exist if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_networkx_data_set.save(dummy_graph_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_networkx_data_set, load_version, save_version, dummy_graph_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for NetworkXDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_networkx_data_set.save(dummy_graph_data)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.json"
        ds = NetworkXDataSet(filepath=filepath)
        ds_versioned = NetworkXDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
        assert "NetworkXDataSet" in str(ds_versioned)
        assert "NetworkXDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)
