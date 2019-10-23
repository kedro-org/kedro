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


import networkx
import pytest

from kedro.contrib.io.networkx import NetworkXLocalDataSet
from kedro.io import DataSetError


@pytest.fixture
def filepath_json(tmp_path):
    return str(tmp_path / "test.json")


@pytest.fixture
def networkx_data_set(filepath_json):
    return NetworkXLocalDataSet(filepath=filepath_json)


@pytest.fixture
def networkx_data_set_args(filepath_json):
    attrs = dict(
        source="from", target="to", name="fake_id", key="fake_key", link="fake_link"
    )
    return NetworkXLocalDataSet(
        filepath=filepath_json, load_args={"attrs": attrs}, save_args={"attrs": attrs}
    )


@pytest.fixture(params=[[1, 2, 3]])
def network_graph_data():
    return networkx.complete_graph(3)


class TestNetworkXLocalDataSet:
    def test_save_and_load(self, networkx_data_set, network_graph_data):
        """Test saving and reloading the data set."""
        networkx_data_set.save(network_graph_data)
        reloaded = networkx_data_set.load()
        assert network_graph_data.nodes(data=True) == reloaded.nodes(data=True)

    def test_load_missing_file(self, networkx_data_set):
        """Check the error when trying to load missing file."""
        pattern = (
            r"Failed while loading data from data set " r"NetworkXLocalDataSet\(.*\)"
        )
        with pytest.raises(DataSetError, match=pattern):
            assert networkx_data_set.load()

    def test_load_args_save_args(
        self, mocker, networkx_data_set_args, network_graph_data
    ):
        """Test saving and reloading with save and load arguments."""
        patched_save = mocker.patch(
            "networkx.node_link_data", wraps=networkx.node_link_data
        )
        networkx_data_set_args.save(network_graph_data)
        attrs = dict(
            source="from", target="to", name="fake_id", key="fake_key", link="fake_link"
        )
        patched_save.assert_called_once_with(network_graph_data, attrs=attrs)

        patched_load = mocker.patch(
            "networkx.node_link_graph", wraps=networkx.node_link_graph
        )
        # load args need to be the same attrs as the ones used for saving
        # in order to successfully retrieve data
        load_attrs = dict(
            source="from", target="to", name="fake_id", key="fake_key", link="fake_link"
        )
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
            attrs=load_attrs,
        )
        assert network_graph_data.nodes(data=True) == reloaded.nodes(data=True)

    def test_exists(self, networkx_data_set, network_graph_data):
        """Test `exists` method invocation."""
        assert not networkx_data_set.exists()

        networkx_data_set.save(network_graph_data)
        assert networkx_data_set.exists()
