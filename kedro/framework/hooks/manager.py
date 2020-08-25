# Copyright 2020 QuantumBlack Visual Analytics Limited
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
"""This module provides an utility function to retrieve the global hook_manager singleton
in a Kedro's execution process.
"""
# pylint: disable=global-statement,invalid-name
from pluggy import PluginManager

from .markers import HOOK_NAMESPACE
from .specs import DataCatalogSpecs, NodeSpecs, PipelineSpecs, RegistrationSpecs

_hook_manager = None


def _create_hook_manager() -> PluginManager:
    """Create a new PluginManager instance and register Kedro's hook specs.
    """
    manager = PluginManager(HOOK_NAMESPACE)
    manager.add_hookspecs(NodeSpecs)
    manager.add_hookspecs(PipelineSpecs)
    manager.add_hookspecs(DataCatalogSpecs)
    manager.add_hookspecs(RegistrationSpecs)
    return manager


def get_hook_manager():
    """Create or return the global _hook_manager singleton instance.
    """
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = _create_hook_manager()
    return _hook_manager
