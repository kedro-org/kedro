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

"""
This module contains function decorators for PySpark, which can be
used as ``Node`` decorators. See ``kedro.pipeline.node.decorate``
"""
from functools import wraps
from typing import Callable
from warnings import warn

import pandas as pd

try:
    from pyspark.sql import SparkSession
except ImportError as error:
    raise ImportError(
        "{}: `pip install kedro[pyspark]` to get the required "
        "dependencies".format(error)
    )

warn(
    "`kedro.contrib.decorators.pyspark` will be deprecated in future releases. "
    "Please refer to Transcoding in the Kedro documentation for an alternative method.",
    DeprecationWarning,
)


def pandas_to_spark(spark: SparkSession) -> Callable:
    """Inspects the decorated function's inputs and converts all pandas
    DataFrame inputs to spark DataFrames.

    **Note** that in the example below we have enabled
    ``spark.sql.execution.arrow.enabled``. For this to work, you should first
    ``pip install pyarrow`` and add ``pyarrow`` to ``requirements.txt``.
    Enabling this option makes the convertion between pyspark <-> DataFrames
    **much faster**.

    Args:
        spark: The spark session singleton object to use for the creation of
            the pySpark DataFrames. A possible pattern you can use here is
            the following:

            **spark.py**
            ::

                >>> from pyspark.sql import SparkSession
                >>>
                >>> def get_spark():
                >>>   return (
                >>>     SparkSession.builder
                >>>       .master("local[*]")
                >>>       .appName("kedro")
                >>>       .config("spark.driver.memory", "4g")
                >>>       .config("spark.driver.maxResultSize", "3g")
                >>>       .config("spark.sql.execution.arrow.enabled", "true")
                >>>       .getOrCreate()
                >>>     )

            **nodes.py**
            ::

                >>> from spark import get_spark
                >>> @pandas_to_spark(get_spark())
                >>> def node_1(data):
                >>>     data.show() # data is pyspark.sql.DataFrame

    Returns:
        The original function with any pandas DF inputs translated to spark.

    """

    def _to_spark(arg):
        if isinstance(arg, pd.DataFrame):
            return spark.createDataFrame(arg)
        return arg

    def inputs_to_spark(node_func: Callable):
        @wraps(node_func)
        def _wrapper(*args, **kwargs):
            return node_func(
                *[_to_spark(arg) for arg in args],
                **{key: _to_spark(value) for key, value in kwargs.items()}
            )

        return _wrapper

    return inputs_to_spark


def spark_to_pandas() -> Callable:
    """Inspects the decorated function's inputs and converts all pySpark
    DataFrame inputs to pandas DataFrames.

    Returns:
        The original function with any pySpark DF inputs translated to pandas.

    """

    def _to_pandas(arg):
        if "pyspark.sql.dataframe" in str(type(arg)):
            return arg.toPandas()
        return arg

    def inputs_to_pandas(node_func: Callable):
        @wraps(node_func)
        def _wrapper(*args, **kwargs):
            return node_func(
                *[_to_pandas(arg) for arg in args],
                **{key: _to_pandas(value) for key, value in kwargs.items()}
            )

        return _wrapper

    return inputs_to_pandas
