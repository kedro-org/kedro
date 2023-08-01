"""This module provides markers to declare Kedro CLI's hook specs and implementations.
For more information, please see
[Pluggy's documentation](https://pluggy.readthedocs.io/en/stable/#marking-hooks).
"""
import pluggy

CLI_HOOK_NAMESPACE = "kedro_cli"

cli_hook_spec = pluggy.HookspecMarker(CLI_HOOK_NAMESPACE)  # pragma: no cover
cli_hook_impl = pluggy.HookimplMarker(CLI_HOOK_NAMESPACE)
