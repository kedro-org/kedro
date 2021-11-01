"""``kedro.versioning`` provides functionality to setup the Journal for
capturing information required to reproduce a Kedro run.
"""

from .journal import Journal

__all__ = ["Journal"]
