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
import logging
from typing import Any, Iterable

from pluggy import PluginManager

from .markers import HOOK_NAMESPACE
from .specs import (
    DataCatalogSpecs,
    DatasetSpecs,
    NodeSpecs,
    PipelineSpecs,
    RegistrationSpecs,
)

_hook_manager = None

_PLUGIN_HOOKS = "kedro.hooks"  # entry-point to load hooks from for installed plugins


def _create_hook_manager() -> PluginManager:
    """Create a new PluginManager instance and register Kedro's hook specs.
    """
    manager = PluginManager(HOOK_NAMESPACE)
    manager.add_hookspecs(NodeSpecs)
    manager.add_hookspecs(PipelineSpecs)
    manager.add_hookspecs(DataCatalogSpecs)
    manager.add_hookspecs(RegistrationSpecs)
    manager.add_hookspecs(DatasetSpecs)
    return manager


def get_hook_manager():
    """Create or return the global _hook_manager singleton instance.
    """
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = _create_hook_manager()
    return _hook_manager


def _register_hooks(hook_manager: PluginManager, hooks: Iterable[Any]) -> None:
    """Register all hooks as specified in ``hooks`` with the global ``hook_manager``.

    Args:
        hook_manager: Hook manager instance to register the hooks with.
        hooks: Hooks that need to be registered.

    """
    for hooks_collection in hooks:
        # Sometimes users might call hook registration more than once, in which
        # case hooks have already been registered, so we perform a simple check
        # here to avoid an error being raised and break user's workflow.
        if not hook_manager.is_registered(hooks_collection):
            hook_manager.register(hooks_collection)


def _register_hooks_setuptools(
    hook_manager: PluginManager, disabled_plugins: Iterable[str]
) -> None:
    """Register pluggy hooks from setuptools entrypoints.

    Args:
        hook_manager: Hook manager instance to register the hooks with.
        disabled_plugins: An iterable returning the names of plugins
            which hooks must not be registered; any already registered
            hooks will be unregistered.

    """
    already_registered = hook_manager.get_plugins()
    found = hook_manager.load_setuptools_entrypoints(_PLUGIN_HOOKS)
    disabled_plugins = set(disabled_plugins)

    # Get list of plugin/distinfo tuples for all setuptools registered plugins.
    plugininfo = hook_manager.list_plugin_distinfo()
    plugin_names = set()
    disabled_plugin_names = set()
    for plugin, dist in plugininfo:
        if dist.project_name in disabled_plugins:
            # `unregister()` is used instead of `set_blocked()` because
            # we want to disable hooks for specific plugin based on project
            # name and not `entry_point` name. Also, we log project names with
            # version for which hooks were registered.
            hook_manager.unregister(plugin=plugin)
            found -= 1
            disabled_plugin_names.add(f"{dist.project_name}-{dist.version}")
        elif plugin not in already_registered:
            plugin_names.add(f"{dist.project_name}-{dist.version}")

    if disabled_plugin_names:
        logging.info(
            "Hooks are disabled for plugin(s): %s",
            ", ".join(sorted(disabled_plugin_names)),
        )

    if plugin_names:
        logging.info(
            "Registered hooks from %d installed plugin(s): %s",
            found,
            ", ".join(sorted(plugin_names)),
        )
