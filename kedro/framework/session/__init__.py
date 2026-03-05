"""``kedro.framework.session`` provides access to KedroSession responsible for
project lifecycle.
"""

from .session import AbstractSession, KedroSession

__all__ = ["AbstractSession", "KedroSession"]
