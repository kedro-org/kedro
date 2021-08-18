# Copyright 2021 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
"""This module provides ``kedro.abstract_config`` with the baseline
class model for a `ConfigLoader` implementation.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class AbstractConfigLoader(ABC):
    """
    ``AbstractConfigLoader`` is the abstract base class
        for all `ConfigLoader` implementations.
    All user-defined `ConfigLoader` implementations should inherit
        from `AbstractConfigLoader` and implement all relevant abstract methods.
    """

    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: Dict[str, Any] = None,
        **kwargs  # pylint: disable=unused-argument
    ):
        self.conf_source = conf_source
        self.env = env
        self.runtime_params = runtime_params

    @abstractmethod  # pragma: no cover
    def get(self) -> Dict[str, Any]:
        """Required method to get all configurations."""
        pass


class BadConfigException(Exception):
    """Raised when a configuration file cannot be loaded, for instance
    due to wrong syntax or poor formatting.
    """

    pass


class MissingConfigException(Exception):
    """Raised when no configuration files can be found within a config path"""

    pass
