"""This module provides an utility function to retrieve the global hook_manager singleton
in a Kedro's execution process.
"""
import logging
from typing import Any, Iterable

from pluggy import PluginManager

from .markers import HOOK_NAMESPACE
from .specs import (
    DataCatalogSpecs,
    DatasetSpecs,
    KedroContextSpecs,
    NodeSpecs,
    PipelineSpecs,
)

_PLUGIN_HOOKS = "kedro.hooks"  # entry-point to load hooks from for installed plugins

logger = logging.getLogger(__name__)


def _create_hook_manager() -> PluginManager:
    """Create a new PluginManager instance and register Kedro's hook specs."""
    manager = PluginManager(HOOK_NAMESPACE)
    manager.trace.root.setwriter(logger.debug)
    manager.enable_tracing()
    manager.add_hookspecs(NodeSpecs)
    manager.add_hookspecs(PipelineSpecs)
    manager.add_hookspecs(DataCatalogSpecs)
    manager.add_hookspecs(DatasetSpecs)
    manager.add_hookspecs(KedroContextSpecs)
    return manager


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


def _register_hooks_entry_points(
    hook_manager: PluginManager, disabled_plugins: Iterable[str]
) -> None:
    """Register pluggy hooks from python package entrypoints.

    Args:
        hook_manager: Hook manager instance to register the hooks with.
        disabled_plugins: An iterable returning the names of plugins
            which hooks must not be registered; any already registered
            hooks will be unregistered.

    """
    already_registered = hook_manager.get_plugins()
    # Method name is misleading:
    # entry points are standard and don't require setuptools,
    # see https://packaging.python.org/en/latest/specifications/entry-points/
    hook_manager.load_setuptools_entrypoints(_PLUGIN_HOOKS)
    disabled_plugins = set(disabled_plugins)

    # Get list of plugin/distinfo tuples for all registered plugins.
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
            disabled_plugin_names.add(f"{dist.project_name}-{dist.version}")
        elif plugin not in already_registered:
            plugin_names.add(f"{dist.project_name}-{dist.version}")

    if disabled_plugin_names:
        logger.debug(
            "Hooks are disabled for plugin(s): %s",
            ", ".join(sorted(disabled_plugin_names)),
        )

    if plugin_names:
        logger.debug(
            "Registered hooks from %d installed plugin(s): %s",
            len(plugin_names),
            ", ".join(sorted(plugin_names)),
        )


class _NullPluginManager:
    """This class creates an empty ``hook_manager`` that will ignore all calls to hooks,
    allowing the runner to function if no ``hook_manager`` has been instantiated."""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        pass
