"""``kedro.framework.session`` provides access to KedroSession responsible for
project lifecycle.
"""
from .session import KedroSession, get_current_session

__all__ = ["KedroSession", "get_current_session"]
