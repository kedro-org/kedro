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

"""Behave step definitions for the io core features."""

import pandas as pd
from behave import given, then, when

from features.steps.util import (
    create_sample_csv,
    create_temp_csv,
    get_sample_data_frame,
)
from kedro.io import CSVLocalDataSet, DataSetError, LambdaDataSet, MemoryDataSet


@given("I have defined a custom CSV data set with both load and save methods")
def define_dataset_with_load_save(context):
    context.read_csv_path = create_sample_csv()
    context.write_csv_path = create_temp_csv()
    context.csv_data_set = LambdaDataSet(
        load=lambda: pd.read_csv(context.read_csv_path),
        save=lambda df: df.to_csv(context.write_csv_path),
    )


@given(
    "I have defined a custom CSV data set with both load and save methods "
    "to the same file"
)
def csv_dataset_same_file(context):
    context.read_csv_path = create_sample_csv()
    context.write_csv_path = context.read_csv_path
    context.csv_data_set = LambdaDataSet(
        load=lambda: pd.read_csv(context.read_csv_path),
        save=lambda df: df.to_csv(context.write_csv_path, index=False),
    )


@given("I have defined a custom CSV data set without providing a save method")
def data_set_with_no_save(context):
    context.csv_data_set = LambdaDataSet(load=None, save=None)


@given("I have instantiated a CSVLocalDataSet")
def prepare_csv_data(context):
    context.read_csv_path = create_sample_csv()
    context.write_csv_path = create_temp_csv()
    context.csv_data_set = CSVLocalDataSet(filepath=context.read_csv_path)


@given("I have instantiated a CSVLocalDataSet with tabs as separator")
def prepare_csv_data_with_tabs(context):
    context.read_csv_path = create_sample_csv()
    context.write_csv_path = create_temp_csv()
    context.csv_data_set = CSVLocalDataSet(
        filepath=context.read_csv_path,
        load_args={"sep": "\t"},
        save_args={"index": False, "sep": "\t"},
    )


@given("I have instatiated a MemoryDataSet with data")
def create_memory_data_frame(context):
    context.test_data_frame = get_sample_data_frame()
    context.memory_data_set = MemoryDataSet(data=context.test_data_frame)


@given("I have pointed a CSV data set to a missing file")
def prepare_missing_csv(context):
    sample_csv = "/var/missing_csv_file.csv"
    context.csv_data_set = LambdaDataSet(
        load=lambda: pd.read_csv(sample_csv), save=None
    )


@given("I have saved a new data frame")
def save_new_data_to_data_set(context):
    context.new_data_frame = pd.DataFrame(
        {"col1": [1, 2], "col2": [3, 4], "col3": [5, 6]}
    )
    context.memory_data_set.save(data=context.new_data_frame)


@when("I load the data set")
def loading_from_source(context):
    """Loads from the CSV."""
    try:
        context.result = context.csv_data_set.load()
    except DataSetError as error:
        context.data_set_error = error


@when("I load the data from the MemoryDataSet")
def load_data_from_memory_data_set(context):
    context.data_from_memory_data_set = context.memory_data_set.load()


@when("I save a data frame")
def save_data_frame(context):
    data_frame = get_sample_data_frame()
    try:
        context.csv_data_set.save(data_frame)
    except DataSetError:
        context.data_set_error_raised = True


@when("I save a data frame and then load it")
def save_and_load_content(context):
    data_frame = get_sample_data_frame()
    context.csv_data_set.save(data_frame)
    context.reloaded_df = context.csv_data_set.load()


@then("CSV file content should be returned")
def csv_content_returned(context):
    assert context.result is not None
    assert len(context.result) == 2


@then("the CSV file contents should be updated with the contents of the data frame")
def data_frame_content_saved(context):
    data_frame = pd.read_csv(context.write_csv_path)
    assert 5 in data_frame["col2"].values


@then("the value I originally saved should be returned")
def reloaded_content_is_returned(context):
    data_frame = get_sample_data_frame()
    assert context.reloaded_df.equals(data_frame)


@then("the original data should be returned")
def original_data_is_returned(context):
    assert context.data_from_memory_data_set.equals(context.test_data_frame)


@then("the new data frame should be returned")
def saved_data_is_returned(context):
    assert context.data_from_memory_data_set.equals(context.new_data_frame)


@then("an error should be raised")
def error_reading_missing_csv(context):
    assert context.data_set_error is not None


@then("an exception should be thrown")
def exception_is_thrown(context):
    assert context.data_set_error_raised
