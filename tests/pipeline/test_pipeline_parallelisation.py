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
import pandas as pd
import pytest
from pandas.testing import assert_series_equal

from kedro.extras.datasets.pandas import CSVDataSet
from kedro.io import DataCatalog, MemoryDataSet
from kedro.pipeline import Pipeline, node
from kedro.pipeline.parallelised_pipeline import parallelised_pipeline
from kedro.runner import ParallelRunner


def node_multiply(inp: pd.DataFrame, multiply_by=2, **kwds):
    del kwds  # unused but linter complains
    inp["values"] = inp["values"] * multiply_by
    return inp


def node_divide(inp: pd.DataFrame, divide_by=3, **kwds):
    del kwds  # unused but linter complains
    inp["values"] = inp["values"] / divide_by
    return inp


def node_add(inp1: pd.DataFrame, inp2: pd.DataFrame, **kwds):
    del kwds  # unused but linter complains
    inp1["values"] += inp2["values"]
    return inp1


DATASET = pd.DataFrame(
    dict(
        index=[1, 2, 3, 4, 5, 6, 7, 8, 9],
        values=[2, 4, 6, 8, 10, 12, 14, 16, 18],
        col1=["A", "A", "A", "A", "B", "B", "B", "B", "B"],
        col2=["c", "c", "d", "d", "d", "d", "e", "e", "e"],
    )
)


@pytest.fixture
def runner():
    return ParallelRunner()


@pytest.fixture
def pipe():
    return Pipeline(
        [
            node(
                func=node_multiply,
                inputs="base_data",
                outputs="multiplied_data",
                name="multiply_input_by",
            ),
            node(
                func=node_divide,
                inputs="base_data",
                outputs="divided_data",
                name="divide_input_by",
            ),
            node(
                func=node_add,
                inputs=["multiplied_data", "divided_data"],
                outputs="summed_data",
                name="sum_inputs_up",
            ),
        ]
    )


@pytest.fixture
def catalog(tmp_path):
    # need to persist output to inspect
    cat = DataCatalog(
        {
            "base_data": MemoryDataSet(data=DATASET),
            "multiplied_data": CSVDataSet(filepath=str(tmp_path / "mul.csv")),
            "divided_data": CSVDataSet(filepath=str(tmp_path / "div.csv")),
            "summed_data": CSVDataSet(filepath=str(tmp_path / "sum.csv")),
        }
    )
    for ds in cat.list():
        cat.save(ds, DATASET)

    return cat


NAKED_RESULT = pd.Series(
    [
        4.666667,
        9.333333,
        14.00000,
        18.66666,
        23.33333,
        28.00000,
        32.66666,
        37.33333,
        42.00000,
    ],
    name="values",
)


AGGREGATOR_RESULT = pd.Series(
    [5.0, 10, 15, 20, 25, 30, 35, 40, 45, 11, 22, 33, 44, 55, 66, 77, 88, 99],
    name="values",
)


FILTERED_RESULT = pd.Series(
    [4.666667, 9.333333, 14.00000, 18.66666, 23.33333, 28.00000], name="values",
)


class TestParallelisedPipelines:
    def test_naked_pipe(self, runner, pipe, catalog):
        runner.run(pipe, catalog)
        assert_series_equal(catalog.load("summed_data")["values"], NAKED_RESULT)

    def test_parallelised_pipeline(self, runner, pipe, catalog):
        ppipe = parallelised_pipeline(
            pipe, scenarios={"multiply_by": [2, 5], "divide_by": [2]},
        )
        runner.run(ppipe, catalog)
        assert_series_equal(catalog.load("summed_data")["values"], AGGREGATOR_RESULT)

    def test_filtered_parallelised_pipeline(self, runner, pipe, catalog):
        ppipe = parallelised_pipeline(
            pipe,
            scenarios={"scenario": ["A", "B"], "subscenario": ["c", "d"]},
            filters={"base_data": ["col1", "col2"]},
        )
        runner.run(ppipe, catalog)
        assert_series_equal(catalog.load("summed_data")["values"], FILTERED_RESULT)
