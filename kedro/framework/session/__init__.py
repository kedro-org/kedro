"""``kedro.framhttps://github.com/kedro-org/kedro/pull/5441ework.session`` provides access to KedroSession responsible for
project lifecycle.
"""

from .abstract_session import AbstractSession
from .session import KedroSession

__all__ = ["AbstractSession", "KedroSession"]
