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

"""This module contains unit tests for methods in the Kedro __init__.py
"""

import logging

from kedro.config.default_logger import LOGGING_CONFIG


def test_cli_logging_setup():
    def to_names(handlers):
        return [h.name for h in handlers]

    assert LOGGING_CONFIG is not None

    # Check root logger is set up correctly
    root_handler_names = to_names(logging.getLogger().handlers)
    all_handlers = ["console", "info_file_handler", "error_file_handler"]
    intersection = set(root_handler_names).intersection(all_handlers)
    assert len(intersection) == 3

    # check cli logger is set up correctly
    cli_handlers = to_names(logging.getLogger("kedro.framework.cli").handlers)
    assert len(cli_handlers) == 1
    assert "console" in cli_handlers
