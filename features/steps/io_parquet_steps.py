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
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""Behave step definitions for Parquet load/save functionality
in the io_scenarios feature.
"""

import pandas as pd
from behave import given, then, when
from pandas.util.testing import assert_frame_equal

from kedro.io import ParquetLocalDataSet


@given("I have defined data in a pandas DataFrame")
def provide_df(context):
    """Adds a dummy dataframe to the context."""
    people = pd.DataFrame(
        {"Name": ["Alex", "Bob", "Clarke", "Dave"], "Age": [31, 12, 65, 29]}
    )
    context.pandas_df = people


@when("I write a given data to a Parquet file")
def write_parquet_locally(context):
    """Writes DataFrame as Parquet in a temporary directory."""
    file_name = "dummy.parq"
    context.full_path = context.temp_dir / file_name
    context.data_set = ParquetLocalDataSet(str(context.full_path))
    context.data_set.save(context.pandas_df)
    assert context.full_path.exists()


@then("the data should be loaded without any alteration")
def parquet_content_returned(context):
    """Load from data set, compare with original DataFrame
    and delete temp directory.
    """
    loaded_parquet = context.data_set.load()
    assert_frame_equal(loaded_parquet, context.pandas_df)
