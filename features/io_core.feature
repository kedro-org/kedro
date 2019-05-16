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


Feature: Kedro IO DataSet features

  Scenario: Create a custom data set
    Given I have defined a custom CSV data set with both load and save methods
    When I load the data set
    Then CSV file content should be returned

  Scenario: Create a missing custom data set
    Given I have pointed a CSV data set to a missing file
    When I load the data set
    Then an error should be raised

  Scenario: Save data
    Given I have defined a custom CSV data set with both load and save methods
    When I save a data frame
    Then the CSV file contents should be updated with the contents of the data frame

  Scenario: Prevent saving to data set without save function
    Given I have defined a custom CSV data set without providing a save method
    When I save a data frame
    Then an exception should be thrown

  Scenario: Saving and loading
    Given I have defined a custom CSV data set with both load and save methods to the same file
    When I save a data frame and then load it
    Then the value I originally saved should be returned

  Scenario: Saving and loading with CSVLocalDataSet
    Given I have instantiated a CSVLocalDataSet
    When I save a data frame and then load it
    Then the value I originally saved should be returned

  Scenario: Saving and loading with CSVLocalDataSet
    Given I have instantiated a CSVLocalDataSet with tabs as separator
    When I save a data frame and then load it
    Then the value I originally saved should be returned

  Scenario: Loading with MemoryDataSet
    Given I have instatiated a MemoryDataSet with data
    When I load the data from the MemoryDataSet
    Then the original data should be returned

  Scenario: Saving with MemoryDataSet
    Given I have instatiated a MemoryDataSet with data
    And I have saved a new data frame
    When I load the data from the MemoryDataSet
    Then the new data frame should be returned
