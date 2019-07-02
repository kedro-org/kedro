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
import pytest

from kedro.contrib.decorators import pandas_to_spark, retry, spark_to_pandas
from kedro.pipeline import node


@pytest.fixture()
def pandas_df():
    return pd.DataFrame(
        {
            "Name": ["Alex", "Bob", "Clarke", "Dave"],
            "Age": [31, 12, 65, 29],
            "member": ["y", "n", "y", "n"],
        }
    )


@pytest.fixture()
def spark_df(pandas_df, spark_session):
    return spark_session.createDataFrame(pandas_df)


@pytest.fixture()
def three_arg_node():
    return node(
        lambda arg1, arg2, arg3: [arg1, arg2, arg3],
        ["input1", "input2", "input3"],
        ["output1", "output2", "output3"],
    )


@pytest.fixture()
def inputs(pandas_df, spark_df):
    return {"input1": pandas_df, "input2": spark_df, "input3": pandas_df}


def test_pandas_to_spark(three_arg_node, spark_session, pandas_df, inputs):
    res = three_arg_node.decorate(pandas_to_spark(spark_session)).run(inputs)
    for output in ["output1", "output2", "output3"]:
        assert res[output].toPandas().equals(pandas_df)


def test_spark_to_pandas(three_arg_node, pandas_df, inputs):
    res = three_arg_node.decorate(spark_to_pandas()).run(inputs)
    for output in ["output1", "output2", "output3"]:
        assert res[output].equals(pandas_df)


def test_retry():
    def _bigger(obj):
        obj["value"] += 1
        if obj["value"] >= 0:
            return True
        raise ValueError("Value less than 0")

    decorated = node(_bigger, "in", "out").decorate(retry())

    with pytest.raises(ValueError, match=r"Value less than 0"):
        decorated.run({"in": {"value": -3}})

    decorated2 = node(_bigger, "in", "out").decorate(retry(n_times=2))
    assert decorated2.run({"in": {"value": -3}})
