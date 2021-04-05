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
"""This module defines a dedicated hook manager for hooks that extends Kedro CLI behaviour."""
import logging

from pluggy import PluginManager

from .markers import CLI_HOOK_NAMESPACE
from .specs import CLICommandSpecs

_CLI_PLUGIN_HOOKS = "kedro.cli_hooks"


class CLIHooksManager(PluginManager):
    """Hooks manager to manage CLI hooks"""

    def __init__(self) -> None:
        super().__init__(CLI_HOOK_NAMESPACE)
        self.add_hookspecs(CLICommandSpecs)
        self._register_cli_hooks_setuptools()

    def _register_cli_hooks_setuptools(self) -> None:
        """Register CLI hook implementations from setuptools entrypoints"""
        already_registered = self.get_plugins()
        num_cli_hooks_found = self.load_setuptools_entrypoints(_CLI_PLUGIN_HOOKS)

        # Get list of plugin/distinfo tuples for all setuptools registered plugins.
        plugininfo = self.list_plugin_distinfo()
        plugin_names = {
            f"{dist.project_name}-{dist.version}"
            for plugin, dist in plugininfo
            if plugin not in already_registered
        }

        if plugin_names:
            logging.info(
                "Registered CLI hooks from %d installed plugin(s): %s",
                num_cli_hooks_found,
                ", ".join(sorted(plugin_names)),
            )
