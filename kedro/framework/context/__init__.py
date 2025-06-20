"""``kedro.framework.context`` provides functionality for loading Kedro
project context.
"""

from .context import KedroContext, KedroContextError

__all__ = ["KedroContext", "KedroContextError"]
