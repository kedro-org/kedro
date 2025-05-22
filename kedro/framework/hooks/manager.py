# FILE: kedro/framework/hooks/manager.py

import logging
from collections.abc import Iterable
from inspect import isclass
from typing import Any

from pluggy import PluginManager

from .markers import HOOK_NAMESPACE
# Ensure all specs, including RunnerSpecs, are imported
from .specs import (
    DataCatalogSpecs,
    DatasetSpecs,
    KedroContextSpecs,
    NodeSpecs,
    PipelineSpecs,
    RunnerSpecs,
)

_PLUGIN_HOOKS = "kedro.hooks"
logger = logging.getLogger(__name__)


# MODIFIED _create_hook_manager
def _create_hook_manager(enable_tracing: bool = True) -> PluginManager:
    """Create a new PluginManager instance and register Kedro's hook specs.

    Args:
        enable_tracing: If True (default), enables pluggy's tracing and sets a log writer.
                        Should be set to False when creating managers for subprocesses
                        that need to be picklable (e.g., for ParallelRunner).
    """
    manager = PluginManager(HOOK_NAMESPACE)

    if enable_tracing:
        manager.trace.root.setwriter(
            logger.debug if logger.getEffectiveLevel() <= logging.DEBUG else None
        )
        manager.enable_tracing()

    manager.add_hookspecs(NodeSpecs)
    manager.add_hookspecs(PipelineSpecs)
    manager.add_hookspecs(DataCatalogSpecs)
    manager.add_hookspecs(DatasetSpecs)
    manager.add_hookspecs(KedroContextSpecs)
    manager.add_hookspecs(RunnerSpecs)
    return manager


def _register_hooks(hook_manager: PluginManager, hooks: Iterable[Any]) -> None:
    for hooks_collection in hooks:
        if not hook_manager.is_registered(hooks_collection):
            if isclass(hooks_collection):  # type: ignore
                raise TypeError(
                    "KedroSession expects hooks to be registered as instances. "
                    "Have you forgotten the `()` when registering a hook class ?"
                )
            hook_manager.register(hooks_collection)


def _register_hooks_entry_points(
        hook_manager: PluginManager, disabled_plugins: Iterable[str]
) -> None:
    already_registered = hook_manager.get_plugins()
    hook_manager.load_setuptools_entrypoints(_PLUGIN_HOOKS)
    disabled_plugins = set(disabled_plugins)

    plugininfo = hook_manager.list_plugin_distinfo()
    plugin_names = set()
    disabled_plugin_names = set()
    for plugin, dist in plugininfo:
        if dist.project_name in disabled_plugins:
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
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __getattr__(self, name: str) -> Any:
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        pass
