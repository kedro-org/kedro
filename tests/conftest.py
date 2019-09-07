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

"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""
import gc
import os
import sys
from subprocess import Popen

import pytest
from pyspark import SparkContext
from pyspark.sql import SparkSession

the_real_getOrCreate = None


class UseTheSparkSessionFixtureOrMock:  # pylint: disable=too-few-public-methods
    pass


# prevent using spark without going through the spark_session fixture
@pytest.fixture(scope="session", autouse=True)
def no_spark():
    global the_real_getOrCreate  # pylint: disable=global-statement
    the_real_getOrCreate = SparkSession.builder.getOrCreate
    SparkSession.builder.getOrCreate = UseTheSparkSessionFixtureOrMock


# clean up pyspark after the test module finishes
@pytest.fixture(scope="module")
def spark_session():
    SparkSession.builder.getOrCreate = the_real_getOrCreate
    spark = SparkSession.builder.getOrCreate()
    yield spark
    spark.stop()
    SparkSession.builder.getOrCreate = UseTheSparkSessionFixtureOrMock

    # remove the cached JVM vars
    SparkContext._jvm = None  # pylint: disable=protected-access
    SparkContext._gateway = None  # pylint: disable=protected-access

    # py4j doesn't shutdown properly so kill the actual JVM process
    for obj in gc.get_objects():
        try:
            if isinstance(obj, Popen) and "pyspark" in obj.args[0]:
                obj.terminate()
        except ReferenceError:  # pragma: no cover
            # gc.get_objects may return dead weak proxy objects that will raise
            # ReferenceError when you isinstance them
            pass


@pytest.fixture(autouse=True)
def preserve_system_context():
    """
    Revert some changes to the application context tests do to isolate them.
    """
    old_path = sys.path.copy()
    old_cwd = os.getcwd()
    yield
    sys.path = old_path

    if os.getcwd() != old_cwd:
        os.chdir(old_cwd)
