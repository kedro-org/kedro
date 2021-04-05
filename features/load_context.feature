# Copyright 2021 QuantumBlack Visual Analytics Limited
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


Feature: Custom Kedro project
    Background:
        Given I have prepared a config file
        And I have run a non-interactive kedro new with starter

    Scenario: Update the source directory to be nested
        When I move the package to "src/nested"
        And Source directory is updated to "src/nested" in pyproject.toml
        And I execute the kedro command "run"
        Then I should get a successful exit code

    Scenario: Update the source directory to be outside of src
        When I move the package to "."
        And Source directory is updated to "." in pyproject.toml
        And I execute the kedro command "run"
        Then I should get a successful exit code

    Scenario: Hooks from installed plugins are automatically registered
        Given I have installed the test plugin
        When I execute the kedro command "run"
        Then I should get a successful exit code
        And I should get a message including "Registered hooks from 1 installed plugin(s): test-plugin-0.1"
        And I should get a message including "Reached after_catalog_created hook"

    Scenario: Pipelines from installed plugins are added to the project's pipelines
        Given I have installed the test plugin
        When I execute the kedro command "run --pipeline from_plugin"
        Then I should get a successful exit code
        And I should get a message including "Registered hooks from 1 installed plugin(s): test-plugin-0.1"

    Scenario: Disable automatically registered plugin hooks
        Given I have installed the test plugin
        And I have disabled hooks for "test-plugin" plugin via config
        When I execute the kedro command "run"
        Then I should get a successful exit code
        And I should not get a message including "Registered hooks from 1 installed plugin(s): test-plugin-0.1"
        And I should not get a message including "Reached after_catalog_created hook"
        And I should get a message including "Hooks are disabled for plugin(s): test-plugin-0.1"
