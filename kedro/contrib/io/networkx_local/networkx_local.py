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


"""``NetworkXLocalDataSet`` loads and saves graphs to a local json file in node/link format using
``NetworkX``.
See https://networkx.github.io/documentation/stable/tutorial.html for details.
"""

import json
from os.path import isfile
from pathlib import Path
from typing import Any, Dict, Union

import networkx

from kedro.contrib.io import DefaultArgumentsMixIn
from kedro.io import AbstractDataSet


class NetworkXLocalDataSet(DefaultArgumentsMixIn, AbstractDataSet):
    """
    ``NetworkXLocalDataSet`` loads and saves graphs to a local json file in node/link format using
    ``NetworkX``.
    See https://networkx.github.io/documentation/stable/tutorial.html for details.
    Example:
    ::
        >>> from kedro.contrib.io.networkx import NetworkXLocalDataSet
        >>> graph = NetworkXLocalDataSet(filepath="graph.json")
        >>> bb = networkx.betweenness_centrality(graph)
        >>> nx.set_node_attributes(graph, bb, 'betweenness')
        >>> graph.save()
        >>> reloaded = graph.load()
        >>> assert graph == reloaded
    """

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def __init__(
        self,
        filepath: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``NetworkXLocalDataSet``.

        Args:
            filepath: The path to the NetworkX graph JSON file.

            load_args: Arguments passed on to ```networkx.node_link_graph``.
                See https://networkx.github.io/documentation/stable/reference/readwrite/generated/networkx.readwrite.json_graph.node_link_graph.html for details.

            save_args: Arguments passed on to ```networkx.node_link_data``.
                See https://networkx.github.io/documentation/stable/reference/readwrite/generated/networkx.readwrite.json_graph.node_link_data.html for details.

        """
        super().__init__(
            filepath=Path(filepath), load_args=load_args, save_args=save_args
        )

    def _load(self) -> Union[networkx.Graph, Dict[str, networkx.Graph]]:
        G = None
        with open(self._filepath, "r") as f:
            json_payload = json.loads(f.readline())
            G = networkx.node_link_graph(json_payload, **self._load_args)

        return G

    def _save(self, data: networkx.Graph) -> None:
        json_graph = networkx.node_link_data(data)
        target_path = (
            self._save_args["output_filepath"]
            if "output_filepath" in self._save_args
            else f"{self._filepath}"
        )
        with open(target_path, "w") as f:
            json_payload = json.dumps(json_graph)
            f.write(json_payload)

    def _exists(self) -> bool:
        return isfile(self._filepath)
