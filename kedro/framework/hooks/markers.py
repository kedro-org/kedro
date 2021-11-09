"""This module provides markers to declare Kedro's hook specs and implementations.
For more information, please see
[Pluggy's documentation](https://pluggy.readthedocs.io/en/stable/#marking-hooks).
"""

import pluggy

HOOK_NAMESPACE = "kedro"

hook_spec = pluggy.HookspecMarker(HOOK_NAMESPACE)
hook_impl = pluggy.HookimplMarker(HOOK_NAMESPACE)
