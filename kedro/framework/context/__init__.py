"""``kedro.framework.context`` provides functionality for loading Kedro
project context.
"""

from .context import KedroContext, KedroContextError, load_context

__all__ = ["KedroContext", "KedroContextError", "load_context"]
