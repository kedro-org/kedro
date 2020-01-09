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
import importlib
import re

import pandas as pd
import pytest

import kedro.contrib.decorators.pyspark as spark_decorators
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
    res = three_arg_node.decorate(spark_decorators.pandas_to_spark(spark_session)).run(
        inputs
    )
    for output in ["output1", "output2", "output3"]:
        assert res[output].toPandas().equals(pandas_df)


def test_pandas_to_spark_dict(pandas_df, spark_df, spark_session):
    @spark_decorators.pandas_to_spark(spark_session)
    def func_with_kwargs(arg1, arg2=None, arg3=None):
        return [arg1, arg2, arg3]

    res = func_with_kwargs(pandas_df, arg2=spark_df, arg3=pandas_df)
    for output in res:
        assert output.toPandas().equals(pandas_df)


def test_spark_to_pandas(three_arg_node, pandas_df, inputs):
    res = three_arg_node.decorate(spark_decorators.spark_to_pandas()).run(inputs)
    for output in ["output1", "output2", "output3"]:
        assert res[output].equals(pandas_df)


def test_spark_to_pandas_dict(pandas_df, spark_df):
    @spark_decorators.spark_to_pandas()
    def func_with_kwargs(arg1, arg2=None, arg3=None):
        return [arg1, arg2, arg3]

    res = func_with_kwargs(pandas_df, arg2=spark_df, arg3=pandas_df)
    for output in res:
        assert output.equals(pandas_df)


def test_spark_import_error(mocker):
    mocker.patch.dict("sys.modules", {"pyspark.sql": None})
    pattern = "`pip install kedro[pyspark]` to get the required dependencies"
    with pytest.raises(ImportError, match=re.escape(pattern)):
        importlib.reload(spark_decorators)
