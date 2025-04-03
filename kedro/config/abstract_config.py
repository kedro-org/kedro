"""This module provides ``kedro.abstract_config`` with the baseline
class model for a `ConfigLoader` implementation.
"""

from __future__ import annotations

from collections import UserDict
from pathlib import Path  # noqa: TCH003
from typing import Any


class AbstractConfigLoader(UserDict):
    """``AbstractConfigLoader`` is the abstract base class
        for all `ConfigLoader` implementations.
    All user-defined `ConfigLoader` implementations should inherit
        from `AbstractConfigLoader` and implement all relevant abstract methods.
    """

    def __init__(
        self,
        conf_source: str | Path,
        env: str | None = None,
        runtime_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__()
        self.conf_source = conf_source
        self.env = env
        self.runtime_params = runtime_params or {}

    # As of Python 3.12 __getitem__ is no longer called in the inherited UserDict.get()
    # This causes AbstractConfigLoader.get() to break
    # See: https://github.com/python/cpython/issues/105524
    # Overwrite the inherited get function with the implementation from 3.11 and prior
    def get(self, key: str, default: Any = None) -> Any:
        "D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None."
        try:
            return self[key]
        except KeyError:
            return default


class BadConfigException(Exception):
    """Raised when a configuration file cannot be loaded, for instance
    due to wrong syntax or poor formatting.
    """

    pass


class MissingConfigException(Exception):
    """Raised when no configuration files can be found within a config path"""

    pass
