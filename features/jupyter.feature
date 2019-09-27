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
#

Feature: Jupyter targets in new project

  Background:
    Given I have prepared a config file with example code
    And I have run a non-interactive kedro new
    And I have executed the kedro command "install"

  Scenario: Execute jupyter-notebook target
    When I execute the kedro jupyter command "notebook --no-browser"
    Then jupyter notebook should run on port 8888

  Scenario: Execute jupyter-lab target
    When I execute the kedro jupyter command "lab --no-browser"
    Then Jupyter Lab should run on port 8888

  Scenario: Execute node convert into Python files
    Given I have added a test jupyter notebook
    When I execute the test jupyter notebook and save changes
    And I execute the kedro jupyter command "convert --all"
    And Wait until the process is finished
    Then I should get a successful exit code
    And Code cell with node tag should be converted into kedro node
