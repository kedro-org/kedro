"""This module defines a dedicated hook manager for hooks that extends Kedro CLI behaviour."""

import logging

from pluggy import PluginManager

from .markers import CLI_HOOK_NAMESPACE
from .specs import CLICommandSpecs

logger = logging.getLogger(__name__)

_cli_hook_manager = None

_CLI_PLUGIN_HOOKS = "kedro.cli_hooks"


def get_cli_hook_manager() -> PluginManager:
    """Create or return the global _hook_manager singleton instance."""
    global _cli_hook_manager  # noqa: PLW0603
    if _cli_hook_manager is None:
        _cli_hook_manager = CLIHooksManager()
    _cli_hook_manager.trace.root.setwriter(
        logger.debug if logger.getEffectiveLevel() == logging.DEBUG else None
    )
    _cli_hook_manager.enable_tracing()
    return _cli_hook_manager


class CLIHooksManager(PluginManager):
    """Hooks manager to manage CLI hooks"""

    def __init__(self) -> None:
        super().__init__(CLI_HOOK_NAMESPACE)
        self.add_hookspecs(CLICommandSpecs)
        self._register_cli_hooks()

    def _register_cli_hooks(self) -> None:
        """Register CLI hook implementations from plugin CLI entrypoints"""
        already_registered = self.get_plugins()
        self.load_setuptools_entrypoints(_CLI_PLUGIN_HOOKS)

        # Get list of plugin/distinfo tuples for all setuptools registered plugins.
        plugininfo = self.list_plugin_distinfo()
        plugin_names = {
            f"{dist.project_name}-{dist.version}"
            for plugin, dist in plugininfo
            if plugin not in already_registered
        }

        if plugin_names:
            logger.debug(
                "Registered CLI hooks from %d installed plugin(s): %s",
                len(plugin_names),
                ", ".join(sorted(plugin_names)),
            )
