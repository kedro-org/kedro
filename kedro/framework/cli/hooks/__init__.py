"""``kedro.framework.cli.hooks`` provides primitives to use hooks to extend KedroCLI's behaviour"""
from .manager import CLIHooksManager, get_cli_hook_manager
from .markers import cli_hook_impl

__all__ = ["CLIHooksManager", "cli_hook_impl", "get_cli_hook_manager"]
