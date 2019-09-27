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

import pandas as pd

from kedro.pipeline import Pipeline, node


def identity(item):
    return item


def sum_dfs(dataframe1: pd.DataFrame, dataframe2: pd.DataFrame):
    return dataframe1 + dataframe2.values


def create_pipelines(*tags: str):
    example_pipeline = Pipeline(
        [
            node(
                lambda x: x,
                "A",
                "B",
                name="node_1",
                tags=[
                    "apple",
                    "orange",
                    "banana",
                    "lemon",
                    "grape",
                    "coconut",
                    "fresh strawberries!",
                ],
            ),
            node(
                sum_dfs,
                ["B", "C"],
                "D",
                name="node_2",
                tags=["apple", "orange", "lemon"],
            ),
            node(
                identity,
                "D",
                "E",
                name="node_3",
                tags=["apple", "orange", "banana", "cherry"],
            ),
            node(identity, "D", "F", name="node_4", tags=["apple", "cherry"]),
        ]
    )

    if tags:
        pipeline = Pipeline([])
        for tag in tags:
            pipeline += example_pipeline.only_nodes_with_tags(tag)
        if not pipeline.nodes:
            raise ValueError(
                "Not found any nodes having any of the following "
                "tags attached: {}".format(", ".join(tags))
            )
    else:
        pipeline = example_pipeline

    return {"__default__": pipeline}
